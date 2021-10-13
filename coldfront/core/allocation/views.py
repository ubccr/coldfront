import datetime
import logging
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
from django.http.response import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html, mark_safe
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.utils.module_loading import import_string

from coldfront.core.allocation.forms import (AllocationAccountForm,
                                             AllocationAddUserForm,
                                             AllocationAttributeDeleteForm,
                                             AllocationForm,
                                             AllocationInvoiceNoteDeleteForm,
                                             AllocationInvoiceUpdateForm,
                                             AllocationRemoveUserForm,
                                             AllocationReviewUserForm,
                                             AllocationSearchForm,
                                             AllocationUpdateForm)
from coldfront.core.allocation.models import (Allocation, AllocationAccount,
                                              AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserNote,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import (allocation_activate_user,
                                               allocation_remove_user)
from coldfront.core.allocation.utils import (compute_prorated_amount,
                                             generate_guauge_data_from_usage,
                                             get_user_resources)
from coldfront.core.utils.common import Echo
from coldfront.core.project.models import (Project, ProjectUser,
                                           ProjectUserStatusChoice)
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email_template

ALLOCATION_ENABLE_ALLOCATION_RENEWAL = import_from_settings(
    'ALLOCATION_ENABLE_ALLOCATION_RENEWAL', True)
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = import_from_settings(
    'ALLOCATION_DEFAULT_ALLOCATION_LENGTH', 365)

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
            user=self.request.user, status__name__in=['Active', ]).exists()

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

        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True
        elif allocation_obj.project.projectuser_set.filter(user=self.request.user).exists():
            project_user = allocation_obj.project.projectuser_set.get(
                user=self.request.user)
            if project_user.role.name == 'Manager':
                context['is_allowed_to_update_project'] = True
            else:
                context['is_allowed_to_update_project'] = False
        else:
            context['is_allowed_to_update_project'] = False

        context['guage_data'] = guage_data
        context['attributes_with_usage'] = attributes_with_usage
        context['attributes'] = attributes

        # Can the user update the project?
        if self.request.user.is_superuser:
            context['is_allowed_to_update_project'] = True
        elif allocation_obj.project.projectuser_set.filter(user=self.request.user).exists():
            project_user = allocation_obj.project.projectuser_set.get(
                user=self.request.user)
            if project_user.role.name == 'Manager':
                context['is_allowed_to_update_project'] = True
            else:
                context['is_allowed_to_update_project'] = False
        else:
            context['is_allowed_to_update_project'] = False
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
            'description': allocation_obj.description
        }

        form = AllocationUpdateForm(initial=initial_data)

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
            'description': allocation_obj.description
        }
        form = AllocationUpdateForm(request.POST, initial=initial_data)

        if form.is_valid():
            form_data = form.cleaned_data
            end_date = form_data.get('end_date')
            start_date = form_data.get('start_date')
            description = form_data.get('description')

            allocation_obj.description = description
            allocation_obj.save()

            if not start_date:
                start_date = datetime.datetime.now()
            if not end_date:
                end_date = datetime.datetime.now(
                ) + relativedelta(days=ALLOCATION_DEFAULT_ALLOCATION_LENGTH)

            if allocation_obj.use_indefinitely:
                end_date = None

            allocation_obj.end_date = end_date

            old_status = allocation_obj.status.name
            new_status = form_data.get('status').name

            allocation_obj.status = form_data.get('status')
            allocation_obj.save()

            if EMAIL_ENABLED:
                resource_name = allocation_obj.get_parent_resource
                domain_url = get_domain_url(self.request)
                allocation_url = '{}{}'.format(domain_url, reverse(
                    'allocation-detail', kwargs={'pk': allocation_obj.pk}))

            if old_status != 'Active' and new_status == 'Active':
                allocation_obj.start_date = start_date
                allocation_obj.save()
                if EMAIL_ENABLED:
                    template_context = {
                        'center_name': EMAIL_CENTER_NAME,
                        'resource': resource_name,
                        'allocation_url': allocation_url,
                        'signature': EMAIL_SIGNATURE,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                    }

                    email_receiver_list = []

                    for allocation_user in allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                        allocation_activate_user.send(
                            sender=self.__class__, allocation_user_pk=allocation_user.pk)
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
                allocation_obj.start_date = None
                allocation_obj.end_date = None
                allocation_obj.save()
                if EMAIL_ENABLED:
                    template_context = {
                        'center_name': EMAIL_CENTER_NAME,
                        'resource': resource_name,
                        'allocation_url': allocation_url,
                        'signature': EMAIL_SIGNATURE,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
                    }
                    email_receiver_list = []
                    for allocation_user in allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                        allocation_remove_user.send(
                            sender=self.__class__, allocation_user_pk=allocation_user.pk)
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

            if start_date and allocation_obj.start_date != start_date:
                allocation_obj.start_date = start_date
                allocation_obj.save()

            if end_date and allocation_obj.end_date != end_date:
                allocation_obj.end_date = end_date
                allocation_obj.save()

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
                    Q(project__status__name='Active') &
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

        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot request a new allocation to an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        context['project'] = project_obj

        user_resources = get_user_resources(self.request.user)
        resources_form_default_quantities = {}
        resources_form_label_texts = {}
        resources_form_storage_space = {}
        resources_form_storage_space_label = {}
        resources_form_storage_space_with_unit = {}
        resources_form_storage_space_with_unit_label = {}
        resources_form_leverage_multiple_gpus = {}
        resources_form_leverage_multiple_gpus_label = {}
        resources_form_dl_workflow = {}
        resources_form_dl_workflow_label = {}
        resources_form_applications_list = {}
        resources_form_applications_list_label = {}
        resources_form_training_or_inference = {}
        resources_form_training_or_inference_label = {}
        resources_form_for_coursework = {}
        resources_form_for_coursework_label = {}
        resources_form_system = {}
        resources_form_system_label = {}
        resources_form_start_date = {}
        resources_form_start_date_label = {}
        resources_form_end_date = {}
        resources_form_end_date_label = {}
        resources_form_phi_association = {}
        resources_form_phi_association_label = {}
        resources_form_access_level = {}
        resources_form_access_level_label = {}
        resources_form_confirm_understanding = {}
        resources_form_confirm_understanding_label = {}
        resources_form_primary_contact = {}
        resources_form_primary_contact_label = {}
        resources_form_secondary_contact = {}
        resources_form_secondary_contact_label = {}
        resources_form_department_full_name = {}
        resources_form_department_full_name_label = {}
        resources_form_department_short_name = {}
        resources_form_department_short_name_label = {}
        resources_form_fiscal_officer = {}
        resources_form_fiscal_officer_label = {}
        resources_form_account_number = {}
        resources_form_account_number_label = {}
        resources_form_sub_account_number = {}
        resources_form_sub_account_number_label = {}
        resources_form_it_pros = {}
        resources_form_it_pros_label = {}
        resources_form_devices_ip_addresses = {}
        resources_form_devices_ip_addresses_label = {}
        resources_form_data_management_plan = {}
        resources_form_data_management_plan_label = {}
        resources_form_project_directory_name = {}
        resources_form_project_directory_name_label = {}
        resources_form_cost = {}
        resources_form_cost_label = {}
        resources_form_prorated_cost = {}
        resources_form_prorated_cost_label = {}
        resources_form_first_name = {}
        resources_form_first_name_label = {}
        resources_form_last_name = {}
        resources_form_last_name_label = {}
        resources_form_campus_affiliation = {}
        resources_form_campus_affiliation_label = {}
        resources_form_email = {}
        resources_form_email_label = {}
        resources_form_url = {}
        resources_form_url_label = {}
        resources_form_faculty_email = {}
        resources_form_faculty_email_label = {}
        resources_form_store_ephi = {}
        resources_form_store_ephi_label = {}
        resources_with_eula = {}

        for resource in user_resources:
            if resource.resourceattribute_set.filter(resource_attribute_type__name='quantity_default_value').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='quantity_default_value').value
                if value == "":
                    resources_form_default_quantities[resource.id] = 0
                else:
                    resources_form_default_quantities[resource.id] = int(value)
            if resource.resourceattribute_set.filter(resource_attribute_type__name='quantity_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='quantity_label').value
                resources_form_label_texts[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='storage_space').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='storage_space').value
                if value == '':
                    resources_form_storage_space[resource.id] = 0
                else:
                    resources_form_storage_space[resource.id] = int(value)
            if resource.resourceattribute_set.filter(resource_attribute_type__name='storage_space_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='storage_space_label').value
                resources_form_storage_space_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='storage_space_with_unit').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='storage_space_with_unit').value
                if value == '':
                    resources_form_storage_space_with_unit[resource.id] = 0
                else:
                    resources_form_storage_space_with_unit[resource.id] = int(value)
            if resource.resourceattribute_set.filter(resource_attribute_type__name='storage_space_with_unit_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='storage_space_with_unit_label').value
                resources_form_storage_space_with_unit_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='leverage_multiple_gpus').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='leverage_multiple_gpus').value
                resources_form_leverage_multiple_gpus[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='leverage_multiple_gpus_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='leverage_multiple_gpus_label').value
                resources_form_leverage_multiple_gpus_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='applications_list').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='applications_list').value
                resources_form_applications_list[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='applications_list_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='applications_list_label').value
                resources_form_applications_list_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='dl_workflow').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='dl_workflow').value
                resources_form_dl_workflow[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='dl_workflow_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='dl_workflow_label').value
                resources_form_dl_workflow_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='training_or_inference').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='training_or_inference').value
                resources_form_training_or_inference[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='training_or_inference_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='training_or_inference_label').value
                resources_form_training_or_inference_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='for_coursework').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='for_coursework').value
                resources_form_for_coursework[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='for_coursework_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='for_coursework_label').value
                resources_form_for_coursework_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='system').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='system').value
                resources_form_system[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='system_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='system_label').value
                resources_form_system_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='start_date').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='start_date').value
                resources_form_start_date[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='start_date_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='start_date_label').value
                resources_form_start_date_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='end_date').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='end_date').value
                resources_form_end_date[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='end_date_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='end_date_label').value
                resources_form_end_date_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='phi_association').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='phi_association').value
                resources_form_phi_association[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='phi_association_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='phi_association_label').value
                resources_form_phi_association_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='access_level').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='access_level').value
                resources_form_access_level[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='access_level_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='access_level_label').value
                resources_form_access_level_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='confirm_understanding').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='confirm_understanding').value
                resources_form_confirm_understanding[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='confirm_understanding_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='confirm_understanding_label').value
                resources_form_confirm_understanding_label[resource.id] = mark_safe(
                    '{}'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='primary_contact').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='primary_contact').value
                resources_form_primary_contact[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='primary_contact_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='primary_contact_label').value
                resources_form_primary_contact_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='secondary_contact').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='secondary_contact').value
                resources_form_secondary_contact[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='secondary_contact_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='secondary_contact_label').value
                resources_form_secondary_contact_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='department_full_name').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='department_full_name').value
                resources_form_department_full_name[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='department_full_name_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='department_full_name_label').value
                resources_form_department_full_name_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='department_short_name').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='department_short_name').value
                resources_form_department_short_name[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='department_short_name_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='department_short_name_label').value
                resources_form_department_short_name_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='fiscal_officer').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='fiscal_officer').value
                resources_form_fiscal_officer[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='fiscal_officer_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='fiscal_officer_label').value
                resources_form_fiscal_officer_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='account_number').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='account_number').value
                resources_form_account_number[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='account_number_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='account_number_label').value
                resources_form_account_number_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='sub_account_number').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='sub_account_number').value
                resources_form_sub_account_number[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='sub_account_number_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='sub_account_number_label').value
                resources_form_sub_account_number_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='it_pros').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='it_pros').value
                resources_form_it_pros[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='it_pros_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='it_pros_label').value
                resources_form_it_pros_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='devices_ip_addresses').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='devices_ip_addresses').value
                resources_form_devices_ip_addresses[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='devices_ip_addresses_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='devices_ip_addresses_label').value
                resources_form_devices_ip_addresses_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='data_management_plan').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='data_management_plan').value
                resources_form_data_management_plan[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='data_management_plan_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='data_management_plan_label').value
                resources_form_data_management_plan_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='project_directory_name').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='project_directory_name').value
                resources_form_project_directory_name[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='project_directory_name_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='project_directory_name_label').value
                resources_form_project_directory_name_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='first_name').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='first_name').value
                resources_form_first_name[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='first_name_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='first_name_label').value
                resources_form_first_name_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='last_name').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='last_name').value
                resources_form_last_name[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='last_name_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='last_name_label').value
                resources_form_last_name_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='campus_affiliation').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='campus_affiliation').value
                resources_form_campus_affiliation[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='campus_affiliation_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='campus_affiliation_label').value
                resources_form_campus_affiliation_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='email').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='email').value
                resources_form_email[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='email_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='email_label').value
                resources_form_email_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='url').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='url').value
                resources_form_url[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='url_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='url_label').value
                resources_form_url_label[resource.id] = mark_safe(
                    '<strong>{}</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='faculty_email').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='faculty_email').value
                resources_form_faculty_email[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='faculty_email_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='faculty_email_label').value
                resources_form_faculty_email_label[resource.id] = mark_safe(
                    '<strong>{}</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='store_ephi').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='store_ephi').value
                resources_form_store_ephi[resource.id] = value
            if resource.resourceattribute_set.filter(resource_attribute_type__name='store_ephi_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='store_ephi_label').value
                resources_form_store_ephi_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='cost').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='cost').value
                resources_form_cost[resource.id] = int(value)
            if resource.resourceattribute_set.filter(resource_attribute_type__name='cost_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='cost_label').value
                resources_form_cost_label[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))

            if resource.resourceattribute_set.filter(resource_attribute_type__name='prorated').exists():
                if resource.resourceattribute_set.get(resource_attribute_type__name='prorated'):
                    if resource.resourceattribute_set.filter(resource_attribute_type__name='prorated_cost_label').exists():
                        value = resource.resourceattribute_set.get(
                            resource_attribute_type__name='prorated_cost_label').value
                        resources_form_prorated_cost_label[resource.id] = mark_safe(
                            '<strong>{}*</strong>'.format(value))

                    if resource.resourceattribute_set.filter(resource_attribute_type__name='cost').exists():
                        resources_form_prorated_cost[resource.id] = compute_prorated_amount(
                            int(resource.resourceattribute_set.get(
                                resource_attribute_type__name='cost').value
                        ))
                    else:
                        resources_form_prorated_cost[resource.id] = 0

            if resource.resourceattribute_set.filter(resource_attribute_type__name='eula').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='eula').value
                resources_with_eula[resource.id] = value

        context['AllocationAccountForm'] = AllocationAccountForm()
        context['resources_form_default_quantities'] = resources_form_default_quantities
        context['resources_form_label_texts'] = resources_form_label_texts
        context['resources_form_storage_space'] = resources_form_storage_space
        context['resources_form_storage_space_label'] = resources_form_storage_space_label
        context['resources_form_storage_space_with_unit'] = resources_form_storage_space_with_unit
        context['resources_form_storage_space_with_unit_label'] = resources_form_storage_space_with_unit_label
        context['resources_form_leverage_multiple_gpus_label'] = resources_form_leverage_multiple_gpus_label
        context['resources_form_leverage_multiple_gpus'] = resources_form_leverage_multiple_gpus
        context['resources_form_dl_workflow_label'] = resources_form_dl_workflow_label
        context['resources_form_dl_workflow'] = resources_form_dl_workflow
        context['resources_form_applications_list_label'] = resources_form_applications_list_label
        context['resources_form_applications_list'] = resources_form_applications_list
        context['resources_form_training_or_inference_label'] = resources_form_training_or_inference_label
        context['resources_form_training_or_inference'] = resources_form_training_or_inference
        context['resources_form_for_coursework_label'] = resources_form_for_coursework_label
        context['resources_form_for_coursework'] = resources_form_for_coursework
        context['resources_form_system_label'] = resources_form_system_label
        context['resources_form_system'] = resources_form_system
        context['resources_form_start_date_label'] = resources_form_start_date_label
        context['resources_form_start_date'] = resources_form_start_date
        context['resources_form_end_date_label'] = resources_form_end_date_label
        context['resources_form_end_date'] = resources_form_end_date
        context['resources_form_phi_association_label'] = resources_form_phi_association_label
        context['resources_form_phi_association'] = resources_form_phi_association
        context['resources_form_access_level_label'] = resources_form_access_level_label
        context['resources_form_access_level'] = resources_form_access_level
        context['resources_form_confirm_understanding_label'] = resources_form_confirm_understanding_label
        context['resources_form_confirm_understanding'] = resources_form_confirm_understanding
        context['resources_form_primary_contact'] = resources_form_primary_contact
        context['resources_form_primary_contact_label'] = resources_form_primary_contact_label
        context['resources_form_secondary_contact'] = resources_form_secondary_contact
        context['resources_form_secondary_contact_label'] = resources_form_secondary_contact_label
        context['resources_form_department_full_name'] = resources_form_department_full_name
        context['resources_form_department_full_name_label'] = resources_form_department_full_name_label
        context['resources_form_department_short_name'] = resources_form_department_short_name
        context['resources_form_department_short_name_label'] = resources_form_department_short_name_label
        context['resources_form_fiscal_officer'] = resources_form_fiscal_officer
        context['resources_form_fiscal_officer_label'] = resources_form_fiscal_officer_label
        context['resources_form_account_number'] = resources_form_account_number
        context['resources_form_account_number_label'] = resources_form_account_number_label
        context['resources_form_sub_account_number'] = resources_form_sub_account_number
        context['resources_form_sub_account_number_label'] = resources_form_sub_account_number_label
        context['resources_form_it_pros'] = resources_form_it_pros
        context['resources_form_it_pros_label'] = resources_form_it_pros_label
        context['resources_form_devices_ip_addresses'] = resources_form_devices_ip_addresses
        context['resources_form_devices_ip_addresses_label'] = resources_form_devices_ip_addresses_label
        context['resources_form_data_management_plan'] = resources_form_data_management_plan
        context['resources_form_data_management_plan_label'] = resources_form_data_management_plan_label
        context['resources_form_project_directory_name'] = resources_form_project_directory_name
        context['resources_form_project_directory_name_label'] = resources_form_project_directory_name_label
        context['resources_form_cost'] = resources_form_cost
        context['resources_form_cost_label'] = resources_form_cost_label
        context['resources_form_prorated_cost'] = resources_form_prorated_cost
        context['resources_form_prorated_cost_label'] = resources_form_prorated_cost_label
        context['resources_form_first_name'] = resources_form_first_name
        context['resources_form_first_name_label'] = resources_form_first_name_label
        context['resources_form_last_name'] = resources_form_last_name
        context['resources_form_last_name_label'] = resources_form_last_name_label
        context['resources_form_campus_affiliation'] = resources_form_campus_affiliation
        context['resources_form_campus_affiliation_label'] = resources_form_campus_affiliation_label
        context['resources_form_email'] = resources_form_email
        context['resources_form_email_label'] = resources_form_email_label
        context['resources_form_url'] = resources_form_url
        context['resources_form_url_label'] = resources_form_url_label
        context['resources_form_faculty_email'] = resources_form_faculty_email
        context['resources_form_faculty_email_label'] = resources_form_faculty_email_label
        context['resources_form_store_ephi'] = resources_form_store_ephi
        context['resources_form_store_ephi_label'] = resources_form_store_ephi_label
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
        allocation_account = form_data.get('allocation_account', None)
        license_term = form_data.get('license_term', None)

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

        if resource_obj.name == 'RStudio Connect':
            end_date = self.calculate_end_date(6, 30, license_term)

        # A resource is selected that requires an account name selection but user has no account names
        if ALLOCATION_ACCOUNT_ENABLED and resource_obj.name in ALLOCATION_ACCOUNT_MAPPING and AllocationAttributeType.objects.filter(
                name=ALLOCATION_ACCOUNT_MAPPING[resource_obj.name]).exists() and not allocation_account:
            form.add_error(None, format_html(
                'You need to create an account name. Create it by clicking the link under the "Allocation account" field.'))
            return self.form_invalid(form)

        # Check if the required values exist based on what resource was selected.
        error = False
        if resource_obj.name == 'Priority Boost':
            use_indefinitely = is_grand_challenge
            if system == '' or (end_date is None and not is_grand_challenge):
                error = True
            elif is_grand_challenge and grand_challenge_program == '':
                error = True
            elif end_date is not None and end_date <= date.today():
                form.add_error(None, format_html(
                    'Please select a date later than today.'
                    )
                )
                return self.form_invalid(form)
        elif resource_obj.name == 'Carbonate DL':
            if leverage_multiple_gpus == '' or training_or_inference == '' or for_coursework == '':
                error = True
        elif resource_obj.name == 'Carbonate GPU':
            if leverage_multiple_gpus == '' or dl_workflow == '' or for_coursework == '':
                error = True
        elif resource_obj.name == 'Carbonate Precision Health Initiative (PHI) Nodes':
            if phi_association == '':
                error = True
        elif resource_obj.name == 'cBioPortal':
            if phi_association == '' or access_level == '' or confirm_understanding is False:
                error = True
        elif resource_obj.name == 'Geode-Projects':
            if (
                storage_space_with_unit is None
                or unit == ''
                or (not use_indefinitely and end_date is None)
                or start_date is None
                or primary_contact == ''
                or secondary_contact == ''
                or department_full_name == ''
                or department_short_name == ''
                or fiscal_officer == ''
                or account_number == ''
                or it_pros == ''
                or devices_ip_addresses == ''
                or data_management_plan == ''
            ):
                error = True
            elif (storage_space_with_unit <= 0 and unit == 'TB') or (storage_space_with_unit < 200 and unit == 'GB'):
                form.add_error(None, format_html(
                    'Please enter a storage amount greater than or equal to 200GB.'
                    )
                )
                return self.form_invalid(form)
            elif start_date <= date.today():
                form.add_error(None, format_html(
                    'Please select a start date later than today.'
                    )
                )
                return self.form_invalid(form)
            elif not use_indefinitely and end_date <= date.today():
                form.add_error(None, format_html(
                    'Please select an end date later than today.'
                    )
                )
                return self.form_invalid(form)
            elif not use_indefinitely and start_date >= end_date:
                form.add_error(None, format_html(
                    'Start date must be earlier than end date.'
                    )
                )
                return self.form_invalid(form)
            elif not len(account_number) == 9:
                form.add_error(None, format_html(
                    'Account number must have a format of 00-000-00.'
                    )
                )
                return self.form_invalid(form)
            elif not account_number[2] == '-' or not account_number[6] == '-':
                form.add_error(None, format_html(
                    'Account number must have a format of 00-000-00.'
                    )
                )
                return self.form_invalid(form)

            storage_space_with_unit = str(storage_space_with_unit) + unit
        elif resource_obj.name == 'RStudio Connect':
            if project_directory_name == '' or account_number == '' or not confirm_understanding:
                error = True
        elif resource_obj.name == 'Slate Project':
            if (
                first_name == '' or
                last_name == '' or
                campus_affiliation == '' or
                email == '' or
                project_directory_name == '' or
                start_date is None or
                store_ephi == ''
            ):
                error = True
            elif storage_space <= 0:
                form.add_error(None, format_html(
                    'Storage space must be greater than 0.'
                    )
                )
                return self.form_invalid(form)
            elif storage_space > 15 and account_number == '':
                error = True

        if error:
            form.add_error(None, format_html(
                'Please fill out all the required fields.'
                )
            )
            return self.form_invalid(form)

        usernames = form_data.get('users')
        usernames.append(project_obj.pi.username)
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
        if project_obj.pi not in users:
            users.append(project_obj.pi)

        denied_users = []
        resource_name = ''
        resource = resource_obj.get_attribute('check_user_account')
        for user in users:
            username = user.username
            if resource_obj.name == 'Priority Boost':
                if not resource_obj.check_user_account_exists(username, system):
                    denied_users.append(username)
                    resource_name = system
            else:
                if resource is not None:
                    if not resource_obj.check_user_account_exists(username, resource):
                        denied_users.append(username)
                        resource_name = resource

        if denied_users:
            form.add_error(None, format_html(
                'The following users do not have an account on {}: {}. They will need to create an account <a href="https://access.iu.edu/Accounts/Create">here</a>.'.format(resource_name, ', '.join(denied_users))
            ))
            return self.form_invalid(form)

        denied_users = []
        if resource_obj.name == "Geode-Projects":
            ldap_search = import_string('coldfront.plugins.ldap_user_search.utils.LDAPSearch')
            search_class_obj = ldap_search()
            for username in [primary_contact, secondary_contact, fiscal_officer] + it_pros.split(','):
                attributes = search_class_obj.search_a_user(username, ['memberOf'])
                if attributes['memberOf'] is None:
                    denied_users.append(username)

        if denied_users:
            form.add_error(None, format_html(
                'The following usernames are not valid: {}'.format(', '.join(denied_users))
            ))
            return self.form_invalid(form)

        if INVOICE_ENABLED and resource_obj.requires_payment:
            allocation_status_obj = AllocationStatusChoice.objects.get(
                name=INVOICE_DEFAULT_STATUS)
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
            status=allocation_status_obj
        )
        allocation_obj.resources.add(resource_obj)

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

        allocation_user_active_status = AllocationUserStatusChoice.objects.get(
            name='Active')
        for user in users:
            allocation_user_obj = AllocationUser.objects.create(
                allocation=allocation_obj,
                user=user,
                status=allocation_user_active_status)

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

            send_email_template(
                'New allocation request: {} - {}'.format(
                    pi_name, resource_name),
                'email/new_allocation_request.txt',
                template_context,
                EMAIL_SENDER,
                [EMAIL_TICKET_SYSTEM_ADDRESS, ]
            )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('project_pk')})


class AllocationAddUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_add_users.html'

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
            self.request, 'You do not have permission to add users to the allocation.')

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.is_locked and not self.request.user.is_superuser:
            messages.error(
                request, 'You cannot modify this allocation because it is locked! Contact support for details.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.status.name not in ['Active', 'New', 'Renewal Requested', 'Payment Pending', 'Payment Requested', 'Paid']:
            messages.error(request, 'You cannot add users to a allocation with status {}.'.format(
                allocation_obj.status.name))
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
        else:
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
                        allocation_user_obj.status = allocation_user_active_status_choice
                        allocation_user_obj.save()
                    else:
                        allocation_user_obj = AllocationUser.objects.create(
                            allocation=allocation_obj, user=user_obj, status=allocation_user_active_status_choice)

                    allocation_activate_user.send(sender=self.__class__,
                                                  allocation_user_pk=allocation_user_obj.pk)
            if added_users:
                messages.success(
                    request,
                    'Added user(s) {} to allocation.'.format(', '.join(added_users))
                )
            if denied_users:
                messages.warning(
                    request,
                    'Did not add user(s) {} to allocation. An account is needed for this resource: https://access.iu.edu/Accounts/Create.'.format(', '.join(denied_users))
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
            messages.error(request, 'You cannot remove users from a allocation with status {}.'.format(
                allocation_obj.status.name))
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_remove(self, allocation_obj):
        users_to_remove = list(allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed', 'Error', ]).values_list('user__username', flat=True))

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

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_to_remove = self.get_users_to_remove(allocation_obj)
        context = {}

        if users_to_remove:
            formset = formset_factory(
                AllocationRemoveUserForm, max_num=len(users_to_remove))
            formset = formset(initial=users_to_remove, prefix='userform')
            context['formset'] = formset

        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_to_remove = self.get_users_to_remove(allocation_obj)

        formset = formset_factory(
            AllocationRemoveUserForm, max_num=len(users_to_remove))
        formset = formset(
            request.POST, initial=users_to_remove, prefix='userform')

        remove_users_count = 0

        if formset.is_valid():
            allocation_user_removed_status_choice = AllocationUserStatusChoice.objects.get(
                name='Removed')
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    remove_users_count += 1

                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))
                    if allocation_obj.project.pi == user_obj:
                        continue

                    allocation_user_obj = allocation_obj.allocationuser_set.get(
                        user=user_obj)
                    allocation_user_obj.status = allocation_user_removed_status_choice
                    allocation_user_obj.save()
                    allocation_remove_user.send(sender=self.__class__,
                                                allocation_user_pk=allocation_user_obj.pk)

            messages.success(
                request, 'Removed {} users from allocation.'.format(remove_users_count))
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
            status__name__in=['New', 'Renewal Requested', 'Paid', ])
        context['allocation_list'] = allocation_list
        context['PROJECT_ENABLE_PROJECT_REVIEW'] = PROJECT_ENABLE_PROJECT_REVIEW
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

    def get(self, request, pk):
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        allocation_status_active_obj = AllocationStatusChoice.objects.get(
            name='Active')
        start_date = datetime.datetime.now()
        end_date = datetime.datetime.now(
        ) + relativedelta(days=ALLOCATION_DEFAULT_ALLOCATION_LENGTH)

        if allocation_obj.use_indefinitely:
            end_date = None

        allocation_obj.status = allocation_status_active_obj
        allocation_obj.start_date = start_date
        allocation_obj.end_date = end_date
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

        if EMAIL_ENABLED:
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'allocation_url': allocation_url,
                'signature': EMAIL_SIGNATURE,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
            }

            email_receiver_list = []

            for allocation_user in allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                allocation_activate_user.send(
                    sender=self.__class__, allocation_user_pk=allocation_user.pk)
                if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                    email_receiver_list.append(allocation_user.user.email)

            send_email_template(
                'Allocation Activated',
                'email/allocation_activated.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )

        return HttpResponseRedirect(reverse('allocation-request-list'))


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

        if EMAIL_ENABLED:
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'allocation_url': allocation_url,
                'signature': EMAIL_SIGNATURE,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
            }

            email_receiver_list = []
            for allocation_user in allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error']):
                allocation_remove_user.send(
                            sender=self.__class__, allocation_user_pk=allocation_user.pk)
                if allocation_user.allocation.project.projectuser_set.get(user=allocation_user.user).enable_notifications:
                    email_receiver_list.append(allocation_user.user.email)

            send_email_template(
                'Allocation Denied',
                'email/allocation_denied.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )
            print(email_receiver_list)
        return HttpResponseRedirect(reverse('allocation-request-list'))


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
            messages.error(request, 'You cannot renew a allocation with status {}.'.format(
                allocation_obj.status.name))
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.project.needs_review:
            messages.error(
                request, 'You cannot renew your allocation because you have to review your project first.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': allocation_obj.project.pk}))

        if allocation_obj.expires_in > 60:
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

                send_email_template(
                    'Allocation renewed: {} - {}'.format(
                        pi_name, resource_name),
                    'email/allocation_renewed.txt',
                    template_context,
                    EMAIL_SENDER,
                    [EMAIL_TICKET_SYSTEM_ADDRESS, ]
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

    def get_queryset(self):

        allocations = Allocation.objects.filter(
            status__name__in=['Paid', 'Payment Pending', 'Payment Requested', 'Payment Declined', ])
        return allocations


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
            allocation_obj.status = form_data.get('status')
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

    def get(self, request):
        file_name = request.GET["file_name"]
        resource = request.GET["resource"]

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
        elif resource == "Slate Project":
            header = [
                'Name',
                'Acount*'
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
