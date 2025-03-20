import re
import sys
import traceback
import logging
import datetime
from datetime import date

from io import BytesIO
from lib2to3.fixes.fix_input import context
import requests

from xhtml2pdf import pisa

from dateutil.relativedelta import relativedelta
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.forms import formset_factory
from django.http import (HttpResponseRedirect,
                        JsonResponse, HttpResponse,
                        HttpResponseBadRequest, HttpResponseForbidden)
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html, mark_safe
from django.views import View
from django.template.loader import render_to_string
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, FormView

from coldfront.core.utils.views import ColdfrontListView, NoteCreateView, NoteUpdateView
from coldfront.core.user.forms import UserSearchForm
from coldfront.core.allocation.forms import (AllocationAccountForm,
                                             AllocationAddUserForm,
                                             AllocationApprovalForm,
                                             AllocationAttributeCreateForm,
                                             AllocationAttributeDeleteForm,
                                             AllocationChangeForm,
                                             AllocationChangeNoteForm,
                                             AllocationAttributeChangeForm,
                                             AllocationAttributeUpdateForm,
                                             AllocationForm,
                                             AllocationAutoUpdateForm,
                                             AllocationInvoiceNoteDeleteForm,
                                             AllocationInvoiceUpdateForm,
                                             AllocationRemoveUserForm,
                                             AllocationReviewUserForm,
                                             AllocationSearchForm,
                                             AllocationUpdateForm,
                                             AllocationUserAttributeUpdateForm,
                                             AllocationAddNonProjectUserForm)
from coldfront.core.allocation.models import (Allocation,
                                              AllocationPermission,
                                              AllocationAccount,
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
                                               allocation_autocreate,
                                               allocation_activate_user,
                                               allocation_user_add_on_slurm,
                                               allocation_disable,
                                               allocation_remove_user,
                                               allocation_change_approved,
                                               allocation_user_attribute_edit,
                                               allocation_user_remove_on_slurm)
from coldfront.core.allocation.utils import (generate_guauge_data_from_usage,
                                             get_user_resources)
from coldfront.core.project.models import (Project, ProjectPermission,
                                           ProjectUserStatusChoice)
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_allocation_admin_email, send_allocation_customer_email

from coldfront.plugins.slurm.utils import SlurmError

if 'ifxbilling' in settings.INSTALLED_APPS:
    from fiine.client import API as FiineAPI
    from ifxbilling.models import Account, UserProductAccount
if 'django_q' in settings.INSTALLED_APPS:
    from django_q.tasks import Task
if 'coldfront.plugins.isilon' in settings.INSTALLED_APPS:
    from coldfront.plugins.isilon.utils import update_isilon_allocation_quota

ALLOCATION_ENABLE_ALLOCATION_RENEWAL = import_from_settings(
    'ALLOCATION_ENABLE_ALLOCATION_RENEWAL', True)
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = import_from_settings(
    'ALLOCATION_DEFAULT_ALLOCATION_LENGTH', 365)
ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT = import_from_settings(
    'ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT', True)

PROJECT_ENABLE_PROJECT_REVIEW = import_from_settings(
    'PROJECT_ENABLE_PROJECT_REVIEW', False)
INVOICE_ENABLED = import_from_settings('INVOICE_ENABLED', False)
if INVOICE_ENABLED:
    INVOICE_DEFAULT_STATUS = import_from_settings(
        'INVOICE_DEFAULT_STATUS', 'Pending Payment')

ALLOCATION_ACCOUNT_ENABLED = import_from_settings('ALLOCATION_ACCOUNT_ENABLED', False)
ALLOCATION_ACCOUNT_MAPPING = import_from_settings('ALLOCATION_ACCOUNT_MAPPING', {})

PENDING_ALLOCATION_STATUSES = import_from_settings(
    'PENDING_ALLOCATION_STATUSES', ['New'])
ACTIVE_ALLOCATION_STATUSES = import_from_settings(
    'ACTIVE_ALLOCATION_STATUSES', ['Active'])
PENDING_ACTIVE_ALLOCATION_STATUSES = import_from_settings(
    'PENDING_ACTIVE_ALLOCATION_STATUSES', ['Active', 'New', 'Renewal Requested'])

logger = logging.getLogger(__name__)


def allocation_filter(allocations, user):
    """Offer a definitive list of the allocations that are shown to a user"""
    allocations = allocations.filter(
        Q(status__name__in=['Active', 'New', 'Renewal Requested', ]) &
        Q(project__status__name__in=['New', 'Active', ]) &
        # Q(project__projectuser__status__name='Active') &
        # Q(project__projectuser__user=self.request.user) &
        (
            (
                (
                    Q(resources__resource_type__name__contains='Storage') &
                    (
                        (Q(project__projectuser__user=user) &
                        Q(project__projectuser__status__name='Active')) |
                        (Q(allocationuser__user=user) &
                        Q(allocationuser__status__name='Active'))
                    )
                ) | (
                    Q(resources__resource_type__name__contains='Cluster') &
                    Q(allocationuser__user=user) &
                    Q(allocationuser__status__name='Active')
                )
            ) |
            Q(project__pi=user) |
            Q(resources__allowed_users=user) | (
                Q(project__projectuser__user=user) &
                Q(project__projectuser__status__name='Active') &
                Q(project__projectuser__role__name__contains='Manager')
            )
        )
    ).distinct()
    return allocations

def attribute_and_usage_as_floats(attribute):
    """return a tuple of a given attribute's value and its
    allocationattributeusage value, converted to floats.
    """
    usage = float(attribute.allocationattributeusage.value)
    attribute = float(attribute.value)
    return (attribute, usage)

def make_allocation_change_message(allocation_change_obj, approval):
    return 'Allocation change request to {} has been {} for {} {} ({})'.format(
        allocation_change_obj.allocation.get_parent_resource,
        approval,
        allocation_change_obj.allocation.project.pi.first_name,
        allocation_change_obj.allocation.project.pi.last_name,
        allocation_change_obj.allocation.project.pi.username
    )

class AllocationDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Allocation
    template_name = 'allocation/allocation_detail.html'
    context_object_name = 'allocation'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.has_perm('allocation.can_view_all_allocations'):
            return True
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        return allocation_obj.has_perm(self.request.user, AllocationPermission.USER)

    def get_allocation_users(self, allocation):
        if allocation.get_parent_resource.resource_type.name == "Storage":
            user_filter = (~Q(usage_bytes=0) & Q(usage_bytes__isnull=False))
            return (
                allocation.allocationuser_set.filter(user_filter).order_by('user__username')
            )
        inactive_status = AllocationUserStatusChoice.objects.get(name='Removed')
        inactive_users_without_usage_filter = (Q(usage=0) & Q(status=inactive_status))
        return allocation.allocationuser_set.exclude(inactive_users_without_usage_filter).order_by('user__username')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['note_update_link'] = 'allocation-note-update'
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        allocation_users = self.get_allocation_users(allocation_obj)
        alloc_attr_set = allocation_obj.get_attribute_set(self.request.user)

        attributes_with_usage = [
            a for a in alloc_attr_set if hasattr(a, 'allocationattributeusage')
        ]
        attributes = list(alloc_attr_set)

        allocation_changes = allocation_obj.allocationchangerequest_set.all().order_by('-pk')

        guage_data = []
        invalid_attributes = []
        for attribute in attributes_with_usage:
            try:
                guage_data.append(generate_guauge_data_from_usage(
                    attribute.allocation_attribute_type.name,
                    float(attribute.value),
                    float(attribute.allocationattributeusage.value)
                )
            )
            except ValueError:
                logger.error(
                    "Allocation attribute '%s' is not an int but has a usage",
                    attribute.allocation_attribute_type.name,
                )
                invalid_attributes.append(attribute)

        for a in invalid_attributes:
            attributes_with_usage.remove(a)

        sync_task_name = None
        user_sync_dt = None
        if 'django_q' in settings.INSTALLED_APPS:
            # get last successful runs of djangoq task responsible for allocationuser data pull
            if allocation_obj.get_parent_resource.resource_type.name == "Storage":
                sync_task_name = "pull_sf_push_cf"
            elif allocation_obj.get_parent_resource.resource_type.name == "Cluster":
                sync_task_name = "xdmod_usage"
            if sync_task_name:
                user_sync_task = Task.objects.filter(
                    func__contains=sync_task_name, success=True
                ).order_by('started').last()
                if user_sync_task:
                    user_sync_dt = user_sync_task.started

        context['user_sync_dt'] = user_sync_dt

        if 'ifxbilling' in settings.INSTALLED_APPS:
            try:
                expense_codes = UserProductAccount.objects.filter(
                    user=allocation_obj.project.pi,
                    is_valid=1,
                    product__product_name=allocation_obj.get_parent_resource.name
                )
            except AttributeError:
                logger.error('allocation has no parent resource: %s', allocation_obj.pk)
                expense_codes = None
            context['expense_codes'] = expense_codes

        offer_letter_code_type = AllocationAttributeType.objects.get(name="Expense Code")
        context['invoice'] = (
            allocation_obj.requires_payment
            and allocation_obj.status.name in ACTIVE_ALLOCATION_STATUSES
            and "Storage" in allocation_obj.get_parent_resource.resource_type.name
        )
        context['expense_code'] = allocation_obj.allocationattribute_set.filter(
            allocation_attribute_type=offer_letter_code_type
        )

        context['guage_data'] = guage_data
        context['attributes_with_usage'] = attributes_with_usage
        context['attributes'] = attributes
        context['allocation_changes'] = allocation_changes

        context['user_can_manage_allocation'] = allocation_obj.user_can_manage_allocation(self.request.user)
        context['allocation_non_project_users'] = allocation_obj.get_non_project_users
        non_project_users_list = [allocation_user.user for allocation_user in context['allocation_non_project_users']]
        context['allocation_users'] = allocation_users.exclude(user__in=non_project_users_list)
        context['note_update_link'] = 'allocation-note-update'

        context['notes'] = self.return_visible_notes(allocation_obj)
        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
        return context

    def return_visible_notes(self, allocation_obj):
        notes = allocation_obj.allocationusernote_set.all()
        if not self.request.user.is_superuser:
            notes = notes.filter(is_private=False)
        return notes

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        initial_data = {
            'status': allocation_obj.status,
            'end_date': allocation_obj.end_date,
            'start_date': allocation_obj.start_date,
            'description': allocation_obj.description,
            'is_locked': allocation_obj.is_locked,
            'is_changeable': allocation_obj.is_changeable,
            'heavy_io': allocation_obj.heavy_io,
            'resource': allocation_obj.get_parent_resource,
        }

        form = AllocationUpdateForm(initial=initial_data)

        context = self.get_context_data()

        if not self.request.user.is_superuser:
            form.fields['is_locked'].disabled = True
            form.fields['is_changeable'].disabled = True
        elif allocation_obj.status.name in PENDING_ALLOCATION_STATUSES:
            approval_form = AllocationApprovalForm()
            context['approval_form'] = approval_form

        context['form'] = form
        context['allocation'] = allocation_obj
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        if not self.request.user.is_superuser:
            err = 'You do not have permission to update the allocation'
            messages.error(request, err)
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

        initial_data = {
            'status': allocation_obj.status,
            'end_date': allocation_obj.end_date,
            'start_date': allocation_obj.start_date,
            'description': allocation_obj.description,
            'is_locked': allocation_obj.is_locked,
            'is_changeable': allocation_obj.is_changeable,
            'resource': allocation_obj.get_parent_resource,
        }
        form = AllocationUpdateForm(request.POST, initial=initial_data)

        if not form.is_valid():
            messages.error(request, 'form is not valid.')
            context = self.get_context_data()
            context['form'] = form
            context['allocation'] = allocation_obj
            return render(request, self.template_name, context)

        action = request.POST.get('action')
        if action not in ['update', 'approve', 'deny']:
            return HttpResponseBadRequest('Invalid request')

        form_data = form.cleaned_data
        old_status = allocation_obj.status.name

        allocation_obj.end_date = form_data.get('end_date')
        allocation_obj.start_date = form_data.get('start_date')
        allocation_obj.description = form_data.get('description')
        allocation_obj.is_locked = form_data.get('is_locked')
        allocation_obj.is_changeable = form_data.get('is_changeable')
        allocation_obj.status = form_data.get('status')

        if 'approve' in action:

            approval_form = AllocationApprovalForm(request.POST)
            if not approval_form.is_valid():
                context = self.get_context_data()
                context['form'] = form
                context['allocation'] = allocation_obj
                context['approval_form'] = approval_form
                return render(request, self.template_name, context)

            err = None
            # ensure that Tier gets swapped out for storage volume
            resource = form_data.get('resource')
            if not resource:
                if "Tier " in allocation_obj.get_parent_resource.name:
                    err = "You must select a resource to approve the form."
                else:
                    resource = allocation_obj.get_parent_resource
            elif 'Tier ' in resource.name:
                err = 'You must select a volume for the selected tier.'
            if err:
                messages.error(request, err)
                return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))
            if action == 'approve':
                # ensure that sheetcheck and auto_create_opts are selected
                autoapproval_choice = approval_form.data.get('auto_create_opts')

                if autoapproval_choice == '2':
                    error = None
                    try:
                        preactivation_responses = allocation_autocreate.send(
                            sender=self.__class__,
                            allocation_obj=allocation_obj,
                            resource=resource,
                            approval_form_data=approval_form.cleaned_data
                        )
                        preactivation_replies = [p[1] for p in preactivation_responses if p[1]]
                        if not preactivation_replies:
                            error = ('this allocation\'s resource has no autocreate options '
                                'at this time. Please manually create the resource '
                                'before approving this request.')
                    except Exception as e:
                        error = f"An error was encountered during autocreation: {e} Please contact your administrator."
                        logger.exception('A350: %s', e)
                    if error:
                        messages.error(request, error)
                        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

            if 'Tier ' in allocation_obj.get_resources_as_string:
                # remove current resource from resources
                allocation_obj.resources.clear()
                # add form_data.get(resource)
                allocation_obj.resources.add(resource)

            allocation_obj.status = AllocationStatusChoice.objects.get(name='Active')
            AllocationAttribute.objects.get_or_create(
                allocation=allocation_obj,
                allocation_attribute_type=AllocationAttributeType.objects.get(name='RequiresPayment'),
                defaults={'value': resource.requires_payment}
            )

        elif action == 'deny':
            allocation_obj.status = AllocationStatusChoice.objects.get(name='Denied')
        elif action == 'update':
            if old_status in PENDING_ALLOCATION_STATUSES and allocation_obj.status.name not in PENDING_ALLOCATION_STATUSES:
                err = "You can only use the 'update' option on new allocations to change their statuses to New, On Hold, or In Progress."
                messages.error(request, err)
                return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

        allocation_users = allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed', 'Error']
        )
        if old_status != 'Active' == allocation_obj.status.name:

            if not form_data.get('resource') and 'Tier ' in allocation_obj.get_parent_resource.name:
                err = "You must select a resource to approve the form. If you do not have the option to select a resource, update the status of the Allocation to 'New' first."
                messages.error(request, err)
                return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))
            if not allocation_obj.start_date:
                allocation_obj.start_date = datetime.datetime.now()
            # if 'approve' in action or not allocation_obj.end_date:
            #     rdelta = relativedelta(days=ALLOCATION_DEFAULT_ALLOCATION_LENGTH)
            #     allocation_obj.end_date = datetime.datetime.now() + rdelta

            allocation_obj.save()

            try:
                allocation_activate.send(sender=self.__class__, allocation_pk=allocation_obj.pk)
            except Exception as e:
                logger.exception(e)
                messages.error(request, "Allocation activated, but certain parts of the post-creation process were unsuccessful. Please contact the administrator or check the logs for more information.")

            for allocation_user in allocation_users:
                allocation_activate_user.send(
                    sender=self.__class__, allocation_user_pk=allocation_user.pk
                )

            send_allocation_customer_email(
                allocation_obj, 'Allocation Activated',
                'email/allocation_activated.txt', domain_url=get_domain_url(self.request)
            )
            if action == 'approve':
                messages.success(request, 'Allocation Activated!')
            elif action == 'auto-approve':
                messages.success(request, 'Allocation to {} has been ACTIVATED for {} {} ({})'.format(
                        allocation_obj.get_parent_resource,
                        allocation_obj.project.pi.first_name,
                        allocation_obj.project.pi.last_name,
                        allocation_obj.project.pi.username
                    )
                )
                return HttpResponseRedirect(reverse('allocation-request-list'))

        elif old_status != allocation_obj.status.name in ['Denied', 'Revoked']+PENDING_ALLOCATION_STATUSES:
            allocation_obj.start_date = None
            allocation_obj.end_date = None
            allocation_obj.save()

            if allocation_obj.status.name in ['Denied', 'Revoked']:
                allocation_disable.send(
                    sender=self.__class__, allocation_pk=allocation_obj.pk
                )
                for allocation_user in allocation_users:
                    allocation_remove_user.send(
                        sender=self.__class__, allocation_user_pk=allocation_user.pk
                    )
                send_allocation_customer_email(
                    allocation_obj,
                    f'Allocation {allocation_obj.status.name}',
                    f'email/allocation_{allocation_obj.status.name.lower()}.txt',
                    domain_url=get_domain_url(self.request),
                )
                messages.success(request, f'Allocation {allocation_obj.status.name}!')
            else:
                messages.success(request, 'Allocation updated!')
        else:
            allocation_obj.save()
            messages.success(request, 'Allocation updated!')

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationListView(ColdfrontListView):

    model = Allocation
    template_name = 'allocation/allocation_list.html'
    context_object_name = 'item_list'

    def get_queryset(self):
        order_by = self.return_order()

        allocation_search_form = AllocationSearchForm(self.request.GET)

        allocations = Allocation.objects.prefetch_related(
            'project', 'project__pi', 'status', 'resources'
        )
        if allocation_search_form.is_valid():
            data = allocation_search_form.cleaned_data

            if data.get('show_all_allocations') and (
                self.request.user.is_superuser or self.request.user.has_perm(
            'allocation.can_view_all_allocations')):
                allocations = allocations.order_by(order_by)
            else:
                allocations = allocation_filter(allocations, self.request.user)
                allocations = allocations.order_by(order_by)

            # Project Title
            if data.get('project'):
                allocations = allocations.filter(
                    project__title__icontains=data.get('project')
                )
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
                    resources__resource_type=data.get('resource_type')
                )
            # Resource Name
            if data.get('resource_name'):
                allocations = allocations.filter(
                    resources__in=data.get('resource_name')
                )
            # Allocation Attribute Name
            if data.get('allocation_attribute_name') and data.get('allocation_attribute_value'):
                allocations = allocations.filter(
                    Q(allocationattribute__allocation_attribute_type=data.get(
                        'allocation_attribute_name')) &
                    Q(allocationattribute__value=data.get('allocation_attribute_value'))
                )

            # End Date
            if data.get('end_date'):
                allocations = allocations.filter(
                    end_date__lt=data.get('end_date'), status__name='Active'
                ).order_by('end_date')

            # Active from now until date
            if data.get('active_from_now_until_date'):
                allocations = allocations.filter(end_date__gte=date.today())
                allocations = allocations.filter(
                    end_date__lt=data.get('active_from_now_until_date'),
                    status__name='Active',
                ).order_by('end_date')

            # Status
            if data.get('status'):
                allocations = allocations.filter(status__in=data.get('status'))
        else:
            allocations = allocations.filter(
                Q(allocationuser__user=self.request.user)
                & Q(allocationuser__status__name='Active')
            ).order_by(order_by)

        return allocations.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            SearchFormClass=AllocationSearchForm, **kwargs
        )
        return context


class AllocationCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AllocationForm
    template_name = 'allocation/allocation_create.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.DATA_MANAGER):
            return True
        err = 'You do not have permission to create a new allocation.'
        messages.error(self.request, err)
        return False

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        err = None
        if project_obj.needs_review:
            err = 'You cannot request a new allocation because you have to review your project first.'
        elif project_obj.status.name not in ['Active', 'New']:
            err = 'You cannot request a new allocation to an archived project.'

        if err:
            messages.error(request, err)
            return HttpResponseRedirect(
                reverse('project-detail', kwargs={'pk': project_obj.pk})
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        context['project'] = project_obj

        user_resources = get_user_resources(self.request.user)
        resources_form_default_quantities = {}
        resources_form_label_texts = {}
        resources_with_eula = {}
        attr_names = ('quantity_default_value', 'quantity_label', 'eula')
        for resource in user_resources:
            for attr_name in attr_names:
                query = Q(resource_attribute_type__name=attr_name)
                if resource.resourceattribute_set.filter(query).exists():
                    value = resource.resourceattribute_set.get(query).value
                    if attr_name == 'quantity_default_value':
                        resources_form_default_quantities[resource.id] = int(value)
                    if attr_name == 'quantity_label':
                        resources_form_label_texts[resource.id] = mark_safe(
                                f'<strong>{value}*</strong>')
                    if attr_name == 'eula':
                        resources_with_eula[resource.id] = value

        # create list of resources for which the project already has an allocation
        project_allocations = project_obj.allocation_set.all()
        tiers_with_allocations = {}

        for allo in project_allocations:
            if allo.get_parent_resource:
                tiers_with_allocations[str(allo.get_parent_resource.pk)] = allo.pk
                if allo.get_parent_resource.parent_resource:
                    tiers_with_allocations[str(
                        allo.get_parent_resource.parent_resource.pk)] = allo.pk

        context['tiers_with_allocations'] = tiers_with_allocations
        context['resources_form_default_quantities'] = resources_form_default_quantities
        context['resources_form_label_texts'] = resources_form_label_texts
        context['resources_with_eula'] = resources_with_eula
        context['resources_with_accounts'] = list(Resource.objects.filter(
            name__in=list(ALLOCATION_ACCOUNT_MAPPING.keys())
        ).values_list('id', flat=True))
        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(
            self.request.user, self.kwargs.get('project_pk'), **self.get_form_kwargs()
        )

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        # pull data from form
        resource_obj = form_data.get('tier')
        justification = form_data.get('justification')
        quantity = form_data.get('quantity', 1)
        allocation_account = form_data.get('allocation_account', None)

        if resource_obj.name == "Tier 3" and quantity % 20 != 0:
            form.add_error("quantity", format_html("Tier 3 quantity must be a multiple of 20."))
            return self.form_invalid(form)

        # A resource is selected that requires an account name selection but user has no account names
        if (
            ALLOCATION_ACCOUNT_ENABLED
            and resource_obj.name in ALLOCATION_ACCOUNT_MAPPING
            and AllocationAttributeType.objects.filter(
                name=ALLOCATION_ACCOUNT_MAPPING[resource_obj.name]
            ).exists()
            and not allocation_account
        ):
            err = 'You need to create an account name. Create it by clicking the link under the "Allocation account" field.'
            form.add_error(None, format_html(err))
            return self.form_invalid(form)

        usernames = form_data.get('users', [])
        usernames.append(project_obj.pi.username)
        usernames = list(set(usernames))

        users = [get_user_model().objects.get(username=uname) for uname in usernames]
        if project_obj.pi not in users:
            users.append(project_obj.pi)

        if INVOICE_ENABLED and resource_obj.requires_payment:
            statusname = INVOICE_DEFAULT_STATUS
        else:
            statusname = 'New'
        allocation_status_obj = AllocationStatusChoice.objects.get(name=statusname)

        allocation_obj = Allocation.objects.create(
            project=project_obj,
            justification=justification,
            quantity=quantity,
            status=allocation_status_obj,
        )

        if ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT:
            allocation_obj.is_changeable = True
            allocation_obj.save()

        allocation_obj.resources.add(resource_obj)

        if (
            ALLOCATION_ACCOUNT_ENABLED
            and allocation_account
            and resource_obj.name in ALLOCATION_ACCOUNT_MAPPING
        ):
            allocation_attribute_type_obj = AllocationAttributeType.objects.get(
                name=ALLOCATION_ACCOUNT_MAPPING[resource_obj.name]
            )
            allocation_obj.allocationattribute_set.create(
                allocation_attribute_type=allocation_attribute_type_obj,
                value=allocation_account,
            )

        expense_code = form_data.get('expense_code', None)
        if expense_code:
            insert_dashes = lambda d: '-'.join(
                [d[:3], d[3:8], d[8:12], d[12:18], d[18:24], d[24:28], d[28:33]]
            )
            expense_code = insert_dashes(re.sub(r'\D', '', expense_code))

        additional_specifications = form_data.get('additional_specifications', None)
        for spec in additional_specifications:
            attr_type = AllocationAttributeType.objects.get(name=spec)
            allocation_obj.allocationattribute_set.create(
                allocation_attribute_type=attr_type, value=True,
            )

        for value, attr_name in (
            (quantity, 'Storage Quota (TB)'),
            (expense_code, 'Expense Code'),
        ):
            allocation_obj.allocationattribute_set.create(
                value=value,
                allocation_attribute_type=AllocationAttributeType.objects.get(
                    name=attr_name
                )
            )

        allocation_obj.set_usage('Storage Quota (TB)', 0)

        allocation_user_active_status = AllocationUserStatusChoice.objects.get(
            name='Active'
        )
        for user in users:
            AllocationUser.objects.create(
                allocation=allocation_obj,
                user=user,
                status=allocation_user_active_status,
            )

        # if requested resource is on NESE, add to vars
        nese = bool(allocation_obj.resources.filter(name__contains="Tier 3"))
        used_percentage = allocation_obj.get_parent_resource.used_percentage

        other_vars = {
            'justification':justification,
            'quantity':quantity,
            'nese': nese,
            'used_percentage': used_percentage,
            'expense_code': expense_code,
            'unmatched_code': False,
            'user': self.request.user,
        }

        if 'ifxbilling' in settings.INSTALLED_APPS:
            try:
                matched_fiineaccts = FiineAPI.listAccounts(code=expense_code)
                if not matched_fiineaccts:
                    other_vars['unmatched_code'] = True
            except Exception:
                #Not authorized to use accounts_list
                pass

        send_allocation_admin_email(
            allocation_obj,
            'New Allocation Request',
            'email/new_allocation_request.txt',
            domain_url=get_domain_url(self.request),
            url_path=reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}),
            other_vars=other_vars,
        )
        return super().form_valid(form)

    def get_success_url(self):
        msg = 'Allocation requested. It will be available once it is approved.'
        messages.success(self.request, msg)
        return reverse('project-detail', kwargs={'pk': self.kwargs.get('project_pk')})


class AllocationAddUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_add_users.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.user_can_manage_allocation(self.request.user):
            return True
        err = 'You do not have permission to add users to the allocation.'
        messages.error(self.request, err)
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        err = None
        if allocation_obj.is_locked and not self.request.user.is_superuser:
            err = 'You cannot modify this allocation because it is locked! Contact support for details.'
        elif 'Storage' in allocation_obj.get_parent_resource.resource_type.name:
            err = 'You cannot edit the user list for a storage allocation.'
        elif allocation_obj.status.name not in PENDING_ACTIVE_ALLOCATION_STATUSES:
            err = f'You cannot add users to an allocation with status {allocation_obj.status.name}.'
        if err:
            messages.error(request, err)
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            )
        return super().dispatch(request, *args, **kwargs)

    def get_non_project_users_to_add(self, allocation_obj, return_all=False, limit=10):
        allocation_user_ids = list(
            allocation_obj.allocationuser_set.filter(status__name="Active")
            .values_list('user__id', flat=True)
        )
        project_user_ids = list(
            allocation_obj.project.projectuser_set.filter(status__name='Active')
            .values_list('user__id', flat=True)
        )
        user_exclude_list = allocation_user_ids + project_user_ids
        non_project_users_to_add = get_user_model().objects.exclude(id__in=user_exclude_list)
        if return_all:
            return non_project_users_to_add
        return non_project_users_to_add.values('username', 'first_name', 'last_name', 'email')[0:limit]

    def get_users_to_add(self, allocation_obj):
        active_users_in_project = list(allocation_obj.project.projectuser_set.filter(
            status__name='Active').values_list('user__username', flat=True)
        )
        allocation_users = allocation_obj.allocationuser_set.exclude(status__name='Removed')
        users_already_in_allocation = list(
            allocation_users.values_list('user__username', flat=True)
        )

        missing_users = list(
            set(active_users_in_project) - set(users_already_in_allocation)
        )
        missing_users = (
            get_user_model().objects.filter(username__in=missing_users)
            .exclude(pk=allocation_obj.project.pi.pk)
        )
        users_to_add = missing_users.values('username', 'first_name', 'last_name', 'email')
        return users_to_add

    def non_project_users_search(self, allocation_obj, search_term):
        user_list = []
        search_term = requests.utils.unquote(search_term)
        user_search = search_term.split(" ") if " " in search_term else search_term.splitlines()
        for username in user_search:
            like_filter = (
                Q(username__icontains=username)
                or Q(first_name__icontains=username)
                or Q(last_name__icontains=username)
                or Q(title_icontains=username)
            )

            non_project_users = (
                self.get_non_project_users_to_add(allocation_obj, return_all=True)
                .filter(like_filter)
                .exclude(project=allocation_obj.project)
                .values('username', 'first_name', 'last_name', 'email')
            )
            user_list += non_project_users

        return user_list

    def search_non_project_users(self, allocation_obj, search_term, request):
        found_non_project_users = self.non_project_users_search(allocation_obj, search_term)
        context = {'allocation': allocation_obj}
        if len(found_non_project_users) > 0:
            formset = formset_factory(AllocationAddNonProjectUserForm, max_num=len(found_non_project_users))
            formset = formset(initial=found_non_project_users, prefix='nonuserform')
            context = {'formset_non_users': formset, 'allocation': allocation_obj, 'matches': found_non_project_users, 'search_term': search_term}
        form_html = render_to_string('allocation/allocation_add_users_search_result.html', context, request=request)
        return JsonResponse({'status': 'success', 'data': form_html})

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        users_to_add = self.get_users_to_add(allocation_obj)
        non_project_users_to_add = self.get_non_project_users_to_add(allocation_obj)
        context = {}
        search_request = request.GET.get('search', None)
        if search_request is not None:
            return self.search_non_project_users(allocation_obj, search_request, request)
        if users_to_add:
            formset = formset_factory(AllocationAddUserForm, max_num=len(users_to_add))
            formset = formset(initial=users_to_add, prefix='userform')
            context['formset'] = formset
        if non_project_users_to_add:
            context['user_search_form'] = UserSearchForm()
        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        users_to_add = self.get_users_to_add(allocation_obj)
        non_project_users_to_add = self.get_non_project_users_to_add(allocation_obj)
        formset_initial = users_to_add
        prefix = 'userform'
        formset = formset_factory(AllocationAddUserForm, max_num=len(users_to_add))
        if 'nonuserform-TOTAL_FORMS' in request.POST.keys():
            search_term = request.GET.get('search')
            formset_initial = self.non_project_users_search(allocation_obj, search_term)
            formset = formset_factory(AllocationAddNonProjectUserForm, max_num=len(non_project_users_to_add))
            prefix = 'nonuserform'

        formset = formset(request.POST, initial=formset_initial, prefix=prefix)
        users_added_count = 0

        if formset.is_valid():
            user_active_status = AllocationUserStatusChoice.objects.get(name='Active')
            cleaned_form = [form.cleaned_data for form in formset]
            selected_cleaned_form = [form for form in cleaned_form if form['selected']]
            for form_data in selected_cleaned_form:

                user_obj = get_user_model().objects.get(
                    username=form_data.get('username')
                )

                account = allocation_obj.project.title
                cluster = allocation_obj.get_cluster.get_attribute('slurm_cluster')
                logger.warning(f"Username {form_data.get('username')} cluster {cluster}")
                username = form_data.get('username')
                try:
                    allocation_user_add_on_slurm.send(
                        sender=self.__class__,
                        username=username,
                        account=account,
                        cluster=cluster
                    )
                except Exception as e:
                    logger.exception(f"signal processes for addition of user {username} to allocation {allocation_obj.pk} ({allocation_obj.project.title} {allocation_obj.get_parent_resource.name}) failed: {e}")
                    err = f"addition of user {username} to allocation {allocation_obj.pk} ({allocation_obj.project.title} {allocation_obj.get_parent_resource.name}) failed: {e}"
                    messages.error(request, err)
                    continue
                allocation_user_obj, _ = (
                    allocation_obj.allocationuser_set.update_or_create(
                        user=user_obj, defaults={'status': user_active_status}
                    )
                )
                allocation_activate_user.send(
                    sender=self.__class__,
                    username=username,
                    allocation_user_pk=allocation_user_obj.pk
                )
                users_added_count += 1

            user_plural = 'user' if users_added_count == 1 else 'users'
            msg = f'Added {users_added_count} {user_plural} to allocation.'
            messages.success(request, msg)
        else:
            for error in formset.errors:
                logger.error(error)
                messages.error(request, error)
        return HttpResponseRedirect(reverse('allocation-add-users', kwargs={'pk': pk}))


