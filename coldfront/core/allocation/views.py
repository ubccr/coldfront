import datetime
import logging
import urllib
import csv
from datetime import date

from dateutil.relativedelta import relativedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms import formset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.http.response import StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html, mark_safe
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView

from coldfront.core.allocation.forms import (AllocationAccountForm,
                                             AllocationAddUserForm,
                                             AllocationAttributeDeleteForm,
                                             AllocationChangeForm,
                                             AllocationChangeNoteForm,
                                             AllocationAttributeChangeForm,
                                             AllocationAttributeUpdateForm,
                                             AllocationForm,
                                             AllocationInvoiceNoteDeleteForm,
                                             AllocationInvoiceUpdateForm,
                                             AllocationInvoiceExportForm,
                                             AllocationRemoveUserForm,
                                             AllocationRemoveUserFormset,
                                             AllocationReviewUserForm,
                                             AllocationSearchForm,
                                             AllocationUpdateForm)
from coldfront.core.allocation.models import (Allocation, AllocationAccount,
                                              AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationChangeRequest,
                                              AllocationChangeStatusChoice,
                                              AllocationAttributeChangeRequest,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserNote,
                                              AllocationUserRequestStatusChoice,
                                              AllocationUserRequest,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.utils import (compute_prorated_amount,
                                             generate_guauge_data_from_usage,
                                             get_user_resources,
                                             send_allocation_user_request_email)
from coldfront.core.utils.common import Echo
from coldfront.core.allocation.signals import (allocation_activate,
                                               allocation_activate_user,
                                               allocation_disable,
                                               allocation_remove_user,
                                               allocation_change_approved,)
from coldfront.core.project.models import (Project, ProjectUser,
                                           ProjectUserStatusChoice)
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email_template, get_email_recipient_from_groups

ALLOCATION_ENABLE_ALLOCATION_RENEWAL = import_from_settings(
    'ALLOCATION_ENABLE_ALLOCATION_RENEWAL', True)
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = import_from_settings(
    'ALLOCATION_DEFAULT_ALLOCATION_LENGTH', 365)
ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT = import_from_settings(
    'ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT', True)

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings(
        'EMAIL_TICKET_SYSTEM_ADDRESS')
    EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings(
        'EMAIL_OPT_OUT_INSTRUCTION_URL')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')

PROJECT_ENABLE_PROJECT_REVIEW = import_from_settings(
    'PROJECT_ENABLE_PROJECT_REVIEW', False)
INVOICE_ENABLED = import_from_settings('INVOICE_ENABLED', False)
if INVOICE_ENABLED:
    INVOICE_DEFAULT_STATUS = import_from_settings(
        'INVOICE_DEFAULT_STATUS', 'Pending Payment')

ALLOCATION_ACCOUNT_ENABLED = import_from_settings(
    'ALLOCATION_ACCOUNT_ENABLED', False)
ALLOCATION_ACCOUNT_MAPPING = import_from_settings(
    'ALLOCATION_ACCOUNT_MAPPING', {})


logger = logging.getLogger(__name__)


class AllocationDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Allocation
    template_name = 'allocation/allocation_detail.html'
    context_object_name = 'allocation'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_view_all_allocations'):
            return True

        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        user_can_access_project = allocation_obj.project.projectuser_set.filter(
            user=self.request.user, status__name__in=['Active', 'New', ]).exists()

        user_can_access_allocation = allocation_obj.allocationuser_set.filter(
            user=self.request.user, status__name__in=['Active', 'Pending - Remove']).exists()

        if user_can_access_project and user_can_access_allocation:
            return True

        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        allocation_users = allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed']).order_by('user__username')

        if self.request.user.is_superuser:
            attributes_with_usage = [attribute for attribute in allocation_obj.allocationattribute_set.all(
            ).order_by('allocation_attribute_type__name') if hasattr(attribute, 'allocationattributeusage')]

            attributes = [attribute for attribute in allocation_obj.allocationattribute_set.all(
            ).order_by('allocation_attribute_type__name')]

        else:
            attributes_with_usage = [attribute for attribute in allocation_obj.allocationattribute_set.filter(
                allocation_attribute_type__is_private=False) if hasattr(attribute, 'allocationattributeusage')]

            attributes = [attribute for attribute in allocation_obj.allocationattribute_set.filter(
                allocation_attribute_type__is_private=False)]

        allocation_changes = allocation_obj.allocationchangerequest_set.all().order_by('-pk')

        guage_data = []
        invalid_attributes = []
        for attribute in attributes_with_usage:
            try:
                guage_data.append(generate_guauge_data_from_usage(attribute.allocation_attribute_type.name,
                                                                  float(attribute.value), float(attribute.allocationattributeusage.value)))
            except ValueError:
                logger.error("Allocation attribute '%s' is not an int but has a usage",
                             attribute.allocation_attribute_type.name)
                invalid_attributes.append(attribute)

        for a in invalid_attributes:
            attributes_with_usage.remove(a)

        context['guage_data'] = guage_data
        context['attributes_with_usage'] = attributes_with_usage
        context['attributes'] = attributes
        context['allocation_changes'] = allocation_changes

        # Can the user update the project?
        context['is_allowed_to_update_project'] = False
        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True
        elif allocation_obj.project.projectuser_set.filter(user=self.request.user).exists():
            project_user = allocation_obj.project.projectuser_set.get(
                user=self.request.user)
            if project_user.role.name == 'Manager':
                if allocation_obj.get_parent_resource.name == "Slate-Project":
                    if allocation_obj.data_manager == self.request.user.username:
                        context['is_allowed_to_update_project'] = True
                else:
                    context['is_allowed_to_update_project'] = True

        context['allocation_users'] = allocation_users

        if self.request.user.is_superuser:
            notes = allocation_obj.allocationusernote_set.all()
        else:
            notes = allocation_obj.allocationusernote_set.filter(
                is_private=False)

        context['notes'] = notes
        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
        return context

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        initial_data = {
            'status': allocation_obj.status,
            'end_date': allocation_obj.end_date,
            'start_date': allocation_obj.start_date,
            'description': allocation_obj.description,
            'is_locked': allocation_obj.is_locked,
            'is_changeable': allocation_obj.is_changeable,
        }

        form = AllocationUpdateForm(initial=initial_data)
        if not self.request.user.is_superuser:
            form.fields['is_locked'].disabled = True
            form.fields['is_changeable'].disabled = True

        context = self.get_context_data()
        context['form'] = form
        context['allocation'] = allocation_obj

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        if not self.request.user.is_superuser:
            messages.success(
                request, 'You do not have permission to update the allocation')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

        initial_data = {
            'status': allocation_obj.status,
            'end_date': allocation_obj.end_date,
            'start_date': allocation_obj.start_date,
            'description': allocation_obj.description,
            'is_locked': allocation_obj.is_locked,
            'is_changeable': allocation_obj.is_changeable,
        }
        form = AllocationUpdateForm(request.POST, initial=initial_data)

        if form.is_valid():
            form_data = form.cleaned_data
            status = form.cleaned_data.get('status')
            end_date = form_data.get('end_date')
            start_date = form_data.get('start_date')
            description = form_data.get('description')
            is_locked = form_data.get('is_locked')
            is_changeable = form_data.get('is_changeable')

            old_status = allocation_obj.status.name
            new_status = status.name

            allocation_obj.description = description
            allocation_obj.is_locked = is_locked
            allocation_obj.is_changeable = is_changeable
            allocation_obj.end_date = end_date
            allocation_obj.start_date = start_date
            allocation_obj.save()

            if initial_data.get('status') != status and allocation_obj.project.status.name != "Active":
                messages.error(request, 'Project must be approved first before you can update this allocation\'s status!')
                return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

            allocation_obj.status = form_data.get('status')
            allocation_obj.save()

            if EMAIL_ENABLED:
                resource_name = allocation_obj.get_parent_resource
                domain_url = get_domain_url(self.request)
                allocation_url = '{}{}'.format(domain_url, reverse(
                    'allocation-detail', kwargs={'pk': allocation_obj.pk}))

            if old_status != 'Active' and new_status == 'Active':
                if not start_date:
                    allocation_obj.start_date = datetime.date.today()
                allocation_obj.save()

                allocation_activate.send(
                    sender=self.__class__, allocation_pk=allocation_obj.pk)
                allocation_users = allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error'])
                for allocation_user in allocation_users:
                    allocation_activate_user.send(
                        sender=self.__class__, allocation_user_pk=allocation_user.pk)

                if EMAIL_ENABLED:
                    template_context = {
                        'center_name': EMAIL_CENTER_NAME,
                        'resource': resource_name,
                        'allocation_url': allocation_url,
                        'signature': EMAIL_SIGNATURE,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                    }

                    email_receiver_list = []
                    for allocation_user in allocation_users:
                        if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                            email_receiver_list.append(
                                allocation_user.user.email)

                    send_email_template(
                        'Allocation Activated',
                        'email/allocation_activated.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                    )

            elif old_status != 'Denied' and new_status == 'Denied':
                allocation_disable.send(
                    sender=self.__class__, allocation_pk=allocation_obj.pk)
                allocation_users = allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error'])
                for allocation_user in allocation_users:
                    allocation_remove_user.send(
                        sender=self.__class__, allocation_user_pk=allocation_user.pk)

                if EMAIL_ENABLED:
                    template_context = {
                        'center_name': EMAIL_CENTER_NAME,
                        'resource': resource_name,
                        'allocation_url': allocation_url,
                        'signature': EMAIL_SIGNATURE,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                    }

                    email_receiver_list = []
                    for allocation_user in allocation_users:
                        if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                            email_receiver_list.append(
                                allocation_user.user.email)

                    send_email_template(
                        'Allocation Denied',
                        'email/allocation_denied.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                    )

            allocation_obj.refresh_from_db()

            messages.success(request, 'Allocation updated!')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))
        else:
            context = self.get_context_data()
            context['form'] = form
            context['allocation'] = allocation_obj

            return render(request, self.template_name, context)


class AllocationListView(LoginRequiredMixin, ListView):

    model = Allocation
    template_name = 'allocation/allocation_list.html'
    context_object_name = 'allocation_list'
    paginate_by = 25

    def get_queryset(self):

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            elif direction == 'des':
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = 'id'

        allocation_search_form = AllocationSearchForm(self.request.GET)

        if allocation_search_form.is_valid():
            data = allocation_search_form.cleaned_data

            if data.get('show_all_allocations') and (self.request.user.is_superuser or self.request.user.has_perm('allocation.can_view_all_allocations')):
                allocations = Allocation.objects.prefetch_related(
                    'project', 'project__pi', 'status',).all().order_by(order_by)
            else:
                allocations = Allocation.objects.prefetch_related('project', 'project__pi', 'status',).filter(
                    Q(project__status__name__in=['New', 'Active', ]) &
                    Q(project__projectuser__user=self.request.user) &
                    Q(project__projectuser__status__name='Active') &
                    Q(allocationuser__user=self.request.user) &
                    Q(allocationuser__status__name='Active')
                ).distinct().order_by(order_by)

            # Project Title
            if data.get('project'):
                allocations = allocations.filter(
                    project__title__icontains=data.get('project'))

            # username
            if data.get('username'):
                allocations = allocations.filter(
                    Q(project__pi__username__icontains=data.get('username')) |
                    Q(allocationuser__user__username__icontains=data.get('username')) &
                    Q(allocationuser__status__name='Active')
                )

            # Resource Type
            if data.get('resource_type'):
                allocations = allocations.filter(
                    resources__resource_type=data.get('resource_type'))

            # Resource Name
            if data.get('resource_name'):
                allocations = allocations.filter(
                    resources__in=data.get('resource_name'))

            # Allocation Attribute Name
            if data.get('allocation_attribute_name') and data.get('allocation_attribute_value'):
                allocations = allocations.filter(
                    Q(allocationattribute__allocation_attribute_type=data.get('allocation_attribute_name')) &
                    Q(allocationattribute__value=data.get(
                        'allocation_attribute_value'))
                )

            # End Date
            if data.get('end_date'):
                allocations = allocations.filter(end_date__lt=data.get(
                    'end_date'), status__name='Active').order_by('end_date')

            # Active from now until date
            if data.get('active_from_now_until_date'):
                allocations = allocations.filter(
                    end_date__gte=date.today())
                allocations = allocations.filter(end_date__lt=data.get(
                    'active_from_now_until_date'), status__name='Active').order_by('end_date')

            # Status
            if data.get('status'):
                allocations = allocations.filter(
                    status__in=data.get('status'))

        else:
            allocations = Allocation.objects.prefetch_related('project', 'project__pi', 'status',).filter(
                Q(allocationuser__user=self.request.user) &
                Q(allocationuser__status__name='Active')
            ).order_by(order_by)

        return allocations.distinct()

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        allocations_count = self.get_queryset().count()
        context['allocations_count'] = allocations_count

        allocation_search_form = AllocationSearchForm(self.request.GET)

        if allocation_search_form.is_valid():
            context['allocation_search_form'] = allocation_search_form
            data = allocation_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, QuerySet):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele.pk)
                    elif hasattr(value, 'pk'):
                        filter_parameters += '{}={}&'.format(key, value.pk)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['allocation_search_form'] = allocation_search_form
        else:
            filter_parameters = ''
            context['allocation_search_form'] = AllocationSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                'order_by=%s&direction=%s&' % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context['expand_accordion'] = 'show'
        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        allocation_list = context.get('allocation_list')
        paginator = Paginator(allocation_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            allocation_list = paginator.page(page)
        except PageNotAnInteger:
            allocation_list = paginator.page(1)
        except EmptyPage:
            allocation_list = paginator.page(paginator.num_pages)

        return context


class AllocationCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AllocationForm
    template_name = 'allocation/allocation_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permission to create a new allocation.')

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))

        if project_obj.needs_review:
            messages.error(
                request, 'You cannot request a new allocation because you have to review your project first.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        if project_obj.status.name in ['Archived', 'Denied', 'Review Pending', 'Expired', ]:
            messages.error(
                request,
                'You cannot request a new allocation for a project with status "{}".'.format(project_obj.status.name)
            )
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        context['project'] = project_obj
        context['request_user_username'] = {'username': self.request.user.username}

        user_resources = get_user_resources(self.request.user)

        # Format:
        # {
        #   field
        #   label
        #   type
        # }
        resource_form = [
            {
                'leverage_multiple_gpus': {},
                'leverage_multiple_gpus_label': {},
                'type': 'radio',
            },
            {
                'for_coursework': {},
                'for_coursework_label': {},
                'type': 'radio',
            },
            {
                'dl_workflow': {},
                'dl_workflow_label': {},
                'type': 'radio',
            },
            {
                'phi_association': {},
                'phi_association_label': {},
                'type': 'radio',
            },
            {
                'system': {},
                'system_label': {},
                'type': 'radio',
            },
            {
                'store_ephi': {},
                'store_ephi_label': {},
                'type': 'radio',
            },
            {
                'access_level': {},
                'access_level_label': {},
                'type': 'radio',
            },
            {
                'applications_list': {},
                'applications_list_label': {},
                'type': 'text',
            },
            {
                'training_or_inference': {},
                'training_or_inference_label': {},
                'type': 'choice',
            },
            {
                'primary_contact': {},
                'primary_contact_label': {},
                'type': 'text',
            },
            {
                'secondary_contact': {},
                'secondary_contact_label': {},
                'type': 'text',
            },
            {
                'department_full_name': {},
                'department_full_name_label': {},
                'type': 'text',
            },
            {
                'department_short_name': {},
                'department_short_name_label': {},
                'type': 'text',
            },
            {
                'fiscal_officer': {},
                'fiscal_officer_label': {},
                'type': 'text',
            },
            {
                'account_number': {},
                'account_number_label': {},
                'type': 'text',
            },
            {
                'sub_account_number': {},
                'sub_account_number_label': {},
                'type': 'text',
            },
            {
                'it_pros': {},
                'it_pros_label': {},
                'type': 'text',
            },
            {
                'devices_ip_addresses': {},
                'devices_ip_addresses_label': {},
                'type': 'text',
            },
            {
                'data_management_plan': {},
                'data_management_plan_label': {},
                'type': 'text',
            },
            {
                'project_directory_name': {},
                'project_directory_name_label': {},
                'type': 'text',
            },
            {
                'first_name': {},
                'first_name_label': {},
                'type': 'text',
            },
            {
                'last_name': {},
                'last_name_label': {},
                'type': 'text',
            },
            {
                'data_manager': {},
                'data_manager_label': {},
                'type': 'text',
            },
            {
                'campus_affiliation': {},
                'campus_affiliation_label': {},
                'type': 'choice',
            },
            {
                'url': {},
                'url_label': {},
                'type': 'text',
            },
            {
                'email': {},
                'email_label': {},
                'type': 'email',
            },
            {
                'faculty_email': {},
                'faculty_email_label': {},
                'type': 'email',
            },
            {
                'start_date': {},
                'start_date_label': {},
                'type': 'date',
            },
            {
                'end_date': {},
                'end_date_label': {},
                'type': 'date',
            },
            {
                'confirm_understanding': {},
                'confirm_understanding_label': {},
                'type': 'checkbox',
            },
            {
                'storage_space': {},
                'storage_space_label': {},
                'type': 'int',
            },
            {
                'storage_space_with_unit': {},
                'storage_space_with_unit_label': {},
                'type': 'int',
            },
            {
                'cost': {},
                'cost_label': {},
                'type': 'int',
            },
            {
                'prorated_cost': {},
                'prorated_cost_label': {},
                'type': 'int',
            },
            {
                'quantity': {},
                'quantity_label': {},
                'type': 'int',
            },
        ]

        resource_special_attributes = [
            {
                'slurm_cluster': {},
                'has_requirement': {},
            }
        ]

        resource_descriptions = {}
        for resource in user_resources:
            resource_descriptions[resource.id] = resource.description

            for attribute in resource_special_attributes:
                keys = list(attribute.keys())
                field = keys[0]
                check = keys[1]
                if resource.resourceattribute_set.filter(resource_attribute_type__name=field).exists():
                    value = resource.resourceattribute_set.get(resource_attribute_type__name=field).value
                    attribute[field][resource.id] = value
                    if project_obj.slurm_account_name != '':
                        attribute[check][resource.id] = 'Yes'
                    else:
                        attribute[check][resource.id] = 'No'

            for field_set in resource_form:
                keys = list(field_set.keys())
                field = keys[0]
                label = keys[1]
                input_type = keys[2]

                # prorated_cost is a special case
                if field == 'prorated_cost':
                    if resource.resourceattribute_set.filter(resource_attribute_type__name='prorated').exists():
                        if resource.resourceattribute_set.get(resource_attribute_type__name='prorated'):
                            if resource.resourceattribute_set.filter(resource_attribute_type__name=label).exists():
                                value = resource.resourceattribute_set.get(
                                    resource_attribute_type__name=label).value
                                field_set[label][resource.id] = mark_safe(
                                    '<strong>{}</strong>'.format(value))

                            if resource.resourceattribute_set.filter(resource_attribute_type__name='cost').exists():
                                field_set[field][resource.id] = compute_prorated_amount(
                                    int(resource.resourceattribute_set.get(resource_attribute_type__name='cost').value)
                                )
                            else:
                                field_set[field][resource.id] = 0
                    continue

                if resource.resourceattribute_set.filter(resource_attribute_type__name=label).exists():
                    value = resource.resourceattribute_set.get(
                        resource_attribute_type__name=label
                    ).value
                    if field_set[input_type] == 'checkbox':
                        field_set[label][resource.id] = mark_safe(
                            '{}'.format(value)
                        )
                    else:
                        field_set[label][resource.id] = mark_safe(
                            '<strong>{}</strong>'.format(value)
                        )

                if field_set[input_type] == 'int':
                    if resource.resourceattribute_set.filter(resource_attribute_type__name=field).exists():
                        value = resource.resourceattribute_set.get(
                            resource_attribute_type__name=field).value
                        if value == '':
                            field_set[field][resource.id] = 0
                        else:
                            field_set[field][resource.id] = int(value)
                else:
                    if resource.resourceattribute_set.filter(resource_attribute_type__name=field).exists():
                        value = resource.resourceattribute_set.get(
                            resource_attribute_type__name=field
                        ).value
                        field_set[field][resource.id] = value

        context['resource_special_attributes'] = resource_special_attributes
        context['resource_form'] = resource_form

        resources_with_eula = {}

        context['AllocationAccountForm'] = AllocationAccountForm()
        context['resource_descriptions'] = resource_descriptions

        context['resources_with_eula'] = resources_with_eula
        context['resources_with_accounts'] = list(Resource.objects.filter(
            name__in=list(ALLOCATION_ACCOUNT_MAPPING.keys())).values_list('id', flat=True))

        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.request.user, self.kwargs.get('project_pk'), **self.get_form_kwargs())

    def calculate_end_date(self, month, day, license_term):
        current_date = datetime.date.today()
        license_end_date = datetime.date(current_date.year, month, day)
        if current_date > license_end_date:
            license_end_date = license_end_date.replace(year=license_end_date.year + 1)

        if license_term == 'current_and_next_year':
            license_end_date = license_end_date.replace(year=license_end_date.year + 1)

        return license_end_date

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        resource_obj = form_data.get('resource')
        justification = form_data.get('justification')
        quantity = form_data.get('quantity', 1)
        storage_space = form_data.get('storage_space')
        storage_space_with_unit = form_data.get('storage_space_with_unit')
        leverage_multiple_gpus = form_data.get('leverage_multiple_gpus')
        dl_workflow = form_data.get('dl_workflow')
        applications_list = form_data.get('applications_list')
        training_or_inference = form_data.get('training_or_inference')
        for_coursework = form_data.get('for_coursework')
        system = form_data.get('system')
        is_grand_challenge = form_data.get('is_grand_challenge')
        grand_challenge_program = form_data.get('grand_challenge_program')
        start_date = form_data.get('start_date')
        end_date = form_data.get('end_date')
        use_indefinitely = form_data.get('use_indefinitely')
        phi_association = form_data.get('phi_association')
        access_level = form_data.get('access_level')
        confirm_understanding = form_data.get('confirm_understanding')
        unit = form_data.get('unit')
        primary_contact = form_data.get('primary_contact')
        secondary_contact = form_data.get('secondary_contact')
        department_full_name = form_data.get('department_full_name')
        department_short_name = form_data.get('department_short_name')
        fiscal_officer = form_data.get('fiscal_officer')
        account_number = form_data.get('account_number')
        sub_account_number = form_data.get('sub_account_number')
        it_pros = form_data.get('it_pros')
        devices_ip_addresses = form_data.get('devices_ip_addresses')
        data_management_plan = form_data.get('data_management_plan')
        project_directory_name = form_data.get('project_directory_name')
        first_name = form_data.get('first_name')
        last_name = form_data.get('last_name')
        campus_affiliation = form_data.get('campus_affiliation')
        email = form_data.get('email')
        url = form_data.get('url')
        faculty_email = form_data.get('faculty_email')
        store_ephi = form_data.get('store_ephi')
        data_manager = form_data.get('data_manager')
        allocation_account = form_data.get('allocation_account', None)
        license_term = form_data.get('license_term', None)

        if resource_obj.resourceattribute_set.filter(resource_attribute_type__name='slurm_cluster').exists():
            if project_obj.slurm_account_name == '':
                form.add_error(None, 'Project must have a Slurm account name for this resource.')
                return self.form_invalid(form)

        total_cost = None
        cost = resource_obj.get_attribute('cost')
        prorated_cost_label = resource_obj.get_attribute('prorated_cost_label')
        if cost is not None:
            cost = int(cost)
            total_cost = cost
            if prorated_cost_label is not None:
                prorated_cost = compute_prorated_amount(cost)
                if license_term == 'current':
                    total_cost = prorated_cost
                elif license_term == 'current_and_next_year':
                    total_cost += prorated_cost

        if end_date is None:
            end_date = project_obj.end_date

        if resource_obj.name == 'RStudio Connect':
            license_end_date = resource_obj.get_attribute('license_end_date')
            if license_end_date is not None:
                month, day, year = license_end_date.split('/')
                end_date = self.calculate_end_date(int(month), int(day), license_term)
        elif resource_obj.name == 'Geode-Projects':
            storage_space_with_unit = str(storage_space_with_unit) + unit
            if use_indefinitely:
                end_date = None
        elif resource_obj.name == 'Priority Boost':
            if use_indefinitely:
                end_date = None

        # A resource is selected that requires an account name selection but user has no account names
        if ALLOCATION_ACCOUNT_ENABLED and resource_obj.name in ALLOCATION_ACCOUNT_MAPPING and AllocationAttributeType.objects.filter(
                name=ALLOCATION_ACCOUNT_MAPPING[resource_obj.name]).exists() and not allocation_account:
            form.add_error(None, format_html(
                'You need to create an account name. Create it by clicking the link under the "Allocation account" field.'))
            return self.form_invalid(form)

        usernames = form_data.get('users')
        if resource_obj.name == 'Slate-Project':
            usernames.append(data_manager)

        usernames.append(project_obj.pi.username)
        usernames.append(self.request.user.username)
        # Remove potential duplicate usernames
        usernames = list(set(usernames))

        # If a resource has a user limit make sure it's not surpassed.
        total_users = len(usernames)
        user_limit = resource_obj.get_attribute("user_limit")
        if user_limit is not None:
            if total_users > int(user_limit):
                form.add_error(None, format_html(
                    'Too many users are being added (total users: {}). The user limit for this resource is {}.'.format(total_users, user_limit)
                ))
                return self.form_invalid(form)

        users = [User.objects.get(username=username) for username in usernames]
        resource_account = resource_obj.get_attribute('check_user_account')
        if resource_account and not resource_obj.check_user_account_exists(self.request.user.username, resource_account):

            form.add_error(
                None,
                format_html('You do not have an account on {}. You will need to create one\
                <a href="https://access.iu.edu/Accounts/Create">here</a> in order to submit a\
                resource request for this resource.'.format(resource_account))
            )
            return self.form_invalid(form)

        denied_users = []
        resource_name = ''
        for user in users:
            username = user.username
            if resource_obj.name == 'Priority Boost':
                if not resource_obj.check_user_account_exists(username, system):
                    denied_users.append(username)
                    resource_name = system
                    users.remove(user)
            else:
                if resource_account is not None:
                    if not resource_obj.check_user_account_exists(username, resource_account):
                        denied_users.append(username)
                        resource_name = resource_account
                        users.remove(user)

        if denied_users:
            messages.warning(self.request, format_html(
                'The following users do not have an account on {} and were not added: {}. Please\
                direct them to\
                <a href="https://access.iu.edu/Accounts/Create">https://access.iu.edu/Accounts/Create</a>\
                to create an account.'
                .format(resource_account, ', '.join(denied_users))
            ))

        if INVOICE_ENABLED and resource_obj.requires_payment:
            allocation_status_obj = AllocationStatusChoice.objects.get(
                name=INVOICE_DEFAULT_STATUS)
            if resource_obj.name == "Slate-Project" and account_number == '':
                # If a Slate-Project request doesnt have an account number then it shouldn't be
                # placed in the invoice list.
                # TODO: Might not be true anymore
                allocation_status_obj = AllocationStatusChoice.objects.get(
                    name='New')
        else:
            allocation_status_obj = AllocationStatusChoice.objects.get(
                name='New')

        allocation_obj = Allocation.objects.create(
            project=project_obj,
            justification=justification,
            quantity=quantity,
            storage_space=storage_space,
            storage_space_with_unit=storage_space_with_unit,
            leverage_multiple_gpus=leverage_multiple_gpus,
            dl_workflow=dl_workflow,
            applications_list=applications_list,
            training_or_inference=training_or_inference,
            for_coursework=for_coursework,
            system=system,
            is_grand_challenge=is_grand_challenge,
            grand_challenge_program=grand_challenge_program,
            start_date=start_date,
            end_date=end_date,
            use_indefinitely=use_indefinitely,
            phi_association=phi_association,
            access_level=access_level,
            confirm_understanding=confirm_understanding,
            primary_contact=primary_contact,
            secondary_contact=secondary_contact,
            department_full_name=department_full_name,
            department_short_name=department_short_name,
            fiscal_officer=fiscal_officer,
            account_number=account_number,
            sub_account_number=sub_account_number,
            it_pros=it_pros,
            devices_ip_addresses=devices_ip_addresses,
            data_management_plan=data_management_plan,
            project_directory_name=project_directory_name,
            total_cost=total_cost,
            first_name=first_name,
            last_name=last_name,
            campus_affiliation=campus_affiliation,
            email=email,
            url=url,
            faculty_email=faculty_email,
            store_ephi=store_ephi,
            data_manager=data_manager,
            status=allocation_status_obj
        )

        if ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT:
            allocation_obj.is_changeable = True
            allocation_obj.save()

        allocation_obj.resources.add(resource_obj)

        if resource_obj.resourceattribute_set.filter(resource_attribute_type__name='slurm_cluster').exists():
            if project_obj.slurm_account_name:
                value = project_obj.slurm_account_name
                if resource_obj.name == 'Carbonate DL':
                    value = 'DL_' + project_obj.slurm_account_name
                elif resource_obj.name == 'Carbonate GPU':
                    value = 'GPU_' + project_obj.slurm_account_name

                slurm_account_name_attribute_type = AllocationAttributeType.objects.get(
                    name='slurm_account_name'
                )
                AllocationAttribute.objects.create(
                    allocation_attribute_type=slurm_account_name_attribute_type,
                    allocation=allocation_obj,
                    value=value
                )

        if ALLOCATION_ACCOUNT_ENABLED and allocation_account and resource_obj.name in ALLOCATION_ACCOUNT_MAPPING:

            allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                name=ALLOCATION_ACCOUNT_MAPPING[resource_obj.name])
            AllocationAttribute.objects.create(
                allocation_attribute_type=allocation_attribute_type_obj,
                allocation=allocation_obj,
                value=allocation_account
            )

        for linked_resource in resource_obj.linked_resources.all():
            allocation_obj.resources.add(linked_resource)

        new_user_requests = []
        allocation_user_active_status_choice = AllocationUserStatusChoice.objects.get(name='Active')
        requires_user_request = allocation_obj.get_parent_resource.get_attribute('requires_user_request')
        requestor_user = User.objects.get(username=self.request.user.username)
        if requires_user_request is not None and requires_user_request == 'Yes':
            allocation_user_pending_status_choice = AllocationUserStatusChoice.objects.get(
                name='Pending - Add'
            )
            for user in users:
                if user.username == self.request.user.username or user.username == data_manager or user.username == allocation_obj.project.pi.username:
                    allocation_user_obj = AllocationUser.objects.create(
                        allocation=allocation_obj,
                        user=user,
                        status=allocation_user_active_status_choice
                    )
                else:
                    allocation_user_obj = AllocationUser.objects.create(
                        allocation=allocation_obj,
                        user=user,
                        status=allocation_user_pending_status_choice
                    )

                    allocation_obj.create_user_request(
                        requestor_user=requestor_user,
                        allocation_user=allocation_user_obj,
                        allocation_user_status=allocation_user_pending_status_choice
                    )

                    new_user_requests.append(user.username)
        else:
            for user in users:
                allocation_user_obj = AllocationUser.objects.create(
                    allocation=allocation_obj,
                    user=user,
                    status=allocation_user_active_status_choice
                )

        pi_name = '{} {} ({})'.format(allocation_obj.project.pi.first_name,
                                      allocation_obj.project.pi.last_name, allocation_obj.project.pi.username)
        resource_name = allocation_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        url = '{}{}'.format(domain_url, reverse('allocation-request-list'))

        if EMAIL_ENABLED:
            template_context = {
                'pi': pi_name,
                'resource': resource_name,
                'url': url
            }

            email_recipient = get_email_recipient_from_groups(
                allocation_obj.get_parent_resource.review_groups.all()
            )

            send_email_template(
                'New allocation request: {} - {}'.format(
                    pi_name, resource_name),
                'email/new_allocation_request.txt',
                template_context,
                EMAIL_SENDER,
                [email_recipient, ]
            )

            if new_user_requests:
                send_allocation_user_request_email(
                    self.request, new_user_requests, resource_name, email_recipient
                )

        return super().form_valid(form)

    def reverse_with_params(self, path, **kwargs):
        return path + '?' + urllib.parse.urlencode(kwargs)

    def get_success_url(self):
        return self.reverse_with_params(
            reverse(
                'project-detail',
                kwargs={'pk': self.kwargs.get('project_pk')}
            ),
            allocation_submitted=True
        )


class AllocationAddUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_add_users.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.get_parent_resource.name == 'Slate-Project':
            if allocation_obj.data_manager != self.request.user.username:
                messages.error(
                    self.request,
                    'Only the Data Manager can add users to this resource.'
                )
                return False

        if allocation_obj.project.pi == self.request.user:
            return True

        if allocation_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permission to add users to the allocation.')

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.is_locked and not self.request.user.is_superuser:
            messages.error(
                request, 'You cannot modify this allocation because it is locked! Contact support for details.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.status.name not in ['Active', 'New', 'Renewal Requested', 'Payment Pending', 'Payment Requested', 'Paid']:
            messages.error(
                request,
                'You cannot add users to an allocation with status "{}".'.format(allocation_obj.status.name)
            )
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_users_to_add(self, allocation_obj):
        active_users_in_project = list(allocation_obj.project.projectuser_set.filter(
            status__name='Active').values_list('user__username', flat=True))
        users_already_in_allocation = list(allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed']).values_list('user__username', flat=True))

        missing_users = list(set(active_users_in_project) -
                             set(users_already_in_allocation))
        missing_users = User.objects.filter(username__in=missing_users).exclude(
            pk=allocation_obj.project.pi.pk)

        users_to_add = [

            {'username': user.username,
             'first_name': user.first_name,
             'last_name': user.last_name,
             'email': user.email, }

            for user in missing_users
        ]

        return users_to_add

    def get_list_of_users_to_add(self, formset):
        users = []
        for form in formset:
            user_form_data = form.cleaned_data
            if user_form_data['selected']:
                users.append(user_form_data.get('username'))

        return users

    def get_total_users_in_allocation_if_added(self, allocation_obj, formset):
        total_users = len(list(allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed']).values_list('user__username', flat=True)))
        total_users += len(self.get_list_of_users_to_add(formset))

        return total_users

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_to_add = self.get_users_to_add(allocation_obj)
        context = {}

        if users_to_add:
            formset = formset_factory(
                AllocationAddUserForm, max_num=len(users_to_add))
            formset = formset(initial=users_to_add, prefix='userform')
            context['formset'] = formset

        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_to_add = self.get_users_to_add(allocation_obj)
        allocation_user_limit = allocation_obj.get_parent_resource.get_attribute("user_limit")

        formset = formset_factory(
            AllocationAddUserForm, max_num=len(users_to_add))
        formset = formset(request.POST, initial=users_to_add,
                          prefix='userform')

        added_users = []
        denied_users = []
        if formset.is_valid():
            if allocation_user_limit is not None:
                # The users_to_add variable is not an actual list of users to add. The users listed
                # are the remaining users in the project that are not in the allocation. We have to
                # cycle through the formset and increment the total user count for each user that
                # has been selected in the list.
                total_users = self.get_total_users_in_allocation_if_added(allocation_obj, formset)
                if total_users > int(allocation_user_limit):
                    messages.error(request, "Only {} users are allowed on this resource. Users were not added. (Total users counted: {})".format(allocation_user_limit, total_users))
                    return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

            allocation_user_active_status_choice = AllocationUserStatusChoice.objects.get(
                name='Active')
            allocation_user_pending_add_status_choice = AllocationUserStatusChoice.objects.get(
                name='Pending - Add'
            )

            allocation_user_status_choice = allocation_user_active_status_choice
            requires_user_request = allocation_obj.get_parent_resource.get_attribute('requires_user_request')

            if requires_user_request is not None and requires_user_request == 'Yes':
                allocation_user_status_choice = allocation_user_pending_add_status_choice

            requestor_user = User.objects.get(username=request.user)
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

                    username = user_obj.username
                    if allocation_obj.check_user_account_exists_on_resource(username):
                        added_users.append(username)
                    else:
                        denied_users.append(username)
                        continue

                    if allocation_obj.allocationuser_set.filter(user=user_obj).exists():
                        allocation_user_obj = allocation_obj.allocationuser_set.get(
                            user=user_obj)
                        allocation_user_obj.status = allocation_user_status_choice
                        allocation_user_obj.save()
                    else:
                        allocation_user_obj = AllocationUser.objects.create(
                            allocation=allocation_obj, user=user_obj, status=allocation_user_status_choice)

                    allocation_obj.create_user_request(
                        requestor_user=requestor_user,
                        allocation_user=allocation_user_obj,
                        allocation_user_status=allocation_user_status_choice
                    )

                    allocation_activate_user.send(sender=self.__class__,
                                                  allocation_user_pk=allocation_user_obj.pk)
            if added_users:

                if allocation_user_status_choice.name == 'Pending - Add':
                    email_recipient = get_email_recipient_from_groups(
                        allocation_obj.get_parent_resource.review_groups.all()
                    )
                    send_allocation_user_request_email(
                        self.request,
                        added_users,
                        allocation_obj.get_parent_resource.name,
                        email_recipient
                    )
                    messages.success(
                        request,
                        'Pending addition of user(s) {} to allocation.'.format(', '.join(added_users))
                    )
                else:
                    messages.success(
                        request,
                        'Added user(s) {} to allocation.'.format(', '.join(added_users))
                    )

            if denied_users:
                user_text = 'user'
                if len(denied_users) > 1:
                    user_text += 's'
                messages.warning(request, format_html(
                    'Did not add {} {} to allocation. An account is needed for this resource.\
                    Please direct them to\
                    <a href="https://access.iu.edu/Accounts/Create">https://access.iu.edu/Accounts/Create</a>\
                    to create one.'.format(user_text, ', '.join(denied_users))
                    )
                )
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationRemoveUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_remove_users.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.get_parent_resource.name == 'Slate-Project':
            if allocation_obj.data_manager != self.request.user.username:
                messages.error(
                    self.request,
                    'Only the Data Manager can remove users to this resource.'
                )
                return False

        if allocation_obj.project.pi == self.request.user:
            return True

        if allocation_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permission to remove users from allocation.')

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.is_locked and not self.request.user.is_superuser:
            messages.error(
                request, 'You cannot modify this allocation because it is locked! Contact support for details.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.status.name not in ['Active', 'New', 'Renewal Requested', 'Paid', 'Payment Pending', 'Payment Requested']:
            messages.error(
                request,
                'You cannot remove users from an allocation with status "{}".'.format(allocation_obj.status.name)
            )
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_users_to_remove(self, allocation_obj):
        users_to_remove = list(allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed', 'Error', 'Pending - Add', 'Pending - Remove']
        ).values_list('user__username', flat=True))

        users_to_remove = User.objects.filter(username__in=users_to_remove).exclude(
            pk__in=[allocation_obj.project.pi.pk, self.request.user.pk])
        users_to_remove = [

            {'username': user.username,
             'first_name': user.first_name,
             'last_name': user.last_name,
             'email': user.email, }

            for user in users_to_remove
        ]

        return users_to_remove

    def check_data_manager_exists(self, allocation_obj):
        if allocation_obj.data_manager:
            if allocation_obj.get_parent_resource.name == 'Slate-Project':
                return True

        return False

    def get_disable_select_list(self, allocation_obj, users_to_remove):
        """
        Gets a list that determines if a user can be removed by disabling the
        ProjectRemoveUserForm's selected field.
        """
        disable_select_list = [False] * len(users_to_remove)
        if not self.check_data_manager_exists:
            return disable_select_list

        for i, user in enumerate(users_to_remove):
            if user['username'] == allocation_obj.data_manager:
                disable_select_list[i] = True

        return disable_select_list

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_to_remove = self.get_users_to_remove(allocation_obj)
        context = {}

        if users_to_remove:
            formset = formset_factory(
                AllocationRemoveUserForm,
                max_num=len(users_to_remove),
                formset=AllocationRemoveUserFormset
            )
            formset = formset(
                initial=users_to_remove,
                prefix='userform',
                form_kwargs={
                    'disable_selected': self.get_disable_select_list(
                        allocation_obj,
                        users_to_remove
                    )
                }
            )
            context['formset'] = formset

        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_to_remove = self.get_users_to_remove(allocation_obj)

        formset = formset_factory(
            AllocationRemoveUserForm,
            max_num=len(users_to_remove),
            formset=AllocationRemoveUserFormset
        )

        formset = formset(
            request.POST,
            initial=users_to_remove,
            prefix='userform',
            form_kwargs={
                'disable_selected': self.get_disable_select_list(
                    allocation_obj,
                    users_to_remove
                )
            }
        )

        remove_users_count = 0

        if formset.is_valid():
            allocation_user_removed_status_choice = AllocationUserStatusChoice.objects.get(
                name='Removed')
            allocation_user_pending_remove_status_choice = AllocationUserStatusChoice.objects.get(
                name='Pending - Remove'
            )

            allocation_user_status_choice = allocation_user_removed_status_choice
            requires_user_request = allocation_obj.get_parent_resource.get_attribute('requires_user_request')

            if requires_user_request is not None and requires_user_request == 'Yes':
                allocation_user_status_choice = allocation_user_pending_remove_status_choice

            removed_users = []
            requestor_user = User.objects.get(username=request.user)
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    remove_users_count += 1

                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))
                    if allocation_obj.project.pi == user_obj:
                        continue

                    removed_users.append(user_obj.username)

                    allocation_user_obj = allocation_obj.allocationuser_set.get(
                        user=user_obj)
                    allocation_user_obj.status = allocation_user_status_choice
                    allocation_user_obj.save()
                    allocation_remove_user.send(sender=self.__class__,
                                                allocation_user_pk=allocation_user_obj.pk)

                    allocation_obj.create_user_request(
                        requestor_user=requestor_user,
                        allocation_user=allocation_user_obj,
                        allocation_user_status=allocation_user_status_choice
                    )

            if removed_users:
                if allocation_user_status_choice.name == 'Pending - Remove':
                    email_recipient = get_email_recipient_from_groups(
                        allocation_obj.get_parent_resource.review_groups.all()
                    )
                    send_allocation_user_request_email(
                        self.request,
                        removed_users,
                        allocation_obj.get_parent_resource.name,
                        email_recipient
                    )
                    messages.success(
                        request, 'Pending removal of user(s) {} from allocation.'.format(', '.join(removed_users))
                    )
                else:
                    messages.success(
                        request, 'Removed user(s) {} from allocation.'.format(', '.join(removed_users))
                    )

        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationAttribute
    # fields = ['allocation_attribute_type', 'value', 'is_private', ]
    fields = '__all__'
    template_name = 'allocation/allocation_allocationattribute_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True
        else:
            messages.error(
                self.request, 'You do not have permission to add allocation attributes.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        context['allocation'] = allocation_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        initial['allocation'] = allocation_obj
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields['allocation'].widget = forms.HiddenInput()
        return form

    def get_success_url(self):
        return reverse('allocation-detail', kwargs={'pk': self.kwargs.get('pk')})


class AllocationAttributeDeleteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_allocationattribute_delete.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True
        else:
            messages.error(
                self.request, 'You do not have permission to delete allocation attributes.')

    def get_allocation_attributes_to_delete(self, allocation_obj):

        allocation_attributes_to_delete = AllocationAttribute.objects.filter(
            allocation=allocation_obj)
        allocation_attributes_to_delete = [

            {'pk': attribute.pk,
             'name': attribute.allocation_attribute_type.name,
             'value': attribute.value,
             }

            for attribute in allocation_attributes_to_delete
        ]

        return allocation_attributes_to_delete

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        allocation_attributes_to_delete = self.get_allocation_attributes_to_delete(
            allocation_obj)
        context = {}

        if allocation_attributes_to_delete:
            formset = formset_factory(AllocationAttributeDeleteForm, max_num=len(
                allocation_attributes_to_delete))
            formset = formset(
                initial=allocation_attributes_to_delete, prefix='attributeform')
            context['formset'] = formset
        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        allocation_attributes_to_delete = self.get_allocation_attributes_to_delete(
            allocation_obj)

        formset = formset_factory(AllocationAttributeDeleteForm, max_num=len(
            allocation_attributes_to_delete))
        formset = formset(
            request.POST, initial=allocation_attributes_to_delete, prefix='attributeform')

        attributes_deleted_count = 0

        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data['selected']:

                    attributes_deleted_count += 1

                    allocation_attribute = AllocationAttribute.objects.get(
                        pk=form_data['pk'])
                    allocation_attribute.delete()

            messages.success(request, 'Deleted {} attributes from allocation.'.format(
                attributes_deleted_count))
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationUserNote
    fields = '__all__'
    template_name = 'allocation/allocation_note_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True
        else:
            messages.error(
                self.request, 'You do not have permission to add allocation notes.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        context['allocation'] = allocation_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        author = self.request.user
        initial['allocation'] = allocation_obj
        initial['author'] = author
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields['allocation'].widget = forms.HiddenInput()
        form.fields['author'].widget = forms.HiddenInput()
        form.order_fields([ 'allocation', 'author', 'note', 'is_private' ])
        return form

    def get_success_url(self):
        return reverse('allocation-detail', kwargs={'pk': self.kwargs.get('pk')})


class AllocationRequestListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_request_list.html'
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_allocation_requests'):
            return True

        messages.error(
            self.request, 'You do not have permission to review allocation requests.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_list = Allocation.objects.filter(
            status__name__in=['New', 'Renewal Requested', 'Paid', ],
            resources__review_groups__in=list(self.request.user.groups.all())
        ).exclude(project__status__name__in=['Review Pending', 'Archived'])
        context['allocation_list'] = allocation_list
        context['PROJECT_ENABLE_PROJECT_REVIEW'] = PROJECT_ENABLE_PROJECT_REVIEW
        context['ALLOCATION_DEFAULT_ALLOCATION_LENGTH'] = ALLOCATION_DEFAULT_ALLOCATION_LENGTH
        return context


class AllocationActivateRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_allocation_requests'):
            return True

        messages.error(
            self.request, 'You do not have permission to activate a allocation request.')

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=kwargs.get('pk'))
        project_obj = allocation_obj.project

        if project_obj.status.name != 'Active':
            messages.error(request, 'Project must be approved first before you can approve this allocation!')
            return HttpResponseRedirect(reverse('allocation-request-list'))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        allocation_status_active_obj = AllocationStatusChoice.objects.get(
            name='Active')
        start_date = datetime.datetime.now()

        allocation_obj.status = allocation_status_active_obj
        if not allocation_obj.start_date:
            allocation_obj.start_date = start_date
        allocation_obj.save()

        messages.success(request, 'Allocation to {} has been ACTIVATED for {} {} ({})'.format(
            allocation_obj.get_parent_resource,
            allocation_obj.project.pi.first_name,
            allocation_obj.project.pi.last_name,
            allocation_obj.project.pi.username)
        )

        resource_name = allocation_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        allocation_url = '{}{}'.format(domain_url, reverse(
            'allocation-detail', kwargs={'pk': allocation_obj.pk}))

        allocation_activate.send(
            sender=self.__class__, allocation_pk=allocation_obj.pk)
        allocation_users = allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error'])
        for allocation_user in allocation_users:
            allocation_activate_user.send(
                sender=self.__class__, allocation_user_pk=allocation_user.pk)

        if EMAIL_ENABLED:
            email_receiver_list = []

            for allocation_user in allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                allocation_activate_user.send(
                    sender=self.__class__, allocation_user_pk=allocation_user.pk)
                if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                    email_receiver_list.append(allocation_user.user.email)

            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'allocation_url': allocation_url,
                'signature': EMAIL_SIGNATURE,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
            }

            resource_email_template_lookup_table = {
                'Carbonate DL': {
                    'template': 'email/allocation_carbonate_dl_activated.txt',
                    'template_context': {
                        'help_url': 'radl@iu.edu',
                    },
                },
                'Carbonate GPU': {
                    'template': 'email/allocation_carbonate_gpu_activated.txt',
                    'template_context': {
                        'help_url': 'radl@iu.edu',
                    },
                },
            }

            resource_email_template = resource_email_template_lookup_table.get(
                allocation_obj.get_parent_resource.name
            )
            if resource_email_template is None:
                email_template = 'email/allocation_activated.txt'
            else:
                email_template = resource_email_template['template']
                template_context.update(resource_email_template['template_context'])

            send_email_template(
                'Allocation Activated',
                email_template,
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )

        prev_url = self.request.META.get('HTTP_REFERER')
        if 'request-list' in prev_url:
            return HttpResponseRedirect(reverse('allocation-request-list'))
        else:
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationDenyRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_allocation_requests'):
            return True

        messages.error(
            self.request, 'You do not have permission to deny a allocation request.')

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=kwargs.get('pk'))
        project_obj = allocation_obj.project

        if project_obj.status.name != 'Active':
            messages.error(request, 'Project must be approved first before you can deny this allocation!')
            return HttpResponseRedirect(reverse('allocation-request-list'))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        allocation_status_denied_obj = AllocationStatusChoice.objects.get(
            name='Denied')

        allocation_obj.status = allocation_status_denied_obj
        allocation_obj.start_date = None
        allocation_obj.end_date = None
        allocation_obj.save()

        messages.success(request, 'Allocation to {} has been DENIED for {} {} ({})'.format(
            allocation_obj.resources.first(),
            allocation_obj.project.pi.first_name,
            allocation_obj.project.pi.last_name,
            allocation_obj.project.pi.username)
        )

        resource_name = allocation_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        allocation_url = '{}{}'.format(domain_url, reverse(
            'allocation-detail', kwargs={'pk': allocation_obj.pk}))

        allocation_disable.send(
            sender=self.__class__, allocation_pk=allocation_obj.pk)
        allocation_users = allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error'])
        for allocation_user in allocation_users:
            allocation_remove_user.send(
                sender=self.__class__, allocation_user_pk=allocation_user.pk)

        if EMAIL_ENABLED:
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'allocation_url': allocation_url,
                'signature': EMAIL_SIGNATURE,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
            }

            email_receiver_list = []
            for allocation_user in allocation_users:
                if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                    email_receiver_list.append(allocation_user.user.email)

            send_email_template(
                'Allocation Denied',
                'email/allocation_denied.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )
        if 'request-list' in request.path:
            return HttpResponseRedirect(reverse('allocation-request-list'))
        else:
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationRenewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_renew.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.project.pi == self.request.user:
            return True

        if allocation_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permission to renew allocation.')
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if not ALLOCATION_ENABLE_ALLOCATION_RENEWAL:
            messages.error(
                request, 'Allocation renewal is disabled. Request a new allocation to this resource if you want to continue using it after the active until date.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.status.name not in ['Active', ]:
            messages.error(request, 'You cannot renew an allocation with status "{}".'.format(
                allocation_obj.status.name))
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.project.needs_review:
            messages.error(
                request, 'You cannot renew your allocation because you have to review your project first.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': allocation_obj.project.pk}))

        if allocation_obj.expires_in > 30:
            messages.error(
                request, 'It is too soon to review your allocation.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_users_in_allocation(self, allocation_obj):
        users_in_allocation = allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed']).exclude(user__pk__in=[allocation_obj.project.pi.pk, self.request.user.pk]).order_by('user__username')

        users = [

            {'username': allocation_user.user.username,
             'first_name': allocation_user.user.first_name,
             'last_name': allocation_user.user.last_name,
             'email': allocation_user.user.email, }

            for allocation_user in users_in_allocation
        ]

        return users

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_in_allocation = self.get_users_in_allocation(
            allocation_obj)
        context = {}

        if users_in_allocation:
            formset = formset_factory(
                AllocationReviewUserForm, max_num=len(users_in_allocation))
            formset = formset(initial=users_in_allocation, prefix='userform')
            context['formset'] = formset

            context['resource_eula'] = {}
            if allocation_obj.get_parent_resource.resourceattribute_set.filter(resource_attribute_type__name='eula').exists():
                value = allocation_obj.get_parent_resource.resourceattribute_set.get(resource_attribute_type__name='eula').value
                context['resource_eula'].update({'eula': value})

        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_in_allocation = self.get_users_in_allocation(
            allocation_obj)

        formset = formset_factory(
            AllocationReviewUserForm, max_num=len(users_in_allocation))
        formset = formset(
            request.POST, initial=users_in_allocation, prefix='userform')

        allocation_renewal_requested_status_choice = AllocationStatusChoice.objects.get(
            name='Renewal Requested')
        allocation_user_removed_status_choice = AllocationUserStatusChoice.objects.get(
            name='Removed')
        project_user_remove_status_choice = ProjectUserStatusChoice.objects.get(
            name='Removed')

        allocation_obj.status = allocation_renewal_requested_status_choice
        allocation_obj.save()

        if not users_in_allocation or formset.is_valid():

            if users_in_allocation:
                for form in formset:
                    user_form_data = form.cleaned_data
                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))
                    user_status = user_form_data.get('user_status')

                    if user_status == 'keep_in_project_only':
                        allocation_user_obj = allocation_obj.allocationuser_set.get(
                            user=user_obj)
                        allocation_user_obj.status = allocation_user_removed_status_choice
                        allocation_user_obj.save()

                        allocation_remove_user.send(
                            sender=self.__class__, allocation_user_pk=allocation_user_obj.pk)

                    elif user_status == 'remove_from_project':
                        for active_allocation in allocation_obj.project.allocation_set.filter(status__name__in=(
                            'Active', 'Denied', 'New', 'Paid', 'Payment Pending',
                                'Payment Requested', 'Payment Declined', 'Renewal Requested', 'Unpaid',)):

                            allocation_user_obj = active_allocation.allocationuser_set.get(
                                user=user_obj)
                            allocation_user_obj.status = allocation_user_removed_status_choice
                            allocation_user_obj.save()
                            allocation_remove_user.send(
                                sender=self.__class__, allocation_user_pk=allocation_user_obj.pk)

                        project_user_obj = ProjectUser.objects.get(
                            project=allocation_obj.project,
                            user=user_obj)
                        project_user_obj.status = project_user_remove_status_choice
                        project_user_obj.save()

            pi_name = '{} {} ({})'.format(allocation_obj.project.pi.first_name,
                                          allocation_obj.project.pi.last_name, allocation_obj.project.pi.username)
            resource_name = allocation_obj.get_parent_resource
            domain_url = get_domain_url(self.request)
            url = '{}{}'.format(domain_url, reverse(
                'allocation-request-list'))

            if EMAIL_ENABLED:
                template_context = {
                    'pi': pi_name,
                    'resource': resource_name,
                    'url': url
                }

                email_recipient = get_email_recipient_from_groups(
                    allocation_obj.get_parent_resource.review_groups.all()
                )

                send_email_template(
                    'Allocation renewed: {} - {}'.format(
                        pi_name, resource_name),
                    'email/allocation_renewed.txt',
                    template_context,
                    EMAIL_SENDER,
                    [email_recipient, ]
                )

            messages.success(request, 'Allocation renewed successfully')
        else:
            if not formset.is_valid():
                for error in formset.errors:
                    messages.error(request, error)
        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': allocation_obj.project.pk}))


class AllocationInvoiceListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Allocation
    template_name = 'allocation/allocation_invoice_list.html'
    context_object_name = 'allocation_list'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_manage_invoice'):
            return True

        messages.error(
            self.request, 'You do not have permission to manage invoices.')
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['AllocationInvoiceExportForm'] = AllocationInvoiceExportForm()
        return context

    def get_queryset(self):

        allocations = Allocation.objects.filter(
            status__name__in=['Paid', 'Payment Pending', 'Payment Requested', 'Payment Declined', ],
            resources__review_groups__in=list(self.request.user.groups.all())
        )
        return allocations


# class AllocationAllInvoicesListView(AllocationInvoiceListView):
#     template_name = 'allocation/allocation_all_invoices_list.html'

#     def get_queryset(self):
#         allocations = Allocation.objects.filter(
#             resources__requires_payment=True
#         )

#         return allocations


class AllocationInvoiceDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Allocation
    template_name = 'allocation/allocation_invoice_detail.html'
    context_object_name = 'allocation'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_manage_invoice'):
            return True

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        initial_data = {
            'status': allocation_obj.status,
        }

        form = AllocationInvoiceUpdateForm(initial=initial_data)

        context = self.get_context_data()
        context['form'] = form
        context['allocation'] = allocation_obj

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        initial_data = {
            'status': allocation_obj.status,
        }
        form = AllocationInvoiceUpdateForm(
            request.POST, initial=initial_data)

        if form.is_valid():
            form_data = form.cleaned_data
            status = form_data.get('status')

            if initial_data.get('status') != status and allocation_obj.project.status.name != "Active":
                messages.error(request, 'Project must be approved first before you can update this allocation\'s status!')
                return HttpResponseRedirect(reverse('allocation-invoice-detail', kwargs={'pk': pk}))

            allocation_obj.status = status
            allocation_obj.save()
            messages.success(request, 'Allocation updated!')
        else:
            for error in form.errors:
                messages.error(request, error)
        return HttpResponseRedirect(reverse('allocation-invoice-detail', kwargs={'pk': pk}))


