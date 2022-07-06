import datetime
import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms import formset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html, mark_safe
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
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
                                             AllocationRemoveUserForm,
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
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import (allocation_activate,
                                               allocation_activate_user,
                                               allocation_disable,
                                               allocation_remove_user,
                                               allocation_change_approved,)
from coldfront.core.allocation.utils import (generate_guauge_data_from_usage,
                                             get_user_resources)
from coldfront.core.project.models import (Project, ProjectUser,
                                           ProjectUserStatusChoice)
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email_template

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
        context['allocation_changes'] = allocation_changes

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
            end_date = form_data.get('end_date')
            start_date = form_data.get('start_date')
            description = form_data.get('description')
            is_locked = form_data.get('is_locked')
            is_changeable = form_data.get('is_changeable')

            allocation_obj.description = description
            allocation_obj.save()

            old_status = allocation_obj.status.name
            new_status = form_data.get('status').name

            allocation_obj.status = form_data.get('status')
            allocation_obj.is_locked = is_locked
            allocation_obj.is_changeable = is_changeable
            allocation_obj.save()

            if start_date and allocation_obj.start_date != start_date:
                allocation_obj.start_date = start_date
                allocation_obj.save()

            if end_date and allocation_obj.end_date != end_date:
                allocation_obj.end_date = end_date
                allocation_obj.save()

            if EMAIL_ENABLED:
                resource_name = allocation_obj.get_parent_resource
                domain_url = get_domain_url(self.request)
                allocation_url = '{}{}'.format(domain_url, reverse(
                    'allocation-detail', kwargs={'pk': allocation_obj.pk}))

            if old_status != 'Active' and new_status == 'Active':
                if not start_date:
                    start_date = datetime.datetime.now()
                if not end_date:
                    end_date = datetime.datetime.now(
                    ) + relativedelta(days=ALLOCATION_DEFAULT_ALLOCATION_LENGTH)

                allocation_obj.start_date = start_date
                allocation_obj.end_date = end_date
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
                allocation_obj.start_date = None
                allocation_obj.end_date = None
                allocation_obj.save()

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

            elif old_status != 'New' and new_status == 'New':
                allocation_obj.start_date = None
                allocation_obj.end_date = None
                allocation_obj.save()

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
                    Q(allocationattribute__value__contains=data.get(
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
        resources_with_eula = {}
        for resource in user_resources:
            if resource.resourceattribute_set.filter(resource_attribute_type__name='quantity_default_value').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='quantity_default_value').value
                resources_form_default_quantities[resource.id] = int(value)
            if resource.resourceattribute_set.filter(resource_attribute_type__name='quantity_label').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='quantity_label').value
                resources_form_label_texts[resource.id] = mark_safe(
                    '<strong>{}*</strong>'.format(value))
            if resource.resourceattribute_set.filter(resource_attribute_type__name='eula').exists():
                value = resource.resourceattribute_set.get(
                    resource_attribute_type__name='eula').value
                resources_with_eula[resource.id] = value

        context['AllocationAccountForm'] = AllocationAccountForm()
        context['resources_form_default_quantities'] = resources_form_default_quantities
        context['resources_form_label_texts'] = resources_form_label_texts
        context['resources_with_eula'] = resources_with_eula
        context['resources_with_accounts'] = list(Resource.objects.filter(
            name__in=list(ALLOCATION_ACCOUNT_MAPPING.keys())).values_list('id', flat=True))

        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.request.user, self.kwargs.get('project_pk'), **self.get_form_kwargs())

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        resource_obj = form_data.get('resource')
        justification = form_data.get('justification')
        quantity = form_data.get('quantity', 1)
        allocation_account = form_data.get('allocation_account', None)
        # A resource is selected that requires an account name selection but user has no account names
        if ALLOCATION_ACCOUNT_ENABLED and resource_obj.name in ALLOCATION_ACCOUNT_MAPPING and AllocationAttributeType.objects.filter(
                name=ALLOCATION_ACCOUNT_MAPPING[resource_obj.name]).exists() and not allocation_account:
            form.add_error(None, format_html(
                'You need to create an account name. Create it by clicking the link under the "Allocation account" field.'))
            return self.form_invalid(form)

        usernames = form_data.get('users')
        usernames.append(project_obj.pi.username)
        usernames = list(set(usernames))

        users = [User.objects.get(username=username) for username in usernames]
        if project_obj.pi not in users:
            users.append(project_obj.pi)

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
            status=allocation_status_obj
        )
        
        if ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT: 
            allocation_obj.is_changeable = True
            allocation_obj.save()

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

        formset = formset_factory(
            AllocationAddUserForm, max_num=len(users_to_add))
        formset = formset(request.POST, initial=users_to_add,
                          prefix='userform')

        users_added_count = 0

        if formset.is_valid():

            allocation_user_active_status_choice = AllocationUserStatusChoice.objects.get(
                name='Active')

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    users_added_count += 1

                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

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
            messages.success(
                request, 'Added {} users to allocation.'.format(users_added_count))
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

        if allocation_obj.status.name not in ['Active', 'New', 'Renewal Requested', ]:
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

            if remove_users_count == 1:
                messages.success(
                    request, 'Removed {} user from allocation.'.format(remove_users_count))
            else:
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
            status__name__in=['New', 'Renewal Requested', 'Paid', 'Approved',])
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

    def get(self, request, pk):
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        allocation_status_active_obj = AllocationStatusChoice.objects.get(
            name='Active')
        start_date = datetime.datetime.now()
        end_date = datetime.datetime.now(
        ) + relativedelta(days=ALLOCATION_DEFAULT_ALLOCATION_LENGTH)

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
                    email_receiver_list.append(allocation_user.user.email)

            send_email_template(
                'Allocation Activated',
                'email/allocation_activated.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )
        if 'request-list' in request.META.get('HTTP_REFERER'):
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
            status__name__in=['Pending', ])
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

        if allocation_obj.project.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot request a change to an allocation in an archived project.')
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

                        send_email_template(
                            'New Allocation Change Request: {} - {}'.format(
                                pi_name, resource_name),
                            'email/new_allocation_change_request.txt',
                            template_context,
                            EMAIL_SENDER,
                            [EMAIL_TICKET_SYSTEM_ADDRESS, ]
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

                    send_email_template(
                        'New Allocation Change Request: {} - {}'.format(
                            pi_name, resource_name),
                        'email/new_allocation_change_request.txt',
                        template_context,
                        EMAIL_SENDER,
                        [EMAIL_TICKET_SYSTEM_ADDRESS, ]
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
