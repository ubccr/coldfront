import datetime
import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.validators import validate_email
from django.core.validators import ValidationError
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
                                             AllocationClusterAccountRequestActivationForm,
                                             AllocationClusterAccountUpdateStatusForm,
                                             AllocationForm,
                                             AllocationInvoiceNoteDeleteForm,
                                             AllocationInvoiceUpdateForm,
                                             AllocationRemoveUserForm,
                                             AllocationRequestClusterAccountForm,
                                             AllocationReviewUserForm,
                                             AllocationSearchForm,
                                             AllocationUpdateForm,
                                             ClusterRequestSearchForm)
from coldfront.core.allocation.models import (Allocation, AllocationAccount,
                                              AllocationAttribute,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUser,
                                              AllocationUserAttribute,
                                              AllocationUserNote,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import (allocation_activate_user,
                                               allocation_remove_user)
from coldfront.core.allocation.utils import (generate_guauge_data_from_usage,
                                             get_user_resources,
                                             set_allocation_user_attribute_value)
from coldfront.core.project.models import (Project, ProjectUser,
                                           ProjectUserStatusChoice)
from coldfront.core.project.utils import ProjectClusterAccessRequestRunner
from coldfront.core.resource.models import Resource
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.common import utc_now_offset_aware
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
        allocation_users = allocation_obj.allocationuser_set.order_by('user__username')

        # Manually display "Service Units" for each user if applicable.
        # TODO: Avoid doing this manually.
        kwargs = {
            'allocation_attribute_type__name': 'Service Units',
        }
        has_service_units = allocation_obj.allocationattribute_set.filter(
            **kwargs)
        allocation_user_su_usages = {}
        if has_service_units:
            for allocation_user in allocation_users:
                username = allocation_user.user.username
                user_attributes = \
                    allocation_user.allocationuserattribute_set.select_related(
                        'allocationuserattributeusage'
                    ).filter(**kwargs)
                usage = '0.00'
                if user_attributes.exists():
                    attribute = user_attributes.first()
                    try:
                        usage = str(
                            attribute.allocationuserattributeusage.value)
                    except AttributeError:
                        pass
                allocation_user_su_usages[username] = usage

        context['has_service_units'] = has_service_units
        context['allocation_user_su_usages'] = allocation_user_su_usages

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
            if project_user.role.name in ('Principal Investigator', 'Manager'):
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
            if project_user.role.name in ('Principal Investigator', 'Manager'):
                context['is_allowed_to_update_project'] = True
            else:
                context['is_allowed_to_update_project'] = False
        else:
            context['is_allowed_to_update_project'] = False

        # Filter users by whether they have been removed from the allocation.
        allocation_user_status_choice_removed = \
            AllocationUserStatusChoice.objects.get(name='Removed')
        context['allocation_users'] = \
            allocation_users.exclude(status=allocation_user_status_choice_removed)
        context['allocation_users_removed_from_proj'] = \
            allocation_users.filter(status=allocation_user_status_choice_removed)

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
                    for allocation_user in allocation_obj.project.projectuser_set.all():
                        if allocation_user.enable_notifications:
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


class AllocationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):

    model = Allocation
    template_name = 'allocation/allocation_list.html'
    context_object_name = 'allocation_list'
    paginate_by = 25

    def test_func(self):
        """Temporary block: Only allow superusers access."""
        # TODO: Remove this block when allocations should be displayed.
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_view_all_allocations'):
            return True

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
                    'project', 'status',).all().order_by(order_by)
            else:
                allocations = Allocation.objects.prefetch_related('project', 'status',).filter(
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
                    Q(allocationuser__user__username__icontains=data.get('username')) &
                    (Q(project__projectuser__role__name='Principal Investigator') |
                     Q(allocationuser__status__name='Active'))
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
            allocations = Allocation.objects.prefetch_related('project', 'status',).filter(
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

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
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
        pi_users = project_obj.pis()
        for pi_user in pi_users:
            usernames.append(pi_user.username)
        usernames = list(set(usernames))

        users = [User.objects.get(username=username) for username in usernames]
        for pi_user in pi_users:
            if pi_user not in users:
                users.append(pi_user)

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

        pi_names = []
        for pi in allocation_obj.project.pis():
            pi_names.append('{} {} ({})'.format(
                pi.first_name, pi.last_name, pi.username))
        pi_names = ', '.join(pi_names)

        resource_name = allocation_obj.get_parent_resource
        domain_url = get_domain_url(self.request)
        url = '{}{}'.format(domain_url, reverse('allocation-request-list'))

        if EMAIL_ENABLED:
            template_context = {
                'pi': pi_names,
                'resource': resource_name,
                'url': url
            }

            send_email_template(
                'New allocation request: {} - {}'.format(
                    project_obj.name, resource_name),
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
        missing_users = User.objects.filter(username__in=missing_users)
        pi_pks = allocation_obj.project.pis().values_list('pk', flat=True)
        missing_users = missing_users.exclude(pk__in=pi_pks)

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

        users_to_remove = User.objects.filter(username__in=users_to_remove)
        exclude_pks = list(
            allocation_obj.project.pis().values_list('pk', flat=True))
        exclude_pks.append(self.request.user.pk)
        users_to_remove = users_to_remove.exclude(pk__in=exclude_pks)

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
                    if allocation_obj.project.pis().filter(
                            pk=user_obj.pk).exists():
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

        messages.success(
            request, 'Allocation to {} has been ACTIVATED for {}'.format(
                allocation_obj.get_parent_resource,
                allocation_obj.project.name)
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

        messages.success(
            request, 'Allocation to {} has been DENIED for {}'.format(
                allocation_obj.resources.first(),
                allocation_obj.project.name)
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
            for allocation_user in allocation_obj.project.projectuser_set.all():
                if allocation_user.enable_notifications:
                    email_receiver_list.append(allocation_user.user.email)

            send_email_template(
                'Allocation Denied',
                'email/allocation_denied.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )

        return HttpResponseRedirect(reverse('allocation-request-list'))


class AllocationRenewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_renew.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
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
            status__name__in=['Removed'])
        exclude_pks = list(
            allocation_obj.project.pis().values_list('pk', flat=True))
        exclude_pks.append(self.request.user.pk)
        users_in_allocation = users_in_allocation.exclude(
            user__pk__in=exclude_pks).order_by('user__username')

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

            pi_names = []
            for pi in allocation_obj.project.pis():
                pi_names.append('{} {} ({})'.format(
                    pi.first_name, pi.last_name, pi.username))
            pi_names = ', '.join(pi_names)

            resource_name = allocation_obj.get_parent_resource
            domain_url = get_domain_url(self.request)
            url = '{}{}'.format(domain_url, reverse(
                'allocation-request-list'))

            if EMAIL_ENABLED:
                template_context = {
                    'pi': pi_names,
                    'resource': resource_name,
                    'url': url
                }

                send_email_template(
                    'Allocation renewed: {} - {}'.format(
                        allocation_obj.project.name, resource_name),
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


class AllocationRequestClusterAccountView(LoginRequiredMixin,
                                          UserPassesTestMixin, View):

    def test_func(self):
        """UserPassesTestMixin tests."""
        user = self.request.user

        if user.is_superuser:
            return True

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.allocationuser_set.filter(
                user=self.request.user,
                status__name='Active').exists():
            return True
        else:
            message = (
                'You do not have permission to request cluster access under '
                'the allocation.')
            messages.error(self.request, message)
            return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))
        user_obj = get_object_or_404(User, pk=self.kwargs.get('user_pk'))
        project_obj = allocation_obj.project

        redirect = HttpResponseRedirect(
            reverse('project-detail', kwargs={'pk': project_obj.pk}))

        if not user_obj.userprofile.access_agreement_signed_date:
            message = (
                f'User {user_obj.username} has not signed the access '
                f'agreement.')
            messages.error(self.request, message)
            return redirect

        if not allocation_obj.allocationuser_set.filter(
                user=user_obj, status__name='Active').exists():
            message = (
                f'User {user_obj.username} is not a member of allocation '
                f'{allocation_obj.pk}.')
            messages.error(self.request, message)
            return redirect

        acceptable_statuses = [
            'Active', 'New', 'Renewal Requested', 'Payment Pending',
            'Payment Requested', 'Paid']
        if allocation_obj.status.name not in acceptable_statuses:
            message = (
                f'You cannot request cluster access under an allocation '
                f'with status {allocation_obj.status.name}.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))
        user_obj = get_object_or_404(User, pk=self.kwargs.get('user_pk'))
        project_obj = allocation_obj.project

        redirect = HttpResponseRedirect(
            reverse('project-detail', kwargs={'pk': project_obj.pk}))

        try:
            project_user_obj = ProjectUser.objects.get(
                user=user_obj, project=project_obj)
        except ProjectUser.DoesNotExist:
            message = (
                'Unexpected server error. Please contact an administrator.')
            messages.error(self.request, message)
            return redirect

        request_runner = ProjectClusterAccessRequestRunner(project_user_obj)
        runner_result = request_runner.run()
        if runner_result.success:
            message = (
                f'Created a cluster access request for User {user_obj.pk} '
                f'under Project {project_obj.pk}.')
            messages.success(self.request, message)
        else:
            messages.error(self.request, runner_result.error_message)

        return redirect


class AllocationClusterAccountRequestListView(LoginRequiredMixin,
                                              UserPassesTestMixin,
                                              ListView):
    template_name = 'allocation/allocation_cluster_account_request_list.html'
    login_url = '/'
    completed = False
    paginate_by = 30
    context_object_name = "cluster_request_list"

    def get_queryset(self):
        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            if direction == 'asc':
                direction = ''
            else:
                direction = '-'
            order_by = direction + order_by
        else:
            order_by = '-modified'
        cluster_account_status = AllocationAttributeType.objects.get(
            name='Cluster Account Status')

        cluster_search_form = ClusterRequestSearchForm(self.request.GET)

        if self.completed:
            cluster_account_list = AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                value__in=['Denied', 'Active'])
        else:
            cluster_account_list = AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                value__in=['Pending - Add', 'Processing'])

        if cluster_search_form.is_valid():
            data = cluster_search_form.cleaned_data

            if data.get('username'):
                cluster_account_list = cluster_account_list.filter(allocation_user__user__username__icontains=data.get('username'))

            if data.get('email'):
                cluster_account_list = cluster_account_list.filter(allocation_user__user__email__icontains=data.get('email'))

            if data.get('project_name'):
                cluster_account_list = cluster_account_list.filter(allocation_user__allocation__project__name__icontains=data.get('project_name'))

            if data.get('request_status'):
                cluster_account_list = cluster_account_list.filter(value__icontains=data.get('request_status'))

        return cluster_account_list.order_by(order_by)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_cluster_account_requests'):
            return True

        message = (
            'You do not have permission to review cluster account requests.')
        messages.error(self.request, message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cluster_search_form = ClusterRequestSearchForm(self.request.GET)
        if cluster_search_form.is_valid():
            context['cluster_search_form'] = cluster_search_form
            data = cluster_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['cluster_search_form'] = cluster_search_form
        else:
            filter_parameters = None
            context['cluster_search_form'] = ClusterRequestSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        context['request_filter'] = (
            'completed' if self.completed else 'pending')
        cluster_account_list = self.get_queryset()

        paginator = Paginator(cluster_account_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            cluster_accounts = paginator.page(page)
        except PageNotAnInteger:
            cluster_accounts = paginator.page(1)
        except EmptyPage:
            cluster_accounts = paginator.page(paginator.num_pages)

        context['cluster_account_list'] = cluster_accounts

        context['actions_visible'] = not self.completed

        return context


class AllocationClusterAccountUpdateStatusView(LoginRequiredMixin,
                                               UserPassesTestMixin, FormView):
    form_class = AllocationClusterAccountUpdateStatusForm
    login_url = '/'
    template_name = (
        'allocation/allocation_update_cluster_account_status.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to modify a cluster access request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.allocation_user_attribute_obj = get_object_or_404(
            AllocationUserAttribute, pk=self.kwargs.get('pk'))
        self.user_obj = self.allocation_user_attribute_obj.allocation_user.user
        status = self.allocation_user_attribute_obj.value
        if status != 'Pending - Add':
            message = f'Cluster access has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('allocation-cluster-account-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data.get('status')

        allocation_obj = self.allocation_user_attribute_obj.allocation
        project_obj = allocation_obj.project

        self.allocation_user_attribute_obj.value = status
        self.allocation_user_attribute_obj.save()

        message = (
            f'Cluster access request from User {self.user_obj.email} under '
            f'Project {project_obj.name} and Allocation {allocation_obj.pk} '
            f'has been updated to have status "{status}".')
        messages.success(self.request, message)

        log_message = (
            f'Superuser {self.request.user.pk} changed the value of "Cluster '
            f'Account Status" AllocationUserAttribute '
            f'{self.allocation_user_attribute_obj.pk} from "Pending - Add" to '
            f'"{status}".')
        logger.info(log_message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cluster_account'] = self.allocation_user_attribute_obj
        return context

    def get_initial(self):
        initial = {
            'status': self.allocation_user_attribute_obj.value,
        }
        return initial

    def get_success_url(self):
        return reverse('allocation-cluster-account-request-list')


class AllocationClusterAccountActivateRequestView(LoginRequiredMixin,
                                                  UserPassesTestMixin,
                                                  FormView):
    form_class = AllocationClusterAccountRequestActivationForm
    login_url = '/'
    template_name = (
        'allocation/allocation_activate_cluster_account_request.html')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to activate a cluster access '
            'request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.allocation_user_attribute_obj = get_object_or_404(
            AllocationUserAttribute, pk=self.kwargs.get('pk'))
        self.user_obj = self.allocation_user_attribute_obj.allocation_user.user
        status = self.allocation_user_attribute_obj.value
        if status != 'Processing':
            message = f'Cluster access has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('allocation-cluster-account-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        username = form_data.get('username')
        cluster_uid = form_data.get('cluster_uid')

        self.user_obj.username = username
        self.user_obj.userprofile.cluster_uid = cluster_uid
        self.user_obj.userprofile.save()
        self.user_obj.save()

        allocation_obj = self.allocation_user_attribute_obj.allocation
        project_obj = allocation_obj.project

        # For Savio projects, set the user's service units to that of
        # the allocation. Attempt this before setting the status to
        # 'Active' so that failures block completion.
        if not project_obj.name.startswith(('abc', 'vector_')):
            self.__set_user_service_units()

        self.allocation_user_attribute_obj.value = 'Active'
        self.allocation_user_attribute_obj.save()

        message = (
            f'Cluster access request from User {self.user_obj.email} under '
            f'Project {project_obj.name} and Allocation {allocation_obj.pk} '
            f'has been ACTIVATED.')
        messages.success(self.request, message)

        log_message = (
            f'Superuser {self.request.user.pk} changed the value of "Cluster '
            f'Account Status" AllocationUserAttribute '
            f'{self.allocation_user_attribute_obj.pk} from "Processing" to '
            f'"Active".')
        logger.info(log_message)

        if EMAIL_ENABLED:
            subject = 'Cluster Access Activated'
            template = 'email/cluster_access_activated.txt'

            CENTER_USER_GUIDE = import_from_settings('CENTER_USER_GUIDE')
            CENTER_LOGIN_GUIDE = import_from_settings('CENTER_LOGIN_GUIDE')
            CENTER_HELP_EMAIL = import_from_settings('CENTER_HELP_EMAIL')

            template_context = {
                'user': self.user_obj,
                'project_name': project_obj.name,
                'center_user_guide': CENTER_USER_GUIDE,
                'center_login_guide': CENTER_LOGIN_GUIDE,
                'center_help_email': CENTER_HELP_EMAIL,
                'signature': EMAIL_SIGNATURE,
            }
            sender = EMAIL_SENDER

            user_filter = Q(user=self.user_obj)
            manager_pi_filter = Q(
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active')
            receiver_list = list(
                project_obj.projectuser_set.filter(
                    user_filter | manager_pi_filter, enable_notifications=True
                ).values_list(
                    'user__email', flat=True
                ))

            send_email_template(
                subject, template, template_context, sender, receiver_list)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cluster_account'] = self.allocation_user_attribute_obj
        return context

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(
            self.user_obj, self.kwargs.get('pk'), **self.get_form_kwargs())

    def get_initial(self):
        user = self.user_obj
        initial = {
            'username': user.username,
            'cluster_uid': user.userprofile.cluster_uid,
        }
        # If the user's username is an email address, because no cluster
        # username has been set yet, leave the field blank.
        try:
            validate_email(user.username)
        except ValidationError:
            pass
        else:
            initial['username'] = ''
        return initial

    def get_success_url(self):
        return reverse('allocation-cluster-account-request-list')

    def __set_user_service_units(self):
        """Set the AllocationUser's 'Service Units' attribute value to
        that of the Allocation."""
        allocation_obj = self.allocation_user_attribute_obj.allocation
        allocation_user_obj = \
            self.allocation_user_attribute_obj.allocation_user
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_service_units = allocation_obj.allocationattribute_set.get(
            allocation_attribute_type=allocation_attribute_type)
        set_allocation_user_attribute_value(
            allocation_user_obj, 'Service Units',
            allocation_service_units.value)
        # Create a ProjectUserTransaction to store the change in service units.
        project_user = ProjectUser.objects.get(
            user=self.user_obj,
            project=self.allocation_user_attribute_obj.allocation.project)
        ProjectUserTransaction.objects.create(
            project_user=project_user,
            date_time=utc_now_offset_aware(),
            allocation=Decimal(allocation_service_units.value))


class AllocationClusterAccountDenyRequestView(LoginRequiredMixin,
                                              UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to deny a cluster access request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.allocation_user_attribute_obj = get_object_or_404(
            AllocationUserAttribute, pk=self.kwargs.get('pk'))
        self.user_obj = self.allocation_user_attribute_obj.allocation_user.user
        status = self.allocation_user_attribute_obj.value
        if status not in ('Pending - Add', 'Processing'):
            message = f'Cluster access has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('allocation-cluster-account-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.allocation_user_attribute_obj.value = 'Denied'
        self.allocation_user_attribute_obj.save()

        allocation_obj = self.allocation_user_attribute_obj.allocation
        project_obj = allocation_obj.project
        message = (
            f'Cluster access request from User {self.user_obj.email} under '
            f'Project {project_obj.name} and Allocation {allocation_obj.pk} '
            f'has been DENIED.')
        messages.success(request, message)

        if EMAIL_ENABLED:
            domain_url = get_domain_url(self.request)
            view_name = 'allocation-detail'
            view = reverse(view_name, kwargs={'pk': allocation_obj.pk})

            subject = 'Cluster Access Denied'
            template = 'email/cluster_access_denied.txt'
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'project': project_obj.name,
                'allocation': allocation_obj.pk,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
                'signature': EMAIL_SIGNATURE,
            }
            sender = EMAIL_SENDER

            user_filter = Q(user=self.user_obj)
            manager_pi_filter = Q(
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active')
            receiver_list = list(
                project_obj.projectuser_set.filter(
                    user_filter | manager_pi_filter, enable_notifications=True
                ).values_list(
                    'user__email', flat=True
                ))

            send_email_template(
                subject, template, template_context, sender, receiver_list)

        return HttpResponseRedirect(
            reverse('allocation-cluster-account-request-list'))