class AllocationEditUserView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_edit_user.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.user_can_manage_allocation(self.request.user):
            return True
        err = 'You do not have permission to edit users on the allocation.'
        messages.error(self.request, err)
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        allocationuser_obj = get_object_or_404(AllocationUser, pk=self.kwargs.get('userid'))
        err = None
        if allocation_obj.is_locked and not self.request.user.is_superuser:
            err = 'You cannot edit this allocation because it is locked! Contact support for details.'
        elif 'Storage' in allocation_obj.get_parent_resource.resource_type.name:
            err = 'You cannot edit storage allocation users.'
        elif allocation_obj.status.name not in PENDING_ACTIVE_ALLOCATION_STATUSES:
            err = f'You cannot edit users on an allocation with status {allocation_obj.status.name}.'
        elif allocationuser_obj.status.name != 'Active':
            err = f'You can only edit the attributes of active allocation users.'
        if err:
            messages.error(request, err)
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        allocationuser_obj = get_object_or_404(AllocationUser, pk=self.kwargs.get('userid'))
        initial_data = {'allocationuser_pk': allocationuser_obj.pk, 'value': allocationuser_obj.get_slurm_spec_value('RawShares')}
        form = AllocationUserAttributeUpdateForm(initial=initial_data)

        context = {
            'allocation': allocation_obj,
            'allocationuser': allocationuser_obj,
            'userid': allocationuser_obj.pk,
            'formset': form
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        allocationuser_obj = get_object_or_404(AllocationUser, pk=self.kwargs.get('userid'))

        initial_data = {'allocationuser_pk': allocationuser_obj.pk, 'value': allocationuser_obj.get_slurm_spec_value('RawShares')}
        post_data = request.POST.copy()
        post_data['allocationuser_pk'] = allocationuser_obj.pk

        form = AllocationUserAttributeUpdateForm(post_data, initial=initial_data)

        if form.is_valid():
            form_data = form.cleaned_data
            if str(form_data['value']) == str(initial_data.get('value')):
                messages.error(request, "Form not modified")
                return HttpResponseRedirect(
                    reverse('allocation-edit-user', kwargs=self.kwargs)
                )

            # TODO: Update fairshare
            try:
                account = allocation_obj.project.title
                allocation_user_attribute_edit.send(
                    sender=self.__class__, user=allocationuser_obj, account=account, raw_share=form_data['value']
                )
            except Exception as e:
                logger.exception(f'error encountered while trying to update allocationuser {allocation_obj}:{allocationuser_obj} rawshare: {e}')
                messages.error(request, f'error encountered while trying to update allocationuser {allocation_obj}:{allocationuser_obj} rawshare: {e}')
                return HttpResponseRedirect(
                    reverse('allocation-edit-user', kwargs=self.kwargs)
                )
            allocationuser_obj.update_slurm_spec_value('RawShares', form_data['value'])
            messages.success(request, 'rawshare updated!')
        else:
            for error in form.errors:
                messages.error(request, error)
        return HttpResponseRedirect(
            # TODO: Redirect accordingly
            reverse('allocation-edit-user', kwargs=self.kwargs)
        )

class AllocationRemoveUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_remove_users.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.user_can_manage_allocation(self.request.user):
            return True
        err = 'You do not have permission to remove users from allocation.'
        messages.error(self.request, err)
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        err = None
        if allocation_obj.is_locked and not self.request.user.is_superuser:
            err = 'You cannot modify this allocation because it is locked! Contact support for details.'
        elif 'Storage' in allocation_obj.get_parent_resource.resource_type.name:
            err = 'You cannot edit storage allocation users.'
        elif allocation_obj.status.name not in PENDING_ACTIVE_ALLOCATION_STATUSES:
            err = f'You cannot remove users from an allocation with status {allocation_obj.status.name}.'
        if err:
            messages.error(request, err)
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            )
        return super().dispatch(request, *args, **kwargs)

    def get_users_to_remove(self, allocation_obj):
        users_to_remove = list(
            allocation_obj.allocationuser_set.exclude(
                status__name__in=['Removed', 'Error']
            ).values_list('user__username', flat=True)
        )
        users_to_remove = (
            get_user_model().objects.filter(username__in=users_to_remove)
            .exclude(pk__in=[allocation_obj.project.pi.pk, self.request.user.pk])
            .values('username', 'first_name', 'last_name', 'email')
        )
        return users_to_remove

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        users_to_remove = self.get_users_to_remove(allocation_obj)
        context = {}

        if users_to_remove:
            formset = formset_factory(
                AllocationRemoveUserForm, max_num=len(users_to_remove)
            )
            formset = formset(initial=users_to_remove, prefix='userform')
            context['formset'] = formset

        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        users_to_remove = self.get_users_to_remove(allocation_obj)

        formset = formset_factory(
            AllocationRemoveUserForm, max_num=len(users_to_remove)
        )
        formset = formset(request.POST, initial=users_to_remove, prefix='userform')

        remove_users_count = 0
        if formset.is_valid():
            removed_allocuser_status = AllocationUserStatusChoice.objects.get(
                name='Removed'
            )
            cleaned_forms = [form.cleaned_data for form in formset]
            selected_cleaned_forms = [
                form for form in cleaned_forms if form['selected']
            ]
            for user_form_data in selected_cleaned_forms:
                user_obj = get_user_model().objects.get(
                    username=user_form_data.get('username')
                )
                if allocation_obj.project.pi == user_obj:
                    continue

                allocation_user_obj = allocation_obj.allocationuser_set.get(
                    user=user_obj
                )

                try:
                    account = allocation_user_obj.allocation.project.title
                    allocation_user_remove_on_slurm.send(self.__class__, account=account, username=user_obj.username)
                    allocation_user_obj.status = removed_allocuser_status
                    allocation_user_obj.save()
                    allocation_remove_user.send(
                        sender=self.__class__, allocation_user_pk=allocation_user_obj.pk
                    )
                    remove_users_count += 1
                except SlurmError as e:
                    error_message = f"You can't remove this AllocationUser ({user_form_data.get('username')}) while they are running a job using this account. Try again after the job has been completed or cancelled."
                    messages.error(request, error_message)

            user_plural = 'user' if remove_users_count == 1 else 'users'
            msg = f'Removed {remove_users_count} {user_plural} from allocation.'
            messages.success(request, msg)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

class AllocationAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationAttribute
    form_class = AllocationAttributeCreateForm
    template_name = 'allocation/allocation_allocationattribute_create.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True
        err = 'You do not have permission to add allocation attributes.'
        messages.error(self.request, err)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        context['allocation'] = allocation_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        initial['allocation'] = allocation_obj
        return initial

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        form = super().get_form(form_class)
        form.fields['allocation'].widget = forms.HiddenInput()
        return form

    def get_success_url(self):
        return reverse('allocation-detail', kwargs={'pk': self.kwargs.get('pk')})