class AllocationAddInvoiceNoteView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationUserNote
    template_name = 'allocation/allocation_add_invoice_note.html'
    fields = ('is_private', 'note',)

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_manage_invoice'):
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        context['allocation'] = allocation_obj
        return context

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        obj = form.save(commit=False)
        obj.author = self.request.user
        obj.allocation = allocation_obj
        obj.save()
        allocation_obj.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('allocation-invoice-detail', kwargs={'pk': self.object.allocation.pk})


class AllocationUpdateInvoiceNoteView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = AllocationUserNote
    template_name = 'allocation/allocation_update_invoice_note.html'
    fields = ('is_private', 'note',)

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_manage_invoice'):
            return True

    def get_success_url(self):
        return reverse_lazy('allocation-invoice-detail', kwargs={'pk': self.object.allocation.pk})


class AllocationDeleteInvoiceNoteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_delete_invoice_note.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_manage_invoice'):
            return True

    def get_notes_to_delete(self, allocation_obj):

        notes_to_delete = [
            {
                'pk': note.pk,
                'note': note.note,
                'author':  note.author.username,
            }
            for note in allocation_obj.allocationusernote_set.all()
        ]

        return notes_to_delete

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        notes_to_delete = self.get_notes_to_delete(allocation_obj)
        context = {}
        if notes_to_delete:
            formset = formset_factory(
                AllocationInvoiceNoteDeleteForm, max_num=len(notes_to_delete))
            formset = formset(initial=notes_to_delete, prefix='noteform')
            context['formset'] = formset
        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        notes_to_delete = self.get_notes_to_delete(allocation_obj)

        formset = formset_factory(
            AllocationInvoiceNoteDeleteForm, max_num=len(notes_to_delete))
        formset = formset(
            request.POST, initial=notes_to_delete, prefix='noteform')

        if formset.is_valid():
            for form in formset:
                note_form_data = form.cleaned_data
                if note_form_data['selected']:
                    note_obj = AllocationUserNote.objects.get(
                        pk=note_form_data.get('pk'))
                    note_obj.delete()
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse_lazy('allocation-invoice-detail', kwargs={'pk': allocation_obj.pk}))


class AllocationAccountCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationAccount
    template_name = 'allocation/allocation_allocationaccount_create.html'
    form_class = AllocationAccountForm

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not ALLOCATION_ACCOUNT_ENABLED:
            return False
        elif self.request.user.is_superuser:
            return True
        elif self.request.user.userprofile.is_pi:
            return True
        else:
            messages.error(
                self.request, 'You do not have permission to add allocation attributes.')
            return False

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        else:
            return response

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        if self.request.is_ajax():
            data = {
                'pk': self.object.pk,
            }
            return JsonResponse(data)
        else:
            return response

    def get_success_url(self):
        return reverse_lazy('allocation-account-list')


class AllocationAccountListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = AllocationAccount
    template_name = 'allocation/allocation_account_list.html'
    context_object_name = 'allocationaccount_list'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if not ALLOCATION_ACCOUNT_ENABLED:
            return False
        elif self.request.user.is_superuser:
            return True
        elif self.request.user.userprofile.is_pi:
            return True
        else:
            messages.error(
                self.request, 'You do not have permission to manage invoices.')
            return False

    def get_queryset(self):
        return AllocationAccount.objects.filter(user=self.request.user)


class AllocationInvoiceExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_manage_invoice'):
            return True

        messages.error(self.request, 'You do not have permission to download invoices.')

    def post(self, request):
        file_name = request.POST["file_name"]
        resource = request.POST["resource"]

        initial_data = {
            'file_name': file_name,
            'resource': resource
        }
        form = AllocationInvoiceExportForm(
            request.POST, initial=initial_data)

        if form.is_valid():
            data = form.cleaned_data
            file_name = data.get('file_name')
            resource = data.get('resource')

            if file_name[-4:] != ".csv":
                file_name += ".csv"

            invoices = Allocation.objects.prefetch_related('project', 'status').filter(
                Q(status__name__in=['Payment Pending', ]) &
                Q(resources__name=resource)
            ).order_by('-created')

            rows = []
            if resource == "RStudio Connect":
                header = [
                    'Name',
                    'Account*',
                    'Object*',
                    'Sub-Acct',
                    'Product',
                    'Quantity',
                    'Unit cost',
                    'Amount*',
                    'Invoice',
                    'Line Description',
                    'Income Account',
                    'Income Sub-acct',
                    'Income Object Code',
                    'Income sub-object code',
                    'Project',
                    'Org Ref ID'
                ]

                for invoice in invoices:
                    row = [
                        ' '.join((invoice.project.pi.first_name, invoice.project.pi.last_name)),
                        invoice.account_number,
                        '4616',
                        invoice.sub_account_number,
                        '',
                        1,
                        '',
                        invoice.total_cost,
                        '',
                        'RStudio Connect FY 22',
                        '63-101-08',
                        'SMSAL',
                        1500,
                        '',
                        '',
                        ''
                    ]

                    rows.append(row)
                rows.insert(0, header)
            elif resource == "Slate-Project":
                header = [
                    'Name',
                    'Account*'
                ]

                for invoice in invoices:
                    row = [
                        ' '.join((invoice.project.pi.first_name, invoice.project.pi.last_name)),
                        invoice.account_number
                    ]

                    rows.append(row)
                rows.insert(0, header)

            pseudo_buffer = Echo()
            writer = csv.writer(pseudo_buffer)
            response = StreamingHttpResponse(
                (writer.writerow(row) for row in rows),
                content_type='text/csv'
            )
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
        else:
            messages.error(
                request,
                'Please correct the errors for the following fields: {}'
                .format(' '.join(form.errors))
            )
            return HttpResponseRedirect(reverse('allocation-invoice-list'))


class AllocationUserRequestListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_user_request_list.html'
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.change_allocationuserstatuschoice'):
            return True

        messages.error(self.request, 'You do not have access to view allocation user requests.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_list'] = AllocationUserRequest.objects.filter(
            status__name='Pending',
            allocation_user__allocation__resources__review_groups__in=list(self.request.user.groups.all())
        )

        return context


class AllocationUserApproveRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.change_allocationuserstatuschoice'):
            return True

        messages.error('You do not have access to approve allocation user requests.')

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        allocation_user_request = get_object_or_404(AllocationUserRequest, pk=pk)
        allocation_user = allocation_user_request.allocation_user

        current_status = allocation_user.status.name
        action = current_status.split(' ')[2]

        allocation_user_status_choice = AllocationUserStatusChoice.objects.get(
            name='Removed'
        )
        if action == 'Add':
            allocation_user_status_choice = AllocationUserStatusChoice.objects.get(
                name='Active'
            )

        allocation_user_request_status_choice = AllocationUserRequestStatusChoice.objects.get(
            name='Approved'
        )

        allocation_user.status = allocation_user_status_choice
        allocation_user.save()

        allocation_user_request.status = allocation_user_request_status_choice
        allocation_user_request.save()

        if EMAIL_ENABLED:
            domain_url = get_domain_url(request)
            url = '{}{}'.format(domain_url, reverse(
                'allocation-detail', kwargs={'pk': allocation_user.allocation.pk})
            )
            template_context = {
                'user': allocation_user.user.username,
                'project': allocation_user.allocation.project.title,
                'allocation': allocation_user.allocation.get_parent_resource,
                'url': url,
            }

            if action == 'Add':
                email_receiver_list = [
                    allocation_user.user.email,
                    allocation_user_request.requestor_user.email
                ]

                send_email_template(
                    'Add User Request Approved',
                    'email/add_allocation_user_request_approved.txt',
                    template_context,
                    EMAIL_SENDER,
                    email_receiver_list
                )
            else:
                email_receiver_list = [
                    allocation_user_request.requestor_user.email
                ]

                send_email_template(
                    'Remove User Request Approved',
                    'email/remove_allocation_user_request_approved.txt',
                    template_context,
                    EMAIL_SENDER,
                    email_receiver_list
                )

        messages.success(request, 'User {}\'s status has been APPROVED'.format(allocation_user.user.username))

        return HttpResponseRedirect(reverse('allocation-user-request-list'))


class AllocationUserDenyRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.change_allocationuserstatuschoice'):
            return True

        messages.error(self.request, 'You do not have access to deny allocation user requests.')

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        allocation_user_request = get_object_or_404(AllocationUserRequest, pk=pk)
        allocation_user = allocation_user_request.allocation_user

        current_status = allocation_user.status.name
        action = current_status.split(' ')[2]

        allocation_user_status_choice = AllocationUserStatusChoice.objects.get(
            name='Removed'
        )
        if action == 'Remove':
            allocation_user_status_choice = AllocationUserStatusChoice.objects.get(
                name='Active'
            )

        allocation_user_request_status_choice = AllocationUserRequestStatusChoice.objects.get(
            name='Denied'
        )

        allocation_user.status = allocation_user_status_choice
        allocation_user.save()

        allocation_user_request.status = allocation_user_request_status_choice
        allocation_user_request.save()

        if EMAIL_ENABLED:
            domain_url = get_domain_url(request)
            url = '{}{}'.format(domain_url, reverse(
                'allocation-detail', kwargs={'pk': allocation_user.allocation.pk})
            )
            template_context = {
                'user': allocation_user.user.username,
                'project': allocation_user.allocation.project.title,
                'allocation': allocation_user.allocation.get_parent_resource,
                'url': url,
            }

            if action == 'Add':
                email_receiver_list = [
                    allocation_user_request.requestor_user.email
                ]

                send_email_template(
                    'Add User Request Denied',
                    'email/add_allocation_user_request_denied.txt',
                    template_context,
                    EMAIL_SENDER,
                    email_receiver_list
                )
            else:
                email_receiver_list = [
                    allocation_user_request.requestor_user.email
                ]

                send_email_template(
                    'Remove User Request Denied',
                    'email/remove_allocation_user_request_denied.txt',
                    template_context,
                    EMAIL_SENDER,
                    email_receiver_list
                )

        messages.success(request, 'User {}\'s status has been DENIED'.format(allocation_user.user.username))

        return HttpResponseRedirect(reverse('allocation-user-request-list'))