class AllocationAttributeEditView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationAttribute
    formset_class = AllocationAttributeChangeForm
    template_name = 'allocation/allocation_allocationattribute_edit.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.user_can_manage_allocation(self.request.user):
            return True
        err = 'You do not have permission to edit allocation attributes.'
        messages.error(self.request, err)
        return False

    def get_allocation_attrs_to_change(self, allocation_obj):
        attributes_to_change = allocation_obj.allocationattribute_set.filter(
        #    allocation_attribute_type__is_changeable=True
        )
        attributes_to_change = [
            {
                'pk': attribute.pk,
                'name': attribute.allocation_attribute_type.name,
                'value': attribute.value,
            }
            for attribute in attributes_to_change
        ]
        return attributes_to_change

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        attrs_to_change = self.get_allocation_attrs_to_change(allocation_obj)
        context = {}

        form = AllocationChangeForm(**self.get_form_kwargs())
        context['form'] = form

        if attrs_to_change:
            formset = formset_factory(self.formset_class, max_num=len(attrs_to_change))
            formset = formset(initial=attrs_to_change, prefix='attributeform')
            context['formset'] = formset

        if allocation_obj.get_parent_resource:
            resource_used = allocation_obj.get_parent_resource.used_percentage
        else:
            resource_used = None
        context['allocation'] = allocation_obj
        context['attributes'] = attrs_to_change
        context['used_percentage'] = resource_used
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        form = AllocationChangeForm(**self.get_form_kwargs())
        attrs_to_change = self.get_allocation_attrs_to_change(allocation_obj)

        # find errors
        validation_errors = []

        if not form.is_valid():
            validation_errors.extend(list(form.errors))

        if attrs_to_change:
            formset = formset_factory(self.formset_class, max_num=len(attrs_to_change))
            formset = formset(
                request.POST, initial=attrs_to_change, prefix='attributeform'
            )
            if not formset.is_valid():
                attribute_errors = ''
                for error in formset.errors:
                    if error:
                        attribute_errors += error.get('__all__')
                validation_errors.append(attribute_errors)

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return HttpResponseRedirect(reverse('allocation-attribute-edit', kwargs={'pk': pk}))

        if attrs_to_change:
            for entry in formset:
                formset_data = entry.cleaned_data
                new_value = formset_data.get('new_value')
                if new_value != '':
                    allocation_attribute = AllocationAttribute.objects.get(
                        pk=formset_data.get('pk')
                    )
                    allocation_attribute.value = new_value
                    allocation_attribute.clean()
                    allocation_attribute.save()
        messages.success(request, 'Allocation attributes changed.')
        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))

class AllocationAttributeDeleteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_allocationattribute_delete.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.user_can_manage_allocation(self.request.user):
            return True
        err = 'You do not have permission to delete allocation attributes.'
        messages.error(self.request, err)
        return False

    def get_allocation_attributes_to_delete(self, allocation_obj):
        allocation_attributes_to_delete = AllocationAttribute.objects.filter(
            allocation=allocation_obj
        )
        allocation_attributes_to_delete = [
            {
                'pk': attribute.pk,
                'name': attribute.allocation_attribute_type.name,
                'value': attribute.value,
            }
            for attribute in allocation_attributes_to_delete
        ]
        return allocation_attributes_to_delete

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        attrs_to_delete = self.get_allocation_attributes_to_delete(allocation_obj)
        context = {}

        if attrs_to_delete:
            formset = formset_factory(
                AllocationAttributeDeleteForm, max_num=len(attrs_to_delete)
            )
            formset = formset(initial=attrs_to_delete, prefix='attributeform')
            context['formset'] = formset
        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        attrs_to_delete = self.get_allocation_attributes_to_delete(allocation_obj)

        formset = formset_factory(
            AllocationAttributeDeleteForm, max_num=len(attrs_to_delete)
        )
        formset = formset(request.POST, initial=attrs_to_delete, prefix='attributeform')

        attributes_deleted_count = 0
        if formset.is_valid():
            cleaned_forms = [form.cleaned_data for form in formset]
            selected_cleaned_forms = [
                form for form in cleaned_forms if form['selected']
            ]
            for form_data in selected_cleaned_forms:
                allocation_attribute = AllocationAttribute.objects.get(
                    pk=form_data['pk']
                )
                allocation_attribute.delete()
                attributes_deleted_count += 1

            msg = f'Deleted {attributes_deleted_count} attributes from allocation.'
            messages.success(request, msg)
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationUserAttributesEditView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Allocation
    template_name = 'allocation/allocation_user_attributes_edit.html'
    context_object_name = 'allocation'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.user_can_manage_allocation(self.request.user):
            return True
        elif 'Storage' in allocation_obj.get_parent_resource.resource_type.name:
            messages.error(
                self.request, 'You cannot edit storage allocation user attributes.'
            )
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            )
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        return allocation_obj.has_perm(self.request.user, AllocationPermission.MANAGER)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        inactive_status = AllocationUserStatusChoice.objects.get(name='Removed')
        allocation_users = allocation_obj.allocationuser_set.exclude(status=inactive_status).order_by('user__username')

        context['user_can_manage_allocation'] = allocation_obj.user_can_manage_allocation(self.request.user)
        context['allocation_users'] = allocation_users
        context['allocation'] = allocation_obj
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        if context['allocation'].project.status.name in ['Archived']:
            return HttpResponseForbidden(
                'This is an allocation from an archived project! You cannot make any changes.'
            )
        elif context['allocation'].status.name in ['Pending Deactivation', 'Inactive', 'Denied', 'Merged']:
            return HttpResponseForbidden(f"This allocation is {context['allocation'].status.name.lower()}! You cannot make any changes.")
        EditRawShareFormSet = formset_factory(AllocationUserAttributeUpdateForm, extra=0)
        allocation_users = context['allocation_users']
        edit_raw_share_form_set_initial_data = [
            {
                'allocationuser_pk': allocation_user.pk,
                'value': allocation_user.get_slurm_spec_value('RawShares')
            }
            for allocation_user in allocation_users
        ]
        context['formset'] = EditRawShareFormSet(initial=edit_raw_share_form_set_initial_data)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation = get_object_or_404(Allocation, pk=pk)
        if not self.request.user.is_superuser:
            err = 'You do not have permission to update the allocation'
            messages.error(request, err)
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))
        EditRawShareFormSet = formset_factory(AllocationUserAttributeUpdateForm, extra=0)
        formset = EditRawShareFormSet(request.POST)
        error_found = False
        context = self.get_context_data()
        error_messages = []
        if formset.is_valid():
            allocation_users = context['allocation_users']
            user_raw_shares = {
                str(form.cleaned_data.get('allocationuser_pk')): form.cleaned_data.get('value')
                for form in formset.forms
            }
            for allocation_user in allocation_users:
                user = allocation_user.user.username
                account = allocation.project.title
                allocationuser_new_rawshare_value = user_raw_shares.get(str(allocation_user.pk), None)
                if allocationuser_new_rawshare_value is not None:
                    allocationuser_current_rawshare_value = allocation_user.get_slurm_spec_value('RawShares')
                    if str(allocationuser_current_rawshare_value) != str(allocationuser_new_rawshare_value): #Ignore unchanged values
                        try:
                            allocation_user_attribute_edit.send(
                                sender=self.__class__,
                                user=user,
                                account=account,
                                raw_share=allocationuser_new_rawshare_value
                            )
                        except Exception as e:
                            err = f"Failed to update Rawshare on slurm for user {user} account {account} with value {allocationuser_new_rawshare_value}: {str(e)}"
                            logger.exception(err)
                            error_messages.append(err)
                            error_found = True
                            continue
                        rawshare_updated = allocation_user.update_slurm_spec_value('RawShares', allocationuser_new_rawshare_value)
                        if rawshare_updated != True:
                            error_messages.append('value updated on slurm for user {user} with value {allocationuser_new_rawshare_value} but error encountered while changing value on coldfront.')
                            error_found = True
                            continue
                        msg = f'User Attributes for {allocation_user.user} in allocation {allocation.pk} ({allocation}) successfully updated from {allocationuser_current_rawshare_value} to {allocationuser_new_rawshare_value}'
                        logger.info(msg)
                        messages.success(request, msg)
        else:
            for error in formset.errors:
                messages.error(request, error)
            error_found = True
        context['formset'] = formset
        if error_messages:
            for err in error_messages:
                messages.error(request, err)
        messages.success(request, "User Attributes updated!")
        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationNoteCreateView(NoteCreateView):
    model = AllocationUserNote
    fields = '__all__'
    object_model = Allocation
    form_obj = 'allocation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_page'] = 'allocation-detail'
        context['object_title'] = f'Allocation {context["object"]}'
        return context

    def get_success_url(self):
        return reverse('allocation-detail', kwargs={'pk': self.kwargs.get('pk')})


class AllocationNoteUpdateView(NoteUpdateView):
    model = AllocationUserNote

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_object'] = self.object.allocation
        context['object_detail_link'] = 'allocation-detail'
        return context

    def get_success_url(self):
        pk = self.object.allocation.pk
        return reverse_lazy('allocation-detail', kwargs={'pk': pk})


class AllocationRequestListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_request_list.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        review_perm = 'allocation.can_review_allocation_requests'
        if self.request.user.is_superuser or self.request.user.has_perm(review_perm):
            return True

        err = 'You do not have permission to review allocation requests.'
        messages.error(self.request, err)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_list = Allocation.objects.filter(
            status__name__in=PENDING_ALLOCATION_STATUSES
        )
        AllocationFormSet = formset_factory(
            AllocationUpdateForm, max_num=len(allocation_list),
        )
        formset = AllocationFormSet(
            initial=[
                {
                    "project": a.project,
                    "pk": a.pk,
                    "created": a.created,
                    "get_parent_resource": a.get_parent_resource,
                    "resource": a.get_parent_resource,
                    "status": a.status,
                }
                for a in allocation_list
            ],
        )
        context['formset'] = formset
        context['allocation_status_active'] = AllocationStatusChoice.objects.get(name='Active')
        context['allocation_list'] = allocation_list
        context['PROJECT_ENABLE_PROJECT_REVIEW'] = PROJECT_ENABLE_PROJECT_REVIEW
        context['ALLOCATION_DEFAULT_ALLOCATION_LENGTH'] = ALLOCATION_DEFAULT_ALLOCATION_LENGTH
        return context

    def post(self, request, *args, **kwargs):
        post_data = request.POST
        pk = post_data['pk']
        chosen_resource_id = next(v for k, v in post_data.items() if 'resource' in k.lower())
        if not chosen_resource_id:
            err = 'You must select a resource volume.'
            messages.error(request, err)
            return HttpResponseRedirect(reverse('allocation-request-list'))

        allocation_obj = get_object_or_404(Allocation, pk=pk)
        active_status = AllocationStatusChoice.objects.get(name='Active')

        allocation_obj.status = active_status
        chosen_resource = Resource.objects.get(pk=chosen_resource_id)
        if 'Tier ' in allocation_obj.get_resources_as_string:
            # remove current resource from resources
            allocation_obj.resources.clear()
            # add form_data.get(resource)
            allocation_obj.resources.add(chosen_resource)
        allocation_obj.save()

        messages.success(request, 'Allocation Activated.')

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationRenewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_renew.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.has_perm(self.request.user, AllocationPermission.MANAGER):
            return True
        messages.error(self.request, 'You do not have permission to renew allocation.')
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        err = None
        if not ALLOCATION_ENABLE_ALLOCATION_RENEWAL:
            err = 'Allocation renewal is disabled. Request a new allocation to this resource if you want to continue using it after the active until date.'
        elif allocation_obj.status.name not in ['Active']:
            err = f'You cannot renew an allocation with status {allocation_obj.status.name}.'
        elif allocation_obj.expires_in and allocation_obj.expires_in > 60:
            err = 'It is too soon to review your allocation.'

        if err:
            messages.error(request, err)
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            )

        if allocation_obj.project.needs_review:
            err = 'You cannot renew your allocation because you have to review your project first.'
            messages.error(request, err)
            return HttpResponseRedirect(
                reverse('project-detail', kwargs={'pk': allocation_obj.project.pk})
            )

        return super().dispatch(request, *args, **kwargs)

    def get_users_in_allocation(self, allocation_obj):
        users_in_allocation = (
            allocation_obj.allocationuser_set.exclude(status__name__in=['Removed'])
            .exclude(user__pk__in=[allocation_obj.project.pi.pk, self.request.user.pk])
            .order_by('user__username')
        )
        users = [
            {
                'username': allocation_user.user.username,
                'first_name': allocation_user.user.first_name,
                'last_name': allocation_user.user.last_name,
                'email': allocation_user.user.email,
            }
            for allocation_user in users_in_allocation
        ]
        return users

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        users_in_allocation = self.get_users_in_allocation(allocation_obj)
        context = {}

        if users_in_allocation:
            formset = formset_factory(
                AllocationReviewUserForm, max_num=len(users_in_allocation)
            )
            formset = formset(initial=users_in_allocation, prefix='userform')
            context['formset'] = formset

            context['resource_eula'] = {}
            if allocation_obj.get_parent_resource.resourceattribute_set.filter(
                resource_attribute_type__name='eula'
            ).exists():
                value = allocation_obj.get_parent_resource.resourceattribute_set.get(
                    resource_attribute_type__name='eula'
                ).value
                context['resource_eula'].update({'eula': value})

        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        users_in_allocation = self.get_users_in_allocation(allocation_obj)

        formset = formset_factory(
            AllocationReviewUserForm, max_num=len(users_in_allocation)
        )
        formset = formset(request.POST, initial=users_in_allocation, prefix='userform')

        renewal_requested_alloc_status = AllocationStatusChoice.objects.get(
            name='Renewal Requested'
        )
        removed_allocuser_status = AllocationUserStatusChoice.objects.get(
            name='Removed'
        )
        remove_projuser_status = ProjectUserStatusChoice.objects.get(name='Removed')

        allocation_obj.status = renewal_requested_alloc_status
        allocation_obj.save()
        if not formset.is_valid():
            for error in formset.errors:
                messages.error(request, error)
        elif not users_in_allocation or formset.is_valid():
            if users_in_allocation:
                for form in formset:
                    user_form_data = form.cleaned_data
                    user_obj = get_user_model().objects.get(
                        username=user_form_data.get('username')
                    )
                    user_status = user_form_data.get('user_status')

                    update_allocationuser_status_list = []

                    if user_status == 'keep_in_project_only':
                        allocation_user_obj = allocation_obj.allocationuser_set.get(
                            user=user_obj
                        )
                        update_allocationuser_status_list.append(allocation_user_obj)

                    elif user_status == 'remove_from_project':
                        for active_alloc in allocation_obj.project.allocation_set.filter(
                            status__name__in=PENDING_ACTIVE_ALLOCATION_STATUSES
                        ):
                            alloc_user_obj = active_alloc.allocationuser_set.get(
                                user=user_obj
                            )
                            update_allocationuser_status_list.append(alloc_user_obj)
                        project_user_obj = allocation_obj.project.projectuser_set.get(
                            user=user_obj
                        )
                        project_user_obj.status = remove_projuser_status
                        project_user_obj.save()

                    for alloc_user_obj in update_allocationuser_status_list:
                        alloc_user_obj.status = removed_allocuser_status
                        alloc_user_obj.save()
                        allocation_remove_user.send(
                            sender=self.__class__, allocation_user_pk=alloc_user_obj.pk
                        )

            send_allocation_admin_email(
                allocation_obj,
                'Allocation Renewed',
                'email/allocation_renewed.txt',
                domain_url=get_domain_url(self.request),
            )

            messages.success(request, 'Allocation renewed successfully')
        return HttpResponseRedirect(
            reverse('project-detail', kwargs={'pk': allocation_obj.project.pk})
        )


class AllocationInvoiceListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Allocation
    template_name = 'allocation/allocation_invoice_list.html'
    context_object_name = 'allocation_list'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        invoice_perm = self.request.user.has_perm('allocation.can_manage_invoice')
        if self.request.user.is_superuser or invoice_perm:
            return True
        messages.error(self.request, 'You do not have permission to manage invoices.')
        return False

    def get_queryset(self):
        # allocations = Allocation.objects.filter(
        #     status__name__in=['Paid', 'Payment Pending', 'Payment Requested' ])
        allocations = Allocation.objects.filter(
            status__name__in=['Active', 'Payment Pending']
        )
        return allocations


class AllocationInvoicePaidView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Allocation
    template_name = 'allocation/allocation_invoice_paid_list.html'
    context_object_name = 'allocation_list'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        invoice_perm = self.request.user.has_perm('allocation.can_manage_invoice')
        if self.request.user.is_superuser or invoice_perm:
            return True
        messages.error(self.request, 'You do not have permission to manage invoices.')
        return False

    def get_queryset(self):
        # allocations = Allocation.objects.filter(
        #     status__name__in=['Paid', 'Payment Pending', 'Payment Requested' ])
        allocations = Allocation.objects.filter(status__name__in=['Paid'])
        return allocations


# this is the view class thats rendering allocation_invoice_detail.
class AllocationInvoiceDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Allocation
    template_name = 'allocation/allocation_invoice_detail.html'
    context_object_name = 'allocation'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        invoice_perm = self.request.user.has_perm('allocation.can_manage_invoice')
        if self.request.user.is_superuser or invoice_perm:
            return True
        messages.error(self.request, 'You do not have permission to view invoices.')
        return False

    def get_context_data(self, **kwargs):
        """Create all the variables for allocation_invoice_detail.html"""
        context = super().get_context_data(**kwargs)
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        allocation_users = (
            allocation_obj.allocationuser_set.exclude(status__name__in=['Removed'])
            .exclude(usage_bytes__isnull=True).order_by('user__username')
        )
        alloc_attr_set = allocation_obj.get_attribute_set(self.request.user)

        attributes_with_usage = [
            a for a in alloc_attr_set if hasattr(a, 'allocationattributeusage')
        ]
        attributes = list(alloc_attr_set)

        guage_data = []
        invalid_attributes = []
        for attribute in attributes_with_usage:
            try:
                guage_data.append(
                    generate_guauge_data_from_usage(
                        attribute.allocation_attribute_type.name,
                        float(attribute.value),
                        float(attribute.allocationattributeusage.value),
                    )
                )
            except ValueError:
                logger.error(
                    "Allocation attribute '%s' is not an int but has a usage",
                    attribute.allocation_attribute_type.name,
                )
                invalid_attributes.append(attribute)

        for a in invalid_attributes:
            attributes_with_usage.remove(a)

        context['guage_data'] = guage_data
        context['attributes_with_usage'] = attributes_with_usage
        context['attributes'] = attributes

        # Can the user update the project?
        project_update_perm = allocation_obj.project.has_perm(
            self.request.user, ProjectPermission.DATA_MANAGER
        )
        context['user_can_manage_allocation'] = allocation_obj.user_can_manage_allocation(self.request.user)
        context['allocation_users'] = allocation_users
        context['note_update_link'] = 'allocation-note-update'

        context['notes'] = self.return_visible_notes(allocation_obj)
        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
        return context

    def return_visible_notes(self, allocation_obj):
        notes = allocation_obj.allocationusernote_set.all()
        if not self.request.user.is_superuser:
            notes = notes.filter(is_private=False)
        return notes

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        initial_data = {'status': allocation_obj.status}

        form = AllocationInvoiceUpdateForm(initial=initial_data)

        context = self.get_context_data()
        context['form'] = form
        context['allocation'] = allocation_obj

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        initial_data = {'status': allocation_obj.status}
        form = AllocationInvoiceUpdateForm(request.POST, initial=initial_data)

        if form.is_valid():
            form_data = form.cleaned_data
            allocation_obj.status = form_data.get('status')
            allocation_obj.save()
            messages.success(request, 'Allocation updated!')
        else:
            for error in form.errors:
                messages.error(request, error)
        return HttpResponseRedirect(
            reverse('allocation-invoice-detail', kwargs={'pk': pk})
        )


class AllocationInvoiceNoteCreateView(NoteCreateView):
    model = AllocationUserNote
    fields = ('is_private', 'note', 'author', 'allocation')
    object_model = Allocation
    form_obj = 'allocation'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        invoice_perm = self.request.user.has_perm('allocation.can_manage_invoice')
        if invoice_perm:
            return True
        return super().test_func()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_page'] = 'allocation-invoice-detail'
        context['object_title'] = f'Allocation {context["object"]}'
        return context

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        obj = form.save(commit=False)
        obj.author = self.request.user
        obj.allocation = allocation_obj
        obj.save()
        allocation_obj.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'allocation-invoice-detail', kwargs={'pk': self.kwargs.get('pk')}
        )


class AllocationInvoiceNoteUpdateView(NoteUpdateView):
    model = AllocationUserNote
    template_name = 'allocation/allocation_update_invoice_note.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        invoice_perm = self.request.user.has_perm('allocation.can_manage_invoice')
        if self.request.user.is_superuser or invoice_perm:
            return True
        messages.error(self.request, 'You do not have permission to manage invoices.')
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_object'] = self.object.allocation
        context['object_detail_link'] = 'allocation-detail'
        return context

    def get_success_url(self):
        return reverse_lazy(
            'allocation-invoice-detail', kwargs={'pk': self.object.allocation.pk}
        )


class AllocationDeleteInvoiceNoteView(
    LoginRequiredMixin, UserPassesTestMixin, TemplateView
):
    template_name = 'allocation/allocation_delete_invoice_note.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        invoice_perm = self.request.user.has_perm('allocation.can_manage_invoice')
        if self.request.user.is_superuser or invoice_perm:
            return True
        messages.error(self.request, 'You do not have permission to manage invoices.')
        return False

    def get_notes_to_delete(self, allocation_obj):
        notes_to_delete = [
            {
                'pk': note.pk,
                'note': note.note,
                'author': note.author.username,
            }
            for note in allocation_obj.allocationusernote_set.all()
        ]
        return notes_to_delete

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        notes_to_delete = self.get_notes_to_delete(allocation_obj)
        context = {}
        if notes_to_delete:
            formset = formset_factory(
                AllocationInvoiceNoteDeleteForm, max_num=len(notes_to_delete)
            )
            formset = formset(initial=notes_to_delete, prefix='noteform')
            context['formset'] = formset
        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        notes_to_delete = self.get_notes_to_delete(allocation_obj)

        formset = formset_factory(
            AllocationInvoiceNoteDeleteForm, max_num=len(notes_to_delete)
        )
        formset = formset(request.POST, initial=notes_to_delete, prefix='noteform')

        if formset.is_valid():
            cleaned_form = [form.cleaned_data for form in formset]
            selected_cleaned_form = [form for form in cleaned_form if form['selected']]
            for note_form_data in selected_cleaned_form:
                note_obj = AllocationUserNote.objects.get(pk=note_form_data.get('pk'))
                note_obj.delete()
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(
            reverse_lazy('allocation-invoice-detail', kwargs={'pk': allocation_obj.pk})
        )


class AllocationAccountCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationAccount
    template_name = 'allocation/allocation_allocationaccount_create.html'
    form_class = AllocationAccountForm

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if not ALLOCATION_ACCOUNT_ENABLED:
            return False
        if self.request.user.is_superuser:
            return True
        if self.request.user.userprofile.is_pi:
            return True
        err = 'You do not have permission to add allocation attributes.'
        messages.error(self.request, err)
        return False

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        return response

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        if self.request.is_ajax():
            obj_data = {'pk': self.object.pk}
            return JsonResponse(obj_data)
        return response

    def get_success_url(self):
        return reverse_lazy('allocation-account-list')


data = {
    'company': 'FAS Research Computing',
    'address': '38 Oxford St',
    'city': 'Cambridge',
    'state': 'MA',
    'zipcode': '02138',
    'website': 'billing@rc.fas.harvard.edu',
}


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('ISO-8859-1')), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


class ViewPDF(View):
    def get(self, request, *args, **kwargs):
        print('line magic 1773', kwargs)
        pdf = render_to_pdf('allocation/pdf_template.html', data)
        return HttpResponse(pdf, content_type='application/pdf')


# Automatically downloads to PDF file
class DownloadPDF(View):
    def get(self, request, *args, **kwargs):
        pdf = render_to_pdf('allocation/pdf_template.html', data)
        response = HttpResponse(pdf, content_type='allocation/pdf')
        filename = 'Invoice_%s.pdf' % ('12341231')
        content = f"attachment; filename='{filename}'"
        response['Content-Disposition'] = content
        return response

    def index(self, request):
        context = {}
        return render(request, 'app/index.html', context)

    def get_queryset(self):
        return AllocationAccount.objects.filter(user=self.request.user)


class AllocationAccountListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = AllocationAccount
    template_name = 'allocation/allocation_account_list.html'
    context_object_name = 'allocationaccount_list'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if not ALLOCATION_ACCOUNT_ENABLED:
            return False
        if self.request.user.is_superuser:
            return True
        if self.request.user.userprofile.is_pi:
            return True

        messages.error(self.request, 'You do not have permission to manage invoices.')
        return False

    def get_queryset(self):
        return AllocationAccount.objects.filter(user=self.request.user)


class AllocationChangeDetailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    formset_class = AllocationAttributeUpdateForm
    template_name = 'allocation/allocation_change_detail.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        if self.request.user.has_perm('allocation.can_view_all_allocations'):
            return True
        pk = self.kwargs.get('pk')
        allocation_change_obj = get_object_or_404(AllocationChangeRequest, pk=pk)
        manager_perm = AllocationPermission.MANAGER
        if allocation_change_obj.allocation.has_perm(self.request.user, manager_perm):
            return True
        return False

    def get_allocation_attrs_to_change(self, allocation_change_obj):
        attributes_to_change = (
            allocation_change_obj.allocationattributechangerequest_set.all()
        )
        attributes_to_change = [
            {
                'change_pk': attr_change.pk,
                'attribute_pk': attr_change.allocation_attribute.pk,
                'name': attr_change.allocation_attribute.allocation_attribute_type.name,
                'value': attr_change.allocation_attribute.value,
                'new_value': attr_change.new_value,
            }
            for attr_change in attributes_to_change
        ]
        return attributes_to_change

    def get_context_data(self, **kwargs):
        context = {}
        pk = self.kwargs.get('pk')
        allocation_change = get_object_or_404(AllocationChangeRequest, pk=pk)
        attr_changes = self.get_allocation_attrs_to_change(allocation_change)
        if attr_changes:
            formset = formset_factory(self.formset_class, max_num=len(attr_changes))
            formset = formset(initial=attr_changes, prefix='attributeform')
            context['formset'] = formset
        context['allocation_change'] = allocation_change
        context['attribute_changes'] = attr_changes
        return context

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_change_obj = get_object_or_404(AllocationChangeRequest, pk=pk)

        allocation_change_form = AllocationChangeForm(
            initial={
                'justification': allocation_change_obj.justification,
                'end_date_extension': allocation_change_obj.end_date_extension,
            }
        )
        allocation_change_form.fields['justification'].disabled = True
        if allocation_change_obj.status.name != 'Pending':
            allocation_change_form.fields['end_date_extension'].disabled = True
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            allocation_change_form.fields['end_date_extension'].disabled = True

        note_form = AllocationChangeNoteForm(
            initial={'notes': allocation_change_obj.notes}
        )

        autoupdate_form = AllocationAutoUpdateForm()

        context = self.get_context_data()

        context['allocation_change_form'] = allocation_change_form
        context['autoupdate_form'] = autoupdate_form
        context['note_form'] = note_form
        return render(request, self.template_name, context)

    def redirect_to_detail(self, pk):
        return HttpResponseRedirect(
            reverse('allocation-change-detail', kwargs={'pk': pk})
        )

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        if not self.request.user.is_superuser:
            err = 'You do not have permission to update an allocation change request'
            messages.error(request, err)
            return self.redirect_to_detail(pk)

        alloc_change_obj = get_object_or_404(AllocationChangeRequest, pk=pk)
        allocation_change_form = AllocationChangeForm(
            request.POST,
            initial={
                'justification': alloc_change_obj.justification,
                'end_date_extension': alloc_change_obj.end_date_extension,
            },
        )
        allocation_change_form.fields['justification'].required = False

        attrs_to_change = self.get_allocation_attrs_to_change(alloc_change_obj)

        formset = formset_factory(self.formset_class, max_num=len(attrs_to_change))
        formset = formset(request.POST, initial=attrs_to_change, prefix='attributeform')

        note_form = AllocationChangeNoteForm(
            request.POST, initial={'notes': alloc_change_obj.notes}
        )

        if not note_form.is_valid():
            allocation_change_form = AllocationChangeForm(
                initial={'justification': alloc_change_obj.justification}
            )
            allocation_change_form.fields['justification'].disabled = True
            context = self.get_context_data()
            context['note_form'] = note_form
            context['allocation_change_form'] = allocation_change_form
            return render(request, self.template_name, context)

        action = request.POST.get('action')
        if action not in ['update', 'approve', 'deny']:
            return HttpResponseBadRequest('Invalid request')

        autoupdate_form = AllocationAutoUpdateForm(request.POST)

        validation_errors = []
        if not allocation_change_form.is_valid():
            for err in allocation_change_form.errors:
                validation_errors.append(err)
        if attrs_to_change and not formset.is_valid():
            if attrs_to_change:
                attribute_errors = ''
                for error in formset.errors:
                    if error:
                        attribute_errors += error.get('__all__')
                validation_errors.append(attribute_errors)
        if validation_errors:
            for err in validation_errors:
                messages.error(request, err)
            return self.redirect_to_detail(pk)

        notes = note_form.cleaned_data.get('notes')
        alloc_change_obj.notes = notes

        save_and_redirect = False
        if action == 'deny':
            status_denied_obj = AllocationChangeStatusChoice.objects.get(name='Denied')
            alloc_change_obj.status = status_denied_obj
            message = make_allocation_change_message(alloc_change_obj, 'DENIED')
            send_allocation_customer_email(
                alloc_change_obj.allocation,
                'Allocation Change Denied',
                'email/allocation_change_denied.txt',
                domain_url=get_domain_url(self.request),
            )
            save_and_redirect = True

        elif action == 'update' and alloc_change_obj.status.name != 'Pending':
            message = 'Allocation change request updated!'
            save_and_redirect = True
        if save_and_redirect:
            alloc_change_obj.save()
            messages.success(request, message)
            return self.redirect_to_detail(pk)

        form_data = allocation_change_form.cleaned_data
        end_date_extension = form_data.get('end_date_extension')

        if not attrs_to_change and end_date_extension == 0:
            messages.error(request, 'You must make a change to the allocation.')
            return self.redirect_to_detail(pk)

        if end_date_extension != alloc_change_obj.end_date_extension:
            alloc_change_obj.end_date_extension = end_date_extension

        if attrs_to_change:
            for entry in formset:
                formset_data = entry.cleaned_data
                new_value = formset_data.get('new_value')
                attribute_change = AllocationAttributeChangeRequest.objects.get(
                    pk=formset_data.get('change_pk')
                )
                if new_value != attribute_change.new_value:
                    attribute_change.new_value = new_value
                    attribute_change.save()

        if action == 'update':
            message = 'Allocation change request updated!'
        if action == 'approve':
            status_approved_obj = AllocationChangeStatusChoice.objects.get(
                name='Approved'
            )
            alloc_change_obj.status = status_approved_obj

            if alloc_change_obj.allocation.end_date and alloc_change_obj.end_date_extension > 0:
                rdelta = relativedelta(days=ALLOCATION_DEFAULT_ALLOCATION_LENGTH)
                new_end_date = alloc_change_obj.allocation.end_date + rdelta
                alloc_change_obj.allocation.end_date = new_end_date
                alloc_change_obj.allocation.save()

            if attrs_to_change:

                autoupdate_choice = autoupdate_form.data.get('auto_update_opts')
                if autoupdate_choice == '2':
                    # check resource type, see if appropriate plugin is available
                    # resource = alloc_change_obj.allocation.resources.first().name
                    resources_plugins = {
                        'isilon': 'coldfront.plugins.isilon',
                        # 'lfs': 'coldfront.plugins.lustre',
                    }
                    rtype = next((k for k in resources_plugins if k in alloc_change_obj.allocation.get_parent_resource.name), None)
                    if not rtype:
                        err = ('You cannot auto-update non-isilon resources at this '
                            'time. Please manually update the resource before '
                            'approving this change request.')
                        messages.error(request, err)
                        return self.redirect_to_detail(pk)
                    # get new quota value
                    new_quota = next((
                        a for a in attrs_to_change if a['name'] == 'Storage Quota (TB)'), None)
                    if not new_quota:
                        err = ('You can only auto-update resource quotas at this '
                            'time. Please manually update the resource before '
                            'approving this change request.')
                        messages.error(request, err)
                        return self.redirect_to_detail(pk)

                    new_quota_value = int(new_quota['new_value'])
                    plugin = resources_plugins[rtype]
                    if plugin in settings.INSTALLED_APPS:
                        try:
                            update_isilon_allocation_quota(
                                alloc_change_obj.allocation, new_quota_value
                            )
                        except Exception as e:
                            err = ("An error was encountered while auto-updating"
                                "the allocation quota. Please contact Coldfront "
                                "administration and/or manually update the allocation.")
                            messages.error(request, err)
                            return self.redirect_to_detail(pk)
                    else:
                        err = ("There is an issue with the configuration of "
                            "Coldfront's auto-updating capabilities. Please contact Coldfront "
                            "administration and/or manually update the allocation.")
                        messages.error(request, err)
                        return self.redirect_to_detail(pk)

                attr_changes = alloc_change_obj.allocationattributechangerequest_set.all()
                for attribute_change in attr_changes:
                    new_value = attribute_change.new_value
                    attribute_change.allocation_attribute.value = new_value
                    attribute_change.allocation_attribute.save()

            allocation_change_approved.send(
                sender=self.__class__,
                allocation_pk=alloc_change_obj.allocation.pk,
                allocation_change_pk=alloc_change_obj.pk,
            )

            send_allocation_customer_email(
                alloc_change_obj.allocation,
                'Allocation Change Approved',
                'email/allocation_change_approved.txt',
                domain_url=get_domain_url(self.request),
            )

            message = make_allocation_change_message(alloc_change_obj, 'APPROVED')

        if action in ['update', 'approve']:
            alloc_change_obj.save()
            messages.success(request, message)

        return self.redirect_to_detail(pk)


class AllocationChangeListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_change_list.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        review_perm = 'allocation.can_review_allocation_requests'
        if self.request.user.is_superuser or self.request.user.has_perm(review_perm):
            return True
        err = 'You do not have permission to review allocation requests.'
        messages.error(self.request, err)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_change_list = AllocationChangeRequest.objects.filter(
            status__name__in=['Pending']
        )
        context['allocation_change_list'] = allocation_change_list
        context['PROJECT_ENABLE_PROJECT_REVIEW'] = PROJECT_ENABLE_PROJECT_REVIEW
        return context


class AllocationChangeView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    formset_class = AllocationAttributeChangeForm
    template_name = 'allocation/allocation_change.html'

    def test_func(self):
        """UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.has_perm(self.request.user, AllocationPermission.MANAGER):
            return True
        err = 'You do not have permission to request changes to this allocation.'
        messages.error(self.request, err)
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        errs = []
        if allocation_obj.project.needs_review:
            err = 'You cannot request a change to this allocation because you have to review your project first.'
            errs.append(err)
        if allocation_obj.project.status.name not in PENDING_ACTIVE_ALLOCATION_STATUSES:
            err = 'You cannot request a change to an allocation in an archived project.'
            errs.append(err)
        if allocation_obj.is_locked:
            err = 'You cannot request a change to a locked allocation.'
            errs.append(err)
        if allocation_obj.resources.filter(resource_type__name='Storage').count() == 0:
            errs.append('You can only request changes for storage allocations.')
        changeable_status_list = [
            'Active', 'Renewal Requested', 'Payment Pending', 'Payment Requested', 'Paid'
        ]
        if allocation_obj.status.name not in changeable_status_list:
            err = f'You cannot request a change to an allocation with status "{allocation_obj.status.name}"'
            errs.append(err)

        if errs:
            for err in errs:
                messages.error(request, err)
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            )

        return super().dispatch(request, *args, **kwargs)

    def get_allocation_attrs_to_change(self, allocation_obj):
        attributes_to_change = allocation_obj.allocationattribute_set.filter(
            allocation_attribute_type__is_changeable=True
        )
        attributes_to_change = [
            {
                'pk': attribute.pk,
                'name': attribute.allocation_attribute_type.name,
                'value': attribute.value,
            }
            for attribute in attributes_to_change
        ]
        return attributes_to_change

    def get(self, request, *args, **kwargs):
        context = {}
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        form = AllocationChangeForm(**self.get_form_kwargs())
        context['form'] = form

        attrs_to_change = self.get_allocation_attrs_to_change(allocation_obj)
        if attrs_to_change:
            formset = formset_factory(self.formset_class, max_num=len(attrs_to_change))
            formset = formset(initial=attrs_to_change, prefix='attributeform')
            context['formset'] = formset

        if allocation_obj.get_parent_resource:
            resource_used = allocation_obj.get_parent_resource.used_percentage
        else:
            resource_used = None
        context['allocation'] = allocation_obj
        context['attributes'] = attrs_to_change
        context['used_percentage'] = resource_used
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        attribute_changes_to_make = set({})
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        form = AllocationChangeForm(**self.get_form_kwargs())
        attrs_to_change = self.get_allocation_attrs_to_change(allocation_obj)

        # find errors
        validation_errors = []

        if not form.is_valid():
            validation_errors.extend(list(form.errors))

        if attrs_to_change:
            formset = formset_factory(self.formset_class, max_num=len(attrs_to_change))
            formset = formset(
                request.POST, initial=attrs_to_change, prefix='attributeform'
            )

            if not formset.is_valid():
                attribute_errors = ''
                for error in formset.errors:
                    if error:
                        attribute_errors += error.get('__all__')
                validation_errors.append(attribute_errors)

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return HttpResponseRedirect(reverse('allocation-change', kwargs={'pk': pk}))

        # ID changes
        change_requested = False

        form_data = form.cleaned_data

        if form_data.get('end_date_extension') != 0:
            change_requested = True

        # if requested resource is on NESE, add to vars
        nese = bool(allocation_obj.resources.filter(name__contains="nesetape"))

        if attrs_to_change:
            for entry in formset:
                formset_data = entry.cleaned_data

                new_value = formset_data.get('new_value')
                # require nese shares to be divisible by 20
                if formset_data['name'] == 'Storage Quota (TB)':
                    try:
                        new_value = re.sub('\.0$', '', new_value)
                        tbs = int(new_value)
                    except ValueError:
                        messages.error(request, 'Requested storage quota must be an integer.')
                        return HttpResponseRedirect(reverse('allocation-change', kwargs={'pk': pk}))
                else:
                    tbs = False
                if nese and tbs and tbs % 20 != 0:
                    messages.error(request, "Tier 3 quantity must be a multiple of 20.")
                    return HttpResponseRedirect(reverse('allocation-change', kwargs={'pk': pk}))

                if new_value != '':
                    change_requested = True
                    allocation_attribute = AllocationAttribute.objects.get(
                        pk=formset_data.get('pk')
                    )
                    attribute_changes_to_make.add((allocation_attribute, new_value))

        if not change_requested:
            messages.error(request, 'You must request a change.')
            return HttpResponseRedirect(reverse('allocation-change', kwargs={'pk': pk}))

        end_date_extension = form_data.get('end_date_extension')
        justification = form_data.get('justification')
        change_request_status = AllocationChangeStatusChoice.objects.get(name='Pending')

        allocation_change_request_obj = AllocationChangeRequest.objects.create(
            allocation=allocation_obj,
            end_date_extension=end_date_extension,
            justification=justification,
            status=change_request_status,
        )

        for attribute in attribute_changes_to_make:
            AllocationAttributeChangeRequest.objects.create(
                allocation_change_request=allocation_change_request_obj,
                allocation_attribute=attribute[0],
                new_value=attribute[1],
            )

        messages.success(request, 'Allocation change request successfully submitted.')

        quantity = [
            a for a in attribute_changes_to_make
            if a[0].allocation_attribute_type.name == 'Storage Quota (TB)'
        ]

        email_vars = {
            'justification': justification,
            'user': self.request.user,
            'nese': nese,
        }
        if quantity:
            quantity_num = int(float(quantity[0][1]))
            difference = quantity_num - int(float(allocation_obj.size))
            used_percentage = allocation_obj.get_parent_resource.used_percentage
            current_size = allocation_obj.size
            if nese:
                current_size = round(current_size, -1)
                difference = round(difference, -1)
            email_vars['quantity'] = quantity_num
            email_vars['current_size'] = current_size
            email_vars['difference'] = difference
            email_vars['used_percentage'] = used_percentage

        send_allocation_admin_email(
            allocation_obj,
            'New Allocation Change Request',
            'email/new_allocation_change_request.txt',
            url_path=reverse(
                'allocation-change-detail',
                kwargs={'pk': allocation_change_request_obj.pk},
            ),
            domain_url=get_domain_url(self.request),
            other_vars=email_vars,
        )
        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationChangeDeleteAttributeView(
    LoginRequiredMixin, UserPassesTestMixin, View
):
    def test_func(self):
        """UserPassesTestMixin Tests"""
        perm_string = 'allocation.can_review_allocation_requests'
        review_perm = self.request.user.has_perm(perm_string)
        if self.request.user.is_superuser or review_perm:
            return True

        error = 'You do not have permission to update an allocation change request.'
        messages.error(self.request, error)
        return False

    def get(self, request, pk):
        allocationattr_change = get_object_or_404(
            AllocationAttributeChangeRequest, pk=pk
        )
        allocation_change_pk = allocationattr_change.allocation_change_request.pk
        allocationattr_change.delete()
        success_msg = 'Allocation attribute change request successfully deleted.'
        messages.success(request, success_msg)
        return HttpResponseRedirect(
            reverse('allocation-change-detail', kwargs={'pk': allocation_change_pk})
        )