class AllocationUserRequestInfoView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_user_request_info.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.change_allocationuserstatuschoice'):
            return True

        messages.error(self.request, 'You do not have access to view allocation user request info.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        context['request_info'] = get_object_or_404(AllocationUserRequest, pk=pk)

        return context


class AllocationChangeDetailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    formset_class = AllocationAttributeUpdateForm
    template_name = 'allocation/allocation_change_detail.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_view_all_allocations'):
            return True

        allocation_change_obj = get_object_or_404(
            AllocationChangeRequest, pk=self.kwargs.get('pk'))

        if allocation_change_obj.allocation.project.pi == self.request.user:
            return True

        if allocation_change_obj.allocation.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        user_can_access_project = allocation_change_obj.allocation.project.projectuser_set.filter(
            user=self.request.user, status__name__in=['Active', 'New', ]).exists()

        user_can_access_allocation = allocation_change_obj.allocation.allocationuser_set.filter(
            user=self.request.user, status__name__in=['Active', ]).exists()

        if user_can_access_project and user_can_access_allocation:
            return True

        return False

    def get_allocation_attributes_to_change(self, allocation_change_obj):
        attributes_to_change = allocation_change_obj.allocationattributechangerequest_set.all()

        attributes_to_change = [

            {'change_pk': attribute_change.pk,
             'attribute_pk': attribute_change.allocation_attribute.pk,
             'name': attribute_change.allocation_attribute.allocation_attribute_type.name,
             'value': attribute_change.allocation_attribute.value,
             'new_value': attribute_change.new_value,
             }

            for attribute_change in attributes_to_change
        ]

        return attributes_to_change

    def get_context_data(self, **kwargs):
        context = {}

        allocation_change_obj = get_object_or_404(
            AllocationChangeRequest, pk=self.kwargs.get('pk'))

        allocation_attributes_to_change = self.get_allocation_attributes_to_change(
            allocation_change_obj)

        if allocation_attributes_to_change:
            formset = formset_factory(self.formset_class, max_num=len(
                allocation_attributes_to_change))
            formset = formset(
                initial=allocation_attributes_to_change, prefix='attributeform')
            context['formset'] = formset

        context['allocation_change'] = allocation_change_obj
        context['attribute_changes'] = allocation_attributes_to_change

        return context

    def get(self, request, *args, **kwargs):

        allocation_change_obj = get_object_or_404(
            AllocationChangeRequest, pk=self.kwargs.get('pk'))

        allocation_change_form = AllocationChangeForm(
            initial={'justification': allocation_change_obj.justification,
                     'end_date_extension': allocation_change_obj.end_date_extension})
        allocation_change_form.fields['justification'].disabled = True
        if allocation_change_obj.status.name != 'Pending':
            allocation_change_form.fields['end_date_extension'].disabled = True
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            allocation_change_form.fields['end_date_extension'].disabled = True

        note_form = AllocationChangeNoteForm(
            initial={'notes': allocation_change_obj.notes})

        context = self.get_context_data()

        context['allocation_change_form'] = allocation_change_form
        context['note_form'] = note_form
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        if not self.request.user.is_superuser:
            messages.error(
                request, 'You do not have permission to update an allocation change request')
            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

        allocation_change_obj = get_object_or_404(
            AllocationChangeRequest, pk=pk)
        allocation_change_form = AllocationChangeForm(request.POST,
            initial={'justification': allocation_change_obj.justification,
                     'end_date_extension': allocation_change_obj.end_date_extension})
        allocation_change_form.fields['justification'].required = False

        allocation_attributes_to_change = self.get_allocation_attributes_to_change(
            allocation_change_obj)

        if allocation_attributes_to_change:
            formset = formset_factory(self.formset_class, max_num=len(
                allocation_attributes_to_change))
            formset = formset(
                request.POST, initial=allocation_attributes_to_change, prefix='attributeform')

        note_form = AllocationChangeNoteForm(
            request.POST, initial={'notes': allocation_change_obj.notes})

        if note_form.is_valid():
            notes = note_form.cleaned_data.get('notes')

            if request.POST.get('choice') == 'approve':
                if allocation_attributes_to_change:
                    if allocation_change_form.is_valid() and formset.is_valid():
                        allocation_change_obj.notes = notes

                        allocation_change_status_active_obj = AllocationChangeStatusChoice.objects.get(
                            name='Approved')

                        allocation_change_obj.status = allocation_change_status_active_obj

                        form_data = allocation_change_form.cleaned_data

                        if form_data.get('end_date_extension') != allocation_change_obj.end_date_extension:
                            allocation_change_obj.end_date_extension = form_data.get('end_date_extension')

                        new_end_date = allocation_change_obj.allocation.end_date + relativedelta(
                            days=allocation_change_obj.end_date_extension)

                        allocation_change_obj.allocation.end_date = new_end_date
                        allocation_change_obj.allocation.save()

                        allocation_change_obj.save()

                        for entry in formset:
                            formset_data = entry.cleaned_data
                            new_value = formset_data.get('new_value')

                            attribute_change = AllocationAttributeChangeRequest.objects.get(pk=formset_data.get('change_pk'))

                            if new_value != attribute_change.new_value:
                                attribute_change.new_value = new_value
                                attribute_change.save()

                        attribute_change_list = allocation_change_obj.allocationattributechangerequest_set.all()

                        for attribute_change in attribute_change_list:
                            attribute_change.allocation_attribute.value = attribute_change.new_value
                            attribute_change.allocation_attribute.save()

                        messages.success(request, 'Allocation change request to {} has been APPROVED for {} {} ({})'.format(
                            allocation_change_obj.allocation.get_parent_resource,
                            allocation_change_obj.allocation.project.pi.first_name,
                            allocation_change_obj.allocation.project.pi.last_name,
                            allocation_change_obj.allocation.project.pi.username)
                        )

                        allocation_change_approved.send(
                            sender=self.__class__,
                            allocation_pk=allocation_change_obj.allocation.pk,
                            allocation_change_pk=allocation_change_obj.pk,)

                        resource_name = allocation_change_obj.allocation.get_parent_resource
                        domain_url = get_domain_url(self.request)
                        allocation_url = '{}{}'.format(domain_url, reverse(
                            'allocation-detail', kwargs={'pk': allocation_change_obj.allocation.pk}))

                        if EMAIL_ENABLED:
                            template_context = {
                                'center_name': EMAIL_CENTER_NAME,
                                'resource': resource_name,
                                'allocation_url': allocation_url,
                                'signature': EMAIL_SIGNATURE,
                                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                            }

                            email_receiver_list = []
                            for allocation_user in allocation_change_obj.allocation.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                                if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                                    email_receiver_list.append(allocation_user.user.email)

                            send_email_template(
                                'Allocation Change Approved',
                                'email/allocation_change_approved.txt',
                                template_context,
                                EMAIL_SENDER,
                                email_receiver_list
                            )

                        return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))
                else:
                    if allocation_change_form.is_valid():
                        form_data = allocation_change_form.cleaned_data
                        selected_extension = form_data.get('end_date_extension')

                        if selected_extension != 0:
                            allocation_change_obj.notes = notes

                            allocation_change_status_active_obj = AllocationChangeStatusChoice.objects.get(
                                name='Approved')
                            allocation_change_obj.status = allocation_change_status_active_obj

                            if selected_extension != allocation_change_obj.end_date_extension:
                                allocation_change_obj.end_date_extension = selected_extension

                            new_end_date = allocation_change_obj.allocation.end_date + relativedelta(
                                days=allocation_change_obj.end_date_extension)
                            allocation_change_obj.allocation.end_date = new_end_date

                            allocation_change_obj.allocation.save()
                            allocation_change_obj.save()

                            messages.success(request, 'Allocation change request to {} has been APPROVED for {} {} ({})'.format(
                                allocation_change_obj.allocation.get_parent_resource,
                                allocation_change_obj.allocation.project.pi.first_name,
                                allocation_change_obj.allocation.project.pi.last_name,
                                allocation_change_obj.allocation.project.pi.username)
                            )

                            allocation_change_approved.send(
                                sender=self.__class__,
                                allocation_pk=allocation_change_obj.allocation.pk,
                                allocation_change_pk=allocation_change_obj.pk,)

                            resource_name = allocation_change_obj.allocation.get_parent_resource
                            domain_url = get_domain_url(self.request)
                            allocation_url = '{}{}'.format(domain_url, reverse(
                                'allocation-detail', kwargs={'pk': allocation_change_obj.allocation.pk}))

                            if EMAIL_ENABLED:
                                template_context = {
                                    'center_name': EMAIL_CENTER_NAME,
                                    'resource': resource_name,
                                    'allocation_url': allocation_url,
                                    'signature': EMAIL_SIGNATURE,
                                    'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                                }

                                email_receiver_list = []
                                for allocation_user in allocation_change_obj.allocation.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                                    if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                                        email_receiver_list.append(allocation_user.user.email)

                                send_email_template(
                                    'Allocation Change Approved',
                                    'email/allocation_change_approved.txt',
                                    template_context,
                                    EMAIL_SENDER,
                                    email_receiver_list
                                )

                            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

                        else:
                            messages.error(request, 'You must make a change to the allocation.')
                            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

                    else:
                        for error in allocation_change_form.errors:
                            messages.error(request, error)
                        return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

            if request.POST.get('choice') == 'deny':
                allocation_change_obj.notes = notes

                allocation_change_status_denied_obj = AllocationChangeStatusChoice.objects.get(
                    name='Denied')

                allocation_change_obj.status = allocation_change_status_denied_obj
                allocation_change_obj.save()

                messages.success(request, 'Allocation change request to {} has been DENIED for {} {} ({})'.format(
                    allocation_change_obj.allocation.resources.first(),
                    allocation_change_obj.allocation.project.pi.first_name,
                    allocation_change_obj.allocation.project.pi.last_name,
                    allocation_change_obj.allocation.project.pi.username)
                )

                resource_name = allocation_change_obj.allocation.get_parent_resource
                domain_url = get_domain_url(self.request)
                allocation_url = '{}{}'.format(domain_url, reverse(
                    'allocation-detail', kwargs={'pk': allocation_change_obj.allocation.pk}))

                if EMAIL_ENABLED:
                    template_context = {
                        'center_name': EMAIL_CENTER_NAME,
                        'resource': resource_name,
                        'allocation_url': allocation_url,
                        'signature': EMAIL_SIGNATURE,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                    }

                    email_receiver_list = []
                    for allocation_user in allocation_change_obj.allocation.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                        allocation_remove_user.send(
                                    sender=self.__class__, allocation_user_pk=allocation_user.pk)
                        if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                            email_receiver_list.append(allocation_user.user.email)

                    send_email_template(
                        'Allocation Change Denied',
                        'email/allocation_change_denied.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                    )
                return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

            if request.POST.get('choice') == 'update':
                if allocation_change_obj.status.name != 'Pending':
                    allocation_change_obj.notes = notes
                    allocation_change_obj.save()

                    messages.success(
                        request, 'Allocation change request updated!')
                    return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))
                else:
                    if allocation_attributes_to_change:
                        if allocation_change_form.is_valid() and formset.is_valid():
                            allocation_change_obj.notes = notes

                            form_data = allocation_change_form.cleaned_data

                            if form_data.get('end_date_extension') != allocation_change_obj.end_date_extension:
                                allocation_change_obj.end_date_extension = form_data.get('end_date_extension')

                            for entry in formset:
                                formset_data = entry.cleaned_data
                                new_value = formset_data.get('new_value')

                                attribute_change = AllocationAttributeChangeRequest.objects.get(pk=formset_data.get('change_pk'))

                                if new_value != attribute_change.new_value:
                                    attribute_change.new_value = new_value
                                    attribute_change.save()

                            allocation_change_obj.save()

                            messages.success(
                                request, 'Allocation change request updated!')
                            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))
                        else:
                            attribute_errors = ""
                            for error in allocation_change_form.errors:
                                messages.error(request, error)
                            for error in formset.errors:
                                if error: attribute_errors += error.get('__all__')
                            messages.error(request, attribute_errors)
                            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))
                    else:
                        if allocation_change_form.is_valid():
                            form_data = allocation_change_form.cleaned_data
                            selected_extension = form_data.get('end_date_extension')

                            if selected_extension != 0:
                                allocation_change_obj.notes = notes

                                if selected_extension != allocation_change_obj.end_date_extension:
                                    allocation_change_obj.end_date_extension = selected_extension

                                allocation_change_obj.save()

                                messages.success(
                                    request, 'Allocation change request updated!')

                                return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

                            else:
                                messages.error(request, 'You must make a change to the allocation.')
                                return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))
                        else:
                            for error in allocation_change_form.errors:
                                messages.error(request, error)
                            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

        else:
            allocation_change_form = AllocationChangeForm(
                initial={'justification': allocation_change_obj.justification})
            allocation_change_form.fields['justification'].disabled = True

            context = self.get_context_data()

            context['note_form'] = note_form
            context['allocation_change_form'] = allocation_change_form
            return render(request, self.template_name, context)


class AllocationChangeListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_change_list.html'
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_allocation_requests'):
            return True

        messages.error(
            self.request, 'You do not have permission to review allocation requests.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_change_list = AllocationChangeRequest.objects.filter(
            status__name__in=['Pending', ],
            allocation__resources__review_groups__in=list(self.request.user.groups.all())
        )
        context['allocation_change_list'] = allocation_change_list
        context['PROJECT_ENABLE_PROJECT_REVIEW'] = PROJECT_ENABLE_PROJECT_REVIEW
        return context


class AllocationChangeView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    formset_class = AllocationAttributeChangeForm
    template_name = 'allocation/allocation_change.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.project.pi == self.request.user:
            return True

        if allocation_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(
            self.request, 'You do not have permission to request changes to this allocation.')

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.project.needs_review:
            messages.error(
                request, 'You cannot request a change to this allocation because you have to review your project first.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.project.status.name in ['Denied', 'Expired', ]:
            messages.error(
                request, 'You cannot request a change to an allocation in a project with status "{}".'.format(allocation_obj.project.status.name))
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.is_locked:
            messages.error(
                request, 'You cannot request a change to a locked allocation.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.status.name not in ['Active', 'Renewal Requested', 'Payment Pending', 'Payment Requested', 'Paid']:
            messages.error(request, 'You cannot request a change to an allocation with status "{}".'.format(
                allocation_obj.status.name))
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_allocation_attributes_to_change(self, allocation_obj):
        attributes_to_change = allocation_obj.allocationattribute_set.filter(
            allocation_attribute_type__is_changeable=True)

        attributes_to_change = [

            {'pk': attribute.pk,
             'name': attribute.allocation_attribute_type.name,
             'value': attribute.value,
             }

            for attribute in attributes_to_change
        ]

        return attributes_to_change

    def get(self, request, *args, **kwargs):
        context = {}

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        form = AllocationChangeForm(**self.get_form_kwargs())
        context['form'] = form

        allocation_attributes_to_change = self.get_allocation_attributes_to_change(allocation_obj)

        if allocation_attributes_to_change:
            formset = formset_factory(self.formset_class, max_num=len(
                allocation_attributes_to_change))
            formset = formset(
                initial=allocation_attributes_to_change, prefix='attributeform')
            context['formset'] = formset
        context['allocation'] = allocation_obj
        context['attributes'] = allocation_attributes_to_change
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        change_requested = False
        attribute_changes_to_make = set({})

        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        form = AllocationChangeForm(**self.get_form_kwargs())

        allocation_attributes_to_change = self.get_allocation_attributes_to_change(
            allocation_obj)

        if allocation_attributes_to_change:
            formset = formset_factory(self.formset_class, max_num=len(
                allocation_attributes_to_change))
            formset = formset(
                request.POST, initial=allocation_attributes_to_change, prefix='attributeform')

            if form.is_valid() and formset.is_valid():
                form_data = form.cleaned_data

                if form_data.get('end_date_extension') != 0: change_requested = True

                for entry in formset:
                    formset_data = entry.cleaned_data

                    new_value = formset_data.get('new_value')

                    if new_value != "":
                        change_requested = True

                        allocation_attribute = AllocationAttribute.objects.get(pk=formset_data.get('pk'))
                        attribute_changes_to_make.add((allocation_attribute, new_value))

                if change_requested == True:

                    end_date_extension = form_data.get('end_date_extension')
                    justification = form_data.get('justification')

                    change_request_status_obj = AllocationChangeStatusChoice.objects.get(
                        name='Pending')

                    allocation_change_request_obj = AllocationChangeRequest.objects.create(
                        allocation=allocation_obj,
                        end_date_extension=end_date_extension,
                        justification=justification,
                        status=change_request_status_obj
                        )

                    for attribute in attribute_changes_to_make:
                        attribute_change_request_obj = AllocationAttributeChangeRequest.objects.create(
                            allocation_change_request=allocation_change_request_obj,
                            allocation_attribute=attribute[0],
                            new_value=attribute[1]
                            )
                    messages.success(
                        request, 'Allocation change request successfully submitted.')

                    pi_name = '{} {} ({})'.format(allocation_obj.project.pi.first_name,
                                                allocation_obj.project.pi.last_name, allocation_obj.project.pi.username)
                    resource_name = allocation_obj.get_parent_resource
                    domain_url = get_domain_url(self.request)
                    url = '{}{}'.format(domain_url, reverse('allocation-change-list'))

                    if EMAIL_ENABLED:
                        template_context = {
                            'pi': pi_name,
                            'resource': resource_name,
                            'url': url
                        }

                        email_recipient = get_email_recipient_from_groups(
                            allocation_obj.get_parent_resource.review_groups.all()
                        )

                        send_email_template(
                            'New Allocation Change Request: {} - {}'.format(
                                pi_name, resource_name),
                            'email/new_allocation_change_request.txt',
                            template_context,
                            EMAIL_SENDER,
                            [email_recipient, ]
                        )

                    return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

                else:
                    messages.error(request, 'You must request a change.')
                    return HttpResponseRedirect(reverse('allocation-change', kwargs={'pk': pk}))

            else:
                attribute_errors = ""
                for error in form.errors:
                    messages.error(request, error)
                for error in formset.errors:
                    if error: attribute_errors += error.get('__all__')
                messages.error(request, attribute_errors)
                return HttpResponseRedirect(reverse('allocation-change', kwargs={'pk': pk}))
        else:
            if form.is_valid():
                form_data = form.cleaned_data

                if form_data.get('end_date_extension') != 0:

                    end_date_extension = form_data.get('end_date_extension')
                    justification = form_data.get('justification')

                    change_request_status_obj = AllocationChangeStatusChoice.objects.get(
                        name='Pending')

                    allocation_change_request_obj = AllocationChangeRequest.objects.create(
                        allocation=allocation_obj,
                        end_date_extension=end_date_extension,
                        justification=justification,
                        status=change_request_status_obj
                        )
                    messages.success(
                        request, 'Allocation change request successfully submitted.')

                pi_name = '{} {} ({})'.format(allocation_obj.project.pi.first_name,
                                            allocation_obj.project.pi.last_name, allocation_obj.project.pi.username)
                resource_name = allocation_obj.get_parent_resource
                domain_url = get_domain_url(self.request)
                url = '{}{}'.format(domain_url, reverse('allocation-change-list'))

                if EMAIL_ENABLED:
                    template_context = {
                        'pi': pi_name,
                        'resource': resource_name,
                        'url': url
                    }

                    email_recipient = get_email_recipient_from_groups(
                        allocation_obj.get_parent_resource.review_groups.all()
                    )

                    send_email_template(
                        'New Allocation Change Request: {} - {}'.format(
                            pi_name, resource_name),
                        'email/new_allocation_change_request.txt',
                        template_context,
                        EMAIL_SENDER,
                        [email_recipient, ]
                    )

                    return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

                else:
                    messages.error(request, 'You must request a change.')
                    return HttpResponseRedirect(reverse('allocation-change', kwargs={'pk': pk}))

            else:
                for error in form.errors:
                    messages.error(request, error)
                return HttpResponseRedirect(reverse('allocation-change', kwargs={'pk': pk}))


class AllocationChangeActivateView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_allocation_requests'):
            return True

        messages.error(
            self.request, 'You do not have permission to approve an allocation change.')

    def get(self, request, pk):
        allocation_change_obj = get_object_or_404(AllocationChangeRequest, pk=pk)

        allocation_change_status_active_obj = AllocationChangeStatusChoice.objects.get(
            name='Approved')

        allocation_change_obj.status = allocation_change_status_active_obj

        if allocation_change_obj.end_date_extension != 0:
            new_end_date = allocation_change_obj.allocation.end_date + relativedelta(
                days=allocation_change_obj.end_date_extension)

            allocation_change_obj.allocation.end_date = new_end_date

        allocation_change_obj.allocation.save()
        allocation_change_obj.save()

        attribute_change_list = allocation_change_obj.allocationattributechangerequest_set.all()

        for attribute_change in attribute_change_list:
            attribute_change.allocation_attribute.value = attribute_change.new_value
            attribute_change.allocation_attribute.save()

        messages.success(request, 'Allocation change request to {} has been APPROVED for {} {} ({})'.format(
            allocation_change_obj.allocation.get_parent_resource,
            allocation_change_obj.allocation.project.pi.first_name,
            allocation_change_obj.allocation.project.pi.last_name,
            allocation_change_obj.allocation.project.pi.username)
        )

        allocation_change_approved.send(
            sender=self.__class__,
            allocation_pk=allocation_change_obj.allocation.pk,
            allocation_change_pk=allocation_change_obj.pk,)

        resource_name = allocation_change_obj.allocation.get_parent_resource
        domain_url = get_domain_url(self.request)
        allocation_url = '{}{}'.format(domain_url, reverse(
            'allocation-detail', kwargs={'pk': allocation_change_obj.allocation.pk}))

        if EMAIL_ENABLED:
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'allocation_url': allocation_url,
                'signature': EMAIL_SIGNATURE,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
            }

            email_receiver_list = []

            for allocation_user in allocation_change_obj.allocation.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                    email_receiver_list.append(allocation_user.user.email)

            send_email_template(
                'Allocation Change Approved',
                'email/allocation_change_approved.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )

        return HttpResponseRedirect(reverse('allocation-change-list'))


class AllocationChangeDenyView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_allocation_requests'):
            return True

        messages.error(
            self.request, 'You do not have permission to deny an allocation change.')

    def get(self, request, pk):
        allocation_change_obj = get_object_or_404(AllocationChangeRequest, pk=pk)

        allocation_change_status_denied_obj = AllocationChangeStatusChoice.objects.get(
            name='Denied')

        allocation_change_obj.status = allocation_change_status_denied_obj
        allocation_change_obj.save()

        messages.success(request, 'Allocation change request to {} has been DENIED for {} {} ({})'.format(
            allocation_change_obj.allocation.resources.first(),
            allocation_change_obj.allocation.project.pi.first_name,
            allocation_change_obj.allocation.project.pi.last_name,
            allocation_change_obj.allocation.project.pi.username)
        )

        resource_name = allocation_change_obj.allocation.get_parent_resource
        domain_url = get_domain_url(self.request)
        allocation_url = '{}{}'.format(domain_url, reverse(
            'allocation-detail', kwargs={'pk': allocation_change_obj.allocation.pk}))

        if EMAIL_ENABLED:
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'allocation_url': allocation_url,
                'signature': EMAIL_SIGNATURE,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
            }

            email_receiver_list = []
            for allocation_user in allocation_change_obj.allocation.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                allocation_remove_user.send(
                            sender=self.__class__, allocation_user_pk=allocation_user.pk)
                if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                    email_receiver_list.append(allocation_user.user.email)

            send_email_template(
                'Allocation Change Denied',
                'email/allocation_change_denied.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )
        return HttpResponseRedirect(reverse('allocation-change-list'))


class AllocationChangeDeleteAttributeView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_allocation_requests'):
            return True

        messages.error(
            self.request, 'You do not have permission to update an allocation change request.')

    def get(self, request, pk):
        allocation_attribute_change_obj = get_object_or_404(AllocationAttributeChangeRequest, pk=pk)
        allocation_change_pk = allocation_attribute_change_obj.allocation_change_request.pk

        allocation_attribute_change_obj.delete()

        messages.success(
            request, 'Allocation attribute change request successfully deleted.')
        return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': allocation_change_pk}))
