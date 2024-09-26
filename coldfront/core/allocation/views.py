import datetime
import logging
import urllib
import csv
from datetime import date

from dateutil.relativedelta import relativedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.db.models.query import QuerySet
from django.forms import formset_factory
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html, mark_safe
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.http.response import StreamingHttpResponse

from coldfront.core.allocation.forms import (AllocationAccountForm,
                                             AllocationAddUserForm,
                                             AllocationAttributeCreateForm,
                                             AllocationAttributeDeleteForm,
                                             AllocationChangeForm,
                                             AllocationChangeNoteForm,
                                             AllocationAttributeChangeForm,
                                             AllocationAttributeUpdateForm,
                                             AllocationAttributeEditForm,
                                             AllocationForm,
                                             AllocationInvoiceNoteDeleteForm,
                                             AllocationInvoiceUpdateForm,
                                             AllocationRemoveUserForm,
                                             AllocationReviewUserForm,
                                             AllocationSearchForm,
                                             AllocationUpdateForm,
                                             AllocationInvoiceExportForm,
                                             AllocationInvoiceSearchForm,
                                             AllocationExportForm,
                                             AllocationUserUpdateForm,
                                             )
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
                                              AllocationUserRequestStatusChoice,
                                              AllocationUserRequest,
                                              AllocationUserStatusChoice,
                                              AllocationInvoice,
                                              AllocationRemovalRequest,
                                              AllocationRemovalStatusChoice)
from coldfront.core.allocation.signals import (allocation_activate,
                                               allocation_activate_user,
                                               allocation_disable,
                                               allocation_remove_user,
                                               allocation_change_approved,
                                               allocation_change_user_role,
                                               allocation_remove,
                                               visit_allocation_detail)
from coldfront.core.allocation.utils import (compute_prorated_amount,
                                             generate_guauge_data_from_usage,
                                             get_user_resources,
                                             send_allocation_user_request_email,
                                             send_added_user_email,
                                             send_removed_user_email,
                                             create_admin_action,
                                             create_admin_action_for_deletion,
                                             create_admin_action_for_creation,
                                             get_allocation_user_emails,
                                             check_if_roles_are_enabled,
                                             set_default_allocation_user_role,
                                             get_default_allocation_user_role)
from coldfront.core.project.models import (Project, ProjectUser, ProjectPermission,
                                           ProjectUserStatusChoice)
from coldfront.core.resource.models import Resource, ResourceAttributeType
from coldfront.core.utils.common import get_domain_url, import_from_settings, Echo
from coldfront.core.utils.mail import send_allocation_admin_email, send_allocation_customer_email, send_email_template, get_email_recipient_from_groups
from coldfront.core.utils.slack import send_message
from coldfront.core.utils.groups import check_if_groups_in_review_groups

ALLOCATION_ENABLE_ALLOCATION_RENEWAL = import_from_settings(
    'ALLOCATION_ENABLE_ALLOCATION_RENEWAL', True)
ALLOCATION_DEFAULT_ALLOCATION_LENGTH = import_from_settings(
    'ALLOCATION_DEFAULT_ALLOCATION_LENGTH', 365)
ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT = import_from_settings(
    'ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT', True)
ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING = import_from_settings(
    'ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING',
    30
)
ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING = import_from_settings(
    'ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING',
    60
)

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
SLACK_MESSAGING_ENABLED = import_from_settings(
    'SLACK_MESSAGING_ENABLED', False
)
SLATE_PROJECT_SHOW_ESTIMATED_COST = import_from_settings(
    'SLATE_PROJECT_SHOW_ESTIMATED_COST', False
)

logger = logging.getLogger(__name__)


class AllocationDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    model = Allocation
    template_name = 'allocation/allocation_detail.html'
    context_object_name = 'allocation'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        if self.request.user.has_perm('allocation.can_view_all_allocations'):
            return True
        
        return allocation_obj.has_perm(self.request.user, AllocationPermission.USER)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        visit_allocation_detail.send(sender=self.__class__, allocation_pk=pk)
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        allocation_users = allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed']).order_by('user__username')

        # set visible usage attributes
        alloc_attr_set = allocation_obj.get_attribute_set(self.request.user)
        attributes_with_usage = [a for a in alloc_attr_set if hasattr(a, 'allocationattributeusage')]
        attributes = alloc_attr_set

        allocation_changes = allocation_obj.allocationchangerequest_set.all().order_by('-pk')

        guage_data = []
        invalid_attributes = []
        for attribute in attributes_with_usage:
            try:
                guage_data.append(generate_guauge_data_from_usage(
                                attribute.allocation_attribute_type.name,
                                float(attribute.value),
                                float(attribute.allocationattributeusage.value)
                                ))
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
        context['allocation_changes_enabled'] = allocation_obj.is_changeable
        context['display_estimated_cost'] = False
        if 'coldfront.plugins.slate_project' in settings.INSTALLED_APPS: 
            context['display_estimated_cost'] = SLATE_PROJECT_SHOW_ESTIMATED_COST

        # Can the user update the project?
        context['is_allowed_to_update_project'] = allocation_obj.project.has_perm(self.request.user, ProjectPermission.UPDATE, 'change_project')

        context['allocation_user_roles_enabled'] = check_if_roles_are_enabled(allocation_obj)
        context['allocation_users'] = allocation_users
        context['allocation_invoices'] = allocation_obj.allocationinvoice_set.all()

        if (
            self.request.user.is_superuser
            or self.request.user.has_perm('allocation.view_allocationusernote')
        ):
            notes = allocation_obj.allocationusernote_set.all()
        else:
            notes = allocation_obj.allocationusernote_set.filter(
                is_private=False)

        context['user_has_permissions'] = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'change_allocation'
        )

        if self.request.user.is_superuser:
            context['user_has_permissions'] = True

        context['user_exists_in_allocation'] = allocation_obj.allocationuser_set.filter(
            user=self.request.user, status__name__in=['Active', 'Pending - Remove', 'Eligible', 'Disabled', 'Retired']).exists()

        context['project'] = allocation_obj.project
        context['notes'] = notes
        context['ALLOCATION_ENABLE_ALLOCATION_RENEWAL'] = ALLOCATION_ENABLE_ALLOCATION_RENEWAL
        context['ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING'] = ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING
        context['ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING'] = ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING
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
        if not request.user.is_superuser:
            group_exists = check_if_groups_in_review_groups(
                allocation_obj.get_parent_resource.review_groups.all(),
                self.request.user.groups.all(),
                'change_allocation'
            )
            if not group_exists:
                messages.error(
                    request,
                    'You do not have permission to update this allocation'
                )
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

        if not form.is_valid():
            context = self.get_context_data()
            context['form'] = form
            context['allocation'] = allocation_obj
            return render(request, self.template_name, context)
        
        action = request.POST.get('action')
        if action not in ['update', 'approve', 'auto-approve', 'deny']:
            return HttpResponseBadRequest("Invalid request")
        
        form_data = form.cleaned_data
        create_admin_action(request.user, form_data, allocation_obj)
        old_status = allocation_obj.status.name

        if action in ['update', 'approve', 'deny']:
            allocation_obj.end_date = form_data.get('end_date')
            allocation_obj.start_date = form_data.get('start_date')
            allocation_obj.description = form_data.get('description')
            allocation_obj.is_locked = form_data.get('is_locked')
            allocation_obj.is_changeable = form_data.get('is_changeable')
            allocation_obj.status = form_data.get('status')


        if 'approve' in action:
            allocation_obj.status = AllocationStatusChoice.objects.get(name='Active')
        elif action == 'deny':
            allocation_obj.status = AllocationStatusChoice.objects.get(name='Denied')

        if old_status != 'Active' == allocation_obj.status.name:
            if allocation_obj.project.status.name != "Active":
                messages.error(request, 'Project must be approved first before you can update this allocation\'s status!')
                return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))
            if not allocation_obj.start_date:
                allocation_obj.start_date = datetime.datetime.now()
            if 'approve' in action or not allocation_obj.end_date:
                allocation_obj.end_date = allocation_obj.project.end_date

            allocation_obj.save()

            allocation_activate.send(
                sender=self.__class__, allocation_pk=allocation_obj.pk)
            allocation_users = allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error'])
            for allocation_user in allocation_users:
                allocation_activate_user.send(
                    sender=self.__class__, allocation_user_pk=allocation_user.pk)
            
            resource_email_template_lookup_table = {
                'Quartz': {
                    'template': 'email/allocation_quartz_activated.txt',
                    'template_context': {
                        'help_url': EMAIL_TICKET_SYSTEM_ADDRESS,
                        'slurm_account_name': allocation_obj.get_attribute('slurm_account_name')
                    },
                },
                'Big Red 200': {
                    'template': 'email/allocation_bigred200_activated.txt',
                    'template_context': {
                        'help_url': EMAIL_TICKET_SYSTEM_ADDRESS,
                        'slurm_account_name': allocation_obj.get_attribute('slurm_account_name')
                    },
                }
            }

            addtl_context = {}
            resource_email_template = resource_email_template_lookup_table.get(
                allocation_obj.get_parent_resource.name
            )
            if resource_email_template is None:
                email_template = 'email/allocation_activated.txt'
            else:
                email_template = resource_email_template['template']
                addtl_context = resource_email_template['template_context']

            send_allocation_customer_email(allocation_obj, 'Allocation Activated', email_template, domain_url=get_domain_url(self.request), addtl_context=addtl_context)
            if action != 'auto-approve':
                messages.success(request, 'Allocation Activated!')
            logger.info(
                f'Admin {request.user.username} approved a {allocation_obj.get_parent_resource.name} '
                f'allocation (allocation pk={allocation_obj.pk})'
            )

        elif old_status != allocation_obj.status.name in ['Denied', 'New', 'Revoked', 'Removed']:
            allocation_obj.end_date = datetime.datetime.now() if allocation_obj.status.name != 'New' else None
            allocation_obj.save()

            if allocation_obj.status.name == ['Denied', 'Revoked', 'Removed']:
                allocation_disable.send(
                    sender=self.__class__, allocation_pk=allocation_obj.pk)
                allocation_users = allocation_obj.allocationuser_set.exclude(
                                        status__name__in=['Removed', 'Error'])
                for allocation_user in allocation_users:
                    allocation_remove_user.send(
                        sender=self.__class__, allocation_user_pk=allocation_user.pk)
            if allocation_obj.status.name == 'Denied':
                send_allocation_customer_email(allocation_obj, 'Allocation Denied', 'email/allocation_denied.txt', domain_url=get_domain_url(self.request))
                messages.success(request, 'Allocation Denied!')
            elif allocation_obj.status.name == 'Revoked':
                send_allocation_customer_email(allocation_obj, 'Allocation Revoked', 'email/allocation_revoked.txt', domain_url=get_domain_url(self.request))
                messages.success(request, 'Allocation Revoked!')
            elif allocation_obj.status.name == 'Removed':
                send_allocation_customer_email(allocation_obj, 'Allocation Removed', 'email/allocation_removed.txt', domain_url=get_domain_url(self.request))
                messages.success(request, 'Allocation Removed!')
            else:
                messages.success(request, 'Allocation updated!')
            logger.info(
                f'Admin {request.user.username} changed the status of a '
                f'{allocation_obj.get_parent_resource.name} allocation to '
                f'{allocation_obj.status.name} (allocation pk={allocation_obj.pk})'
            )
        else:
            messages.success(request, 'Allocation updated!')
            allocation_obj.save()


        if action == 'auto-approve':
            messages.success(request, 'Allocation to {} has been ACTIVATED for {} {} ({})'.format(
                allocation_obj.get_parent_resource,
                allocation_obj.project.pi.first_name,
                allocation_obj.project.pi.last_name,
                allocation_obj.project.pi.username)
            )
            return HttpResponseRedirect(reverse('allocation-request-list'))

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


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

            if data.get('show_all_allocations') and self.request.user.is_superuser:
                allocations = Allocation.objects.prefetch_related(
                    'project', 'project__pi', 'status',
                ).all().order_by(order_by)
            elif data.get('show_all_allocations') and self.request.user.has_perm('allocation.can_view_all_allocations'):
                allocations = Allocation.objects.prefetch_related(
                    'project', 'project__pi', 'status',
                ).filter(
                    resources__review_groups__in=list(self.request.user.groups.all())
                ).order_by(order_by)

            else:
                allocations = Allocation.objects.prefetch_related('project', 'project__pi', 'status',).filter(
                    Q(project__status__name__in=['New', 'Active', ]) &
                    Q(project__projectuser__user=self.request.user) &
                    Q(project__projectuser__status__name='Active') &
                    Q(allocationuser__user=self.request.user) &
                    Q(allocationuser__status__name__in= ['Active', 'Pending - Remove', 'Eligible', 'Disabled', 'Retired'])
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
                    Q(allocationuser__status__name__in= ['Active', 'Pending - Remove', 'Eligible', 'Disabled', 'Retired'])
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
                Q(allocationuser__status__name__in= ['Active', 'Pending - Remove', 'Eligible', 'Disabled', 'Retired'])
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

        context['allocation_export_form'] = AllocationExportForm()
        context['show_export_button'] = self.request.user.is_superuser or self.request.user.has_perm('allocation.can_view_all_allocations')

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
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        if project_obj.has_perm(self.request.user, ProjectPermission.UPDATE):
            return True

        messages.error(self.request, 'You do not have permission to create a new allocation.')
        return False

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
        resource_form = []
        resource_attributes_type_labels = ResourceAttributeType.objects.filter(
            name__endswith='label'
        )
        resource_attributes_type_field_names = [x.name[:-6] for x in resource_attributes_type_labels]
        resource_attributes_type_fields = ResourceAttributeType.objects.filter(
            name__in=resource_attributes_type_field_names
        )
        for resource_attributes_type_field in resource_attributes_type_fields:
            resource_attributes_type_field_name = resource_attributes_type_field.name
            resource_attributes_type_attribute_type_name = resource_attributes_type_field.attribute_type.name
            if resource_attributes_type_attribute_type_name == 'Yes/No':
                resource_attributes_type_attribute_type_name = 'radio'
            elif resource_attributes_type_attribute_type_name == 'True/False':
                resource_attributes_type_attribute_type_name = 'checkbox'

            if resource_attributes_type_field_name in ['access_level', 'system', 'storage_space_unit', 'use_type']:
                resource_attributes_type_attribute_type_name = 'radio'
            elif resource_attributes_type_field_name in ['campus_affiliation', 'training_or_inference']:
                resource_attributes_type_attribute_type_name = 'choice'
            elif resource_attributes_type_field_name in ['email', 'faculty_email']:
                resource_attributes_type_attribute_type_name = 'email'

            resource_form.append({
                resource_attributes_type_field_name: {},
                resource_attributes_type_field_name + '_label': {},
                'type': resource_attributes_type_attribute_type_name.lower()
            })

        # These do not exist as ResourceAttributeTypes
        resource_form.append({
            'group_account_name': {},
            'group_account_name_label': {},
            'type': 'text',
        })
        resource_form.append({
            'group_account_name_exists': {},
            'group_account_name_exists_label': {},
            'type': 'checkbox',
        })
        resource_form.append({
            'prorated_cost': {},
            'prorated_cost_label': {},
            'type': 'int',
        })
        resource_form.append({
            'quantity': {},
            'quantity_label': {},
            'type': 'int',
        })

        resource_special_attributes = [
            {
                'slurm_cluster': {},
                'has_requirement': {},
            }
        ]

        resource_descriptions = {}
        resources_requiring_user_accounts = []
        for resource in user_resources:
            resource_descriptions[resource.id] = resource.description

            if resource.resourceattribute_set.filter(resource_attribute_type__name='check_user_account').exists():
                resources_requiring_user_accounts.append(resource.pk)

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

        context['resources_requiring_user_accounts'] = resources_requiring_user_accounts
        context['resources_with_eula'] = resources_with_eula
        context['resources_with_accounts'] = list(Resource.objects.filter(
            name__in=list(ALLOCATION_ACCOUNT_MAPPING.keys())).values_list('id', flat=True))

        after_project_creation = self.request.GET.get('after_project_creation')
        if after_project_creation is None:
            after_project_creation = 'false'
        context['after_project_creation'] = after_project_creation

        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        after_project_creation = self.request.GET.get('after_project_creation')
        if after_project_creation == 'true':
            after_project_creation = True
        else:
            after_project_creation = False

        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.request.user, self.kwargs.get('project_pk'), after_project_creation, **self.get_form_kwargs())

    def calculate_end_date(self, month, day, license_term='current'):
        current_date = datetime.date.today()
        license_end_date = datetime.date(current_date.year, month, day)
        if current_date > license_end_date:
            license_end_date = license_end_date.replace(year=license_end_date.year + 1)

        if license_term == 'current_and_next_year':
            license_end_date = license_end_date.replace(year=license_end_date.year + 1)

        return license_end_date

    def check_user_accounts(self, usernames, resource_obj):
        denied_users = []
        approved_users = []
        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_users_info
            results = get_users_info(usernames, ['memberOf'])
            for username in usernames:
                if not resource_obj.check_user_account_exists(username, results.get(username).get('memberOf')):
                    denied_users.append(username)
                else:
                    approved_users.append(username)

        if denied_users:
            messages.warning(self.request, format_html(
                'The following users do not have an account on {} and were not added: {}. Please\
                direct them to\
                <a href="https://access.iu.edu/Accounts/Create">https://access.iu.edu/Accounts/Create</a>\
                to create an account.'
                .format(resource_obj.name, ', '.join(denied_users))
            ))
        return approved_users

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(
            Project, pk=self.kwargs.get('project_pk'))
        resource_obj = Resource.objects.get(pk=form_data.get('resource'))
        justification = form_data.get('justification')
        end_date = form_data.get('end_date')
        allocation_account = form_data.get('allocation_account', None)

        allocation_limit = resource_obj.get_attribute('allocation_limit')
        if allocation_limit is not None:
            num_allocations = 0
            allocations = project_obj.allocation_set.filter(
                status__in=[
                    AllocationStatusChoice.objects.get(name="Active"),
                    AllocationStatusChoice.objects.get(name="New"),
                    AllocationStatusChoice.objects.get(name="Billing Information Submitted"),
                    AllocationStatusChoice.objects.get(name="Renewal Requested"),
                    AllocationStatusChoice.objects.get(name="Paid"),
                    AllocationStatusChoice.objects.get(name="Payment Pending"),
                    AllocationStatusChoice.objects.get(name="Payment Requested")
                ]
            )
            for allocation in allocations:
                if allocation.get_parent_resource == resource_obj:
                    num_allocations += 1

            if num_allocations >= allocation_limit:
                form.add_error(
                    None,
                    'Your project has reached the max allocations it can have with this resource.'
                )
                return self.form_invalid(form)
        
        allocation_limit_per_pi = resource_obj.get_attribute('allocation_limit_per_pi')
        if allocation_limit_per_pi is not None:
            allocations = Allocation.objects.filter(
                project__status__name='Active',
                project__pi=project_obj.pi,
                status__name__in=['Active', 'New', 'Renewal Requested'],
                resources__name='Slate Project'
            )
            if len(allocations) > allocation_limit_per_pi:
                error_message = 'This PI has reached their limit on owning Slate Projects.'
                if self.request.user == project_obj.pi:
                    error_message = 'You have reached your limit on owning Slate Projects'
                form.add_error(
                    None,
                    error_message
                )
                return self.form_invalid(form)

        if end_date is None:
            end_date = project_obj.end_date
            expiry_date = resource_obj.get_attribute('expiry_date')
            if expiry_date is not None:
                month, day, year = expiry_date.split('/')
                end_date = self.calculate_end_date(int(month), int(day))
        elif end_date > project_obj.end_date:
            end_date = project_obj.end_date

        # A resource is selected that requires an account name selection but user has no account names
        if ALLOCATION_ACCOUNT_ENABLED and resource_obj.name in ALLOCATION_ACCOUNT_MAPPING and AllocationAttributeType.objects.filter(
                name=ALLOCATION_ACCOUNT_MAPPING[resource_obj.name]).exists() and not allocation_account:
            form.add_error(None, format_html(
                'You need to create an account name. Create it by clicking the link under the "Allocation account" field.'))
            return self.form_invalid(form)

        usernames = form_data.get('users')
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

        if not resource_obj.check_user_account_exists(self.request.user.username):
            form.add_error(
                None,
                format_html('You do not have an account on {}. You will need to create one\
                <a href="https://access.iu.edu/Accounts/Create">here</a> in order to submit a\
                resource request for this resource.'.format(resource_obj.name))
            )
            return self.form_invalid(form)
        usernames = self.check_user_accounts(usernames, resource_obj)

        if INVOICE_ENABLED and resource_obj.requires_payment:
            allocation_status_obj = AllocationStatusChoice.objects.get(
                name=INVOICE_DEFAULT_STATUS)
        else:
            allocation_status_obj = AllocationStatusChoice.objects.get(
                name='New')

        allocation_obj = Allocation.objects.create(
            project=project_obj,
            justification=justification,
            status=allocation_status_obj
        )

        if ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT:
            allocation_obj.is_changeable = True
            allocation_obj.save()

        allocation_obj.resources.add(resource_obj)

        # This section of code first grabs all the allocation attribute types that are linked to
        # the selected resource. Then it makes sure the only allocation attribute types included
        # are ones that have a linked resource attribute type that exists in a resource attribute
        # the selected resource has.
        allocation_attribute_type_objs = AllocationAttributeType.objects.filter(
            linked_resources__id__exact=resource_obj.id,
            linked_resource_attribute_type__isnull=False
        )
        linked_resource_attribute_type_objs = [
            allocation_attribute_type_obj.linked_resource_attribute_type
            for allocation_attribute_type_obj in allocation_attribute_type_objs
        ]
        resource_attribute_type_objs = resource_obj.resourceattribute_set.filter(
            resource=resource_obj,
            resource_attribute_type__in=linked_resource_attribute_type_objs
        )
        resource_attribute_type_objs = [
            resource_attribute_type_obj.resource_attribute_type
            for resource_attribute_type_obj in resource_attribute_type_objs
        ]
        for allocation_attribute_type_obj in allocation_attribute_type_objs:
            if allocation_attribute_type_obj.linked_resource_attribute_type in resource_attribute_type_objs:
                value = form_data.get(allocation_attribute_type_obj.linked_resource_attribute_type.name)
                if value:
                    AllocationAttribute.objects.create(
                        allocation_attribute_type=allocation_attribute_type_obj,
                        allocation=allocation_obj,
                        value=value
                    )

        slurm_account_allocation_attribute_type_obj = AllocationAttributeType.objects.filter(
            name='slurm_account_name',
            linked_resources__id__exact=resource_obj.id
        )
        if slurm_account_allocation_attribute_type_obj.exists():
            AllocationAttribute.objects.create(
                allocation_attribute_type=slurm_account_allocation_attribute_type_obj[0],
                allocation=allocation_obj,
                value=project_obj.slurm_account_name
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

        users = [User.objects.get(username=username) for username in usernames]

        new_user_requests = []
        allocation_user_active_status_choice = AllocationUserStatusChoice.objects.get(name='Active')
        requires_user_request = allocation_obj.get_parent_resource.get_attribute('requires_user_request')
        requestor_user = User.objects.get(username=self.request.user.username)
        if requires_user_request is not None and requires_user_request == 'Yes':
            allocation_user_pending_status_choice = AllocationUserStatusChoice.objects.get(
                name='Pending - Add'
            )
            for user in users:
                if user.username == self.request.user.username or user.username == allocation_obj.project.pi.username:
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

                set_default_allocation_user_role(resource_obj, allocation_user_obj)
        else:
            for user in users:
                allocation_user_obj = AllocationUser.objects.create(
                    allocation=allocation_obj,
                    user=user,
                    status=allocation_user_active_status_choice
                )

                set_default_allocation_user_role(resource_obj, allocation_user_obj)

        pi_name = '{} {} ({})'.format(allocation_obj.project.pi.first_name,
                                      allocation_obj.project.pi.last_name, allocation_obj.project.pi.username)
        domain_url = get_domain_url(self.request)
        url = '{}{}'.format(domain_url, reverse('allocation-request-list'))
        project_detail_url = '{}{}'.format(
            domain_url, reverse('project-detail', kwargs={'pk': allocation_obj.project.pk})
        )
        resource_name = allocation_obj.get_parent_resource
        if SLACK_MESSAGING_ENABLED:
            text = (
                f'A new allocation in project "{project_obj.title}" with id {project_obj.pk} has '
                f'been requested for {pi_name} - {resource_name}. Please review the allocation: '
                f'{url}. Project detail url: {project_detail_url}'
            )
            send_message(text)
        if EMAIL_ENABLED:
            template_context = {
                'project_title': project_obj.title,
                'project_id': project_obj.pk,
                'pi': pi_name,
                'resource': resource_name,
                'url': url,
                'project_detail_url': project_detail_url
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
            else:
                users.remove(self.request.user)
                if project_obj.pi in users:
                    users.remove(project_obj.pi)

                if users:
                    allocations_added_users = [user.username for user in users]
                    allocations_added_users_emails = list(project_obj.projectuser_set.filter(
                        user__in=users,
                        enable_notifications=True
                    ).values_list('user__email', flat=True))
                    if project_obj.pi.email not in allocations_added_users_emails:
                        allocations_added_users_emails.append(project_obj.pi.email)

                    send_added_user_email(
                        self.request,
                        allocation_obj,
                        allocations_added_users,
                        allocations_added_users_emails
                    )

        logger.info(
            f'User {self.request.user.username} submitted a request for a '
            f'{allocation_obj.get_parent_resource.name} allocation (allocation pk={allocation_obj.pk})'
        )

        added_users = [user.username for user in users if user != self.request.user]
        if added_users:
            logger.info (
                f'User {self.request.user.username} added {", ".join(added_users)} to a new allocation '
                f'(allocation pk={allocation_obj.pk})'
            )
        return super().form_valid(form)

    def reverse_with_params(self, path, **kwargs):
        return path + '?' + urllib.parse.urlencode(kwargs)

    def get_success_url(self):
        after_project_creation = self.request.GET.get('after_project_creation')
        if after_project_creation is None:
            after_project_creation = False

        if not after_project_creation:
            url = self.reverse_with_params(
                reverse(
                    'project-detail',
                    kwargs={'pk': self.kwargs.get('project_pk')}
                ),
                allocation_submitted='true'
            )
        else:
            url = self.reverse_with_params(
                reverse(
                    'project-add-users-search',
                    kwargs={'pk': self.kwargs.get('project_pk')}
                ),
                after_project_creation='true'
            )

        return url


class AllocationAddUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_add_users.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.has_perm(self.request.user, AllocationPermission.MANAGER, 'add_allocationuser'):
            return True

        messages.error(self.request, 'You do not have permission to add users to the allocation.')
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        message = None
        if allocation_obj.is_locked and not self.request.user.is_superuser:
            message = 'You cannot modify this allocation because it is locked! Contact support for details.'
        elif allocation_obj.status.name not in ['Active', 'New', 'Renewal Requested', 'Payment Pending', 'Payment Requested', 'Paid']:
            message = f'You cannot add users to an allocation with status {allocation_obj.status.name}.'
        if message:
            messages.error(request, message)
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_users_to_add(self, allocation_obj):
        active_users_in_project = list(allocation_obj.project.projectuser_set.filter(
            status__name='Active').values_list('user__username', flat=True))
        users_already_in_allocation = list(allocation_obj.allocationuser_set.exclude(
            status__name__in=['Removed']).values_list('user__username', flat=True))

        missing_users = list(set(active_users_in_project) -
                             set(users_already_in_allocation))
        missing_users = User.objects.filter(username__in=missing_users)
        # .exclude(pk=allocation_obj.project.pi.pk)

        resource_obj = allocation_obj.get_parent_resource

        users_to_add = []
        for user in missing_users:
            role = get_default_allocation_user_role(resource_obj, allocation_obj.project, user)
            if role.exists():
                role = role[0]
            else:
                role = None
            users_to_add.append({
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': role
            })

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
    
    def get_users_accounts(self, formset):
        selected_users_accounts = {}
        selected_users_usernames = []
        for form in formset:
            user_form_data = form.cleaned_data
            if user_form_data.get('selected'):
                selected_users_usernames.append(user_form_data.get('username'))
                selected_users_accounts[user_form_data.get('username')] = []

        if 'coldfront.plugins.ldap_user_info' in settings.INSTALLED_APPS:
            from coldfront.plugins.ldap_user_info.utils import get_users_info
            results = get_users_info(selected_users_usernames, ['memberOf'])
            for username, result in results.items():
                selected_users_accounts[username] = result.get('memberOf')

        return selected_users_accounts

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_to_add = self.get_users_to_add(allocation_obj)
        context = {}

        if users_to_add:
            formset = formset_factory(
                AllocationAddUserForm, max_num=len(users_to_add))
            formset = formset(
                initial=users_to_add,
                prefix='userform',
                form_kwargs={
                    'resource': allocation_obj.get_parent_resource 
                }
            )
            context['formset'] = formset

        context['allocation_user_roles_enabled'] = check_if_roles_are_enabled(allocation_obj)
        context['allocation'] = allocation_obj
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)

        users_to_add = self.get_users_to_add(allocation_obj)
        allocation_user_limit = allocation_obj.get_parent_resource.get_attribute("user_limit")

        formset = formset_factory(
            AllocationAddUserForm, max_num=len(users_to_add))
        formset = formset(
            request.POST,
            initial=users_to_add,
            prefix='userform', form_kwargs={
                'resource': allocation_obj.get_parent_resource 
            }
        )

        added_users = []
        added_users_objs = []
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

            selected_users_accounts = self.get_users_accounts(formset)
            requestor_user = User.objects.get(username=request.user)
            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:

                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

                    username = user_obj.username
                    accounts = selected_users_accounts.get(username)
                    if allocation_obj.get_parent_resource.check_user_account_exists(username, accounts):
                        added_users.append(username)
                        added_users_objs.append(user_obj)
                    else:
                        denied_users.append(username)
                        continue

                    if allocation_obj.allocationuser_set.filter(user=user_obj).exists():
                        allocation_user_obj = allocation_obj.allocationuser_set.get(
                            user=user_obj)
                        allocation_user_obj.status = allocation_user_status_choice
                        allocation_user_obj.role = user_form_data.get('role')
                        allocation_user_obj.save()
                    else:
                        allocation_user_obj = AllocationUser.objects.create(
                            allocation=allocation_obj,
                            user=user_obj,
                            status=allocation_user_status_choice,
                            role=user_form_data.get('role')    
                        )

                    allocation_user_request_obj = allocation_obj.create_user_request(
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

                    logger.info(
                        f'User {request.user.username} requested to add {len(added_users)} user(s) '
                        f'to a {allocation_obj.get_parent_resource.name} allocation '
                        f'(allocation pk={allocation_obj.pk})'
                    )
                else:
                    if EMAIL_ENABLED:
                        allocation_added_users_emails = list(allocation_obj.project.projectuser_set.filter(
                            user__in=added_users_objs,
                            enable_notifications=True
                        ).values_list('user__email', flat=True))
                        if allocation_obj.project.pi.email not in allocation_added_users_emails:
                            allocation_added_users_emails.append(allocation_obj.project.pi.email)

                        send_added_user_email(request, allocation_obj, added_users, allocation_added_users_emails)

                    messages.success(
                        request,
                        'Added user(s) {} to allocation.'.format(', '.join(added_users))
                    )

                    logger.info(
                        f'User {request.user.username} added {", ".join(added_users)} '
                        f'to a {allocation_obj.get_parent_resource.name} allocation '
                        f'(allocation pk={allocation_obj.pk})'
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

                logger.info(
                    f'Users {", ".join(denied_users)} were missing accounts for a '
                    f'{allocation_obj.get_parent_resource.name} allocation (allocation pk={allocation_obj.pk})'
                )
        else:
            logger.warning(
                f'An error occured when adding users to an allocation (allocation pk={allocation_obj.pk})'
            )
            for error in formset.errors:
                messages.error(request, error.get('__all__'))
                return HttpResponseRedirect(reverse('allocation-add-users', kwargs={'pk': pk}))

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationRemoveUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_remove_users.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.has_perm(self.request.user, AllocationPermission.MANAGER, 'delete_allocationuser'):
            return True

        messages.error(self.request, 'You do not have permission to remove users from allocation.')
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        message = None
        if allocation_obj.is_locked and not self.request.user.is_superuser:
            message = 'You cannot modify this allocation because it is locked! Contact support for details.'
        elif allocation_obj.status.name not in ['Active', 'New', 'Renewal Requested', ]:
            message = f'You cannot remove users from a allocation with status {allocation_obj.status.name}.'
        if message:
            messages.error(request, message)
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
            allocation_user_pending_remove_status_choice = AllocationUserStatusChoice.objects.get(
                name='Pending - Remove'
            )

            allocation_user_status_choice = allocation_user_removed_status_choice
            requires_user_request = allocation_obj.get_parent_resource.get_attribute('requires_user_request')

            if requires_user_request is not None and requires_user_request == 'Yes':
                allocation_user_status_choice = allocation_user_pending_remove_status_choice

            removed_users = []
            removed_users_objs = []
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
                    removed_users_objs.append(user_obj)

                    allocation_user_obj = allocation_obj.allocationuser_set.get(
                        user=user_obj)
                    allocation_user_obj.status = allocation_user_status_choice
                    allocation_user_obj.save()
                    allocation_remove_user.send(sender=self.__class__,
                                                allocation_user_pk=allocation_user_obj.pk)

                    allocation_user_request_obj = allocation_obj.create_user_request(
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

                    logger.info(
                        f'User {request.user.username} requested to remove {len(removed_users)} '
                        f'user(s) from a {allocation_obj.get_parent_resource.name} allocation '
                        f'(allocation pk={allocation_obj.pk})'
                    )
                else:
                    if EMAIL_ENABLED:
                        allocation_removed_users_emails = list(allocation_obj.project.projectuser_set.filter(
                            user__in=removed_users_objs,
                            enable_notifications=True
                        ).values_list('user__email', flat=True))
                        if allocation_obj.project.pi.email not in allocation_removed_users_emails:
                            allocation_removed_users_emails.append(allocation_obj.project.pi.email)

                        send_removed_user_email(allocation_obj, removed_users, allocation_removed_users_emails)
                    messages.success(
                        request, 'Removed user(s) {} from allocation.'.format(', '.join(removed_users))
                    )

                    logger.info(
                        f'User {request.user.username} removed {", ".join(removed_users)} from a '
                        f'{allocation_obj.get_parent_resource.name} allocation (allocation pk={allocation_obj.pk})'
                    )

        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationAttributeCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationAttribute
    form_class = AllocationAttributeCreateForm
    template_name = 'allocation/allocation_allocationattribute_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        user = self.request.user
        if user.is_superuser:
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'add_allocationattribute'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to add attributes to this allocation.'
        )

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

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        current_allocation_attribute_objs = allocation_obj.allocationattribute_set.all()
        current_allocation_attribute_type_objs = []
        for allocation_attribute_obj in current_allocation_attribute_objs:
            current_allocation_attribute_type_objs.append(
                allocation_attribute_obj.allocation_attribute_type
            )
        allocation_attribute_type_objs = AllocationAttributeType.objects.all()
        allocation_attribute_type_pks = []
        for allocation_attribute_type_obj in allocation_attribute_type_objs:
            if allocation_attribute_type_obj in current_allocation_attribute_type_objs:
                continue

            if allocation_obj.get_parent_resource in allocation_attribute_type_obj.get_linked_resources():
                allocation_attribute_type_pks.append(allocation_attribute_type_obj.pk)
        form.fields['allocation_attribute_type'].queryset = AllocationAttributeType.objects.filter(
            pk__in=allocation_attribute_type_pks
        )

        return form

    def get_success_url(self):
        allocation_obj = Allocation.objects.get(pk=self.kwargs.get('pk'))
        logger.info(
            f'Admin {self.request.user.username} created a {allocation_obj.get_parent_resource.name} '
            f'allocation attribute (allocation pk={allocation_obj.pk})'
        )
        create_admin_action_for_creation(
            self.request.user,
            self.object,
            allocation_obj
        )
        return reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})


class AllocationAttributeDeleteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_allocationattribute_delete.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        user = self.request.user
        if user.is_superuser:
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'delete_allocationattribute'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to delete attributes from this allocation.'
        )

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

                    logger.info(
                        f'Admin {request.user.username} deleted a {allocation_obj.get_parent_resource.name} '
                        f'allocation attribute (allocation pk={allocation_obj.pk})'
                    )
                    create_admin_action_for_deletion(
                        request.user,
                        allocation_attribute,
                        allocation_attribute.allocation
                    )

                    allocation_attribute.delete()

            messages.success(request, 'Deleted {} attributes from allocation.'.format(
                attributes_deleted_count))
        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationAttributeUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    formset_class = AllocationAttributeEditForm
    template_name = 'allocation/allocation_allocationattribute_update.html'

    def test_func(self):
        """ UserPassesTestMixin """
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        user = self.request.user
        if user.is_superuser:
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            user.groups.all(),
            'change_allocationattribute'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to update attributes in this allocation.'
        )

    def get_allocation_attributes_to_change(self, allocation_obj):
        allocation_attributes = allocation_obj.allocationattribute_set.all()

        attributes_to_change = [

            {
             'attribute_pk': allocation_attribute.pk,
             'name': allocation_attribute.allocation_attribute_type.name,
             'value': allocation_attribute.value,
             'new_value': None,
             }

            for allocation_attribute in allocation_attributes
        ]

        return attributes_to_change

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(Allocation, pk=pk)
        allocation_attributes_to_change = self.get_allocation_attributes_to_change(
            allocation_obj
        )

        if allocation_attributes_to_change:
            formset = formset_factory(
                self.formset_class,
                max_num=len(allocation_attributes_to_change)
            )
            formset = formset(
                initial=allocation_attributes_to_change, prefix='attributeform'
            )
            context['formset'] = formset

        context['allocation'] = allocation_obj

        return context

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        allocation_obj = get_object_or_404(
            Allocation, pk=pk
        )

        allocation_attributes_to_change = self.get_allocation_attributes_to_change(
            allocation_obj
        )

        formset = formset_factory(
            self.formset_class,
            max_num=len(allocation_attributes_to_change)
        )
        formset = formset(
            request.POST,
            initial=allocation_attributes_to_change, prefix='attributeform'
        )

        no_changes = True
        if formset.is_valid():
            for entry in formset:
                formset_data = entry.cleaned_data
                new_value = formset_data.get('new_value')
                if not new_value:
                    continue
                no_changes = False

                allocation_attribute = AllocationAttribute.objects.get(
                    pk=formset_data.get('attribute_pk')
                )

                if new_value and new_value != allocation_attribute.value:
                    logger.info(
                        f'Admin {request.user.username} updated a {allocation_obj.get_parent_resource.name} '
                        f'allocation attribute (allocation pk={allocation_obj.pk})'
                    )
                    create_admin_action(
                        request.user,
                        {'new_value': new_value},
                        allocation_obj,
                        allocation_attribute
                    )

                    allocation_attribute.value = new_value
                    allocation_attribute.save()
        else:
            errors = []
            for error in formset.errors:
                if error.get('__all__') is not None:
                        errors.append(error.get('__all__')[0])

            messages.error(request,  ', '.join(errors))
            return HttpResponseRedirect(reverse('allocation-attribute-update', kwargs={'pk': pk}))

        if no_changes:
            messages.error(self.request, 'No allocation attributes where updated')
            return HttpResponseRedirect(reverse('allocation-attribute-update', kwargs={'pk': pk}))

        messages.success(request, 'Successfully updated allocation attributes')

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationNoteCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationUserNote
    fields = '__all__'
    template_name = 'allocation/allocation_note_create.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        user = self.request.user
        if user.is_superuser:
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'add_allocationadminnote'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to add a note to this allocation.'
        )

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
        logger.info(
            f'Admin {self.request.user.username} created an allocation note (allocation pk={self.object.allocation.pk})'
        )
        return reverse('allocation-detail', kwargs={'pk': self.object.allocation.pk})


class AllocationNoteUpdateView(SuccessMessageMixin, LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = AllocationUserNote
    template_name = 'allocation/allocation_note_update.html'
    fields = ['is_private', 'note']
    success_message = 'Allocation note updated.'

    def test_func(self):
        """ UserPassesTestMixin Tests """
        allocation_note_obj = get_object_or_404(AllocationUserNote, pk=self.kwargs.get('pk'))
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('allocation_pk'))
        user = self.request.user
        if user.is_superuser:
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'change_allocationusernote'
        )
        if not group_exists:
            messages.error(
                self.request, 'You do not have permission to update notes in this allocation.'
            )
            return False

        if user != allocation_note_obj.author:
            messages.error(
                self.request, 'Only the original author can edit this note.'
            )
            return False

        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_pk = self.kwargs.get('allocation_pk')
        allocation_obj = get_object_or_404(Allocation, pk=allocation_pk)
        context['allocation'] = allocation_obj
        return context

    def get_success_url(self):
        logger.info(
            f'Admin {self.request.user.username} updated an allocation note (allocation pk={self.object.allocation.pk})'
        )
        return reverse('allocation-detail', kwargs={'pk': self.object.allocation.pk})


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
        if self.request.user.is_superuser:
            allocation_list = Allocation.objects.filter(
                status__name__in=['New', 'Renewal Requested', 'Paid', 'Billing Information Submitted']
            ).exclude(project__status__name__in=['Review Pending', 'Archived'])
        else:
            allocation_list = Allocation.objects.filter(
                status__name__in=['New', 'Renewal Requested', 'Paid', 'Billing Information Submitted'],
                resources__review_groups__in=list(self.request.user.groups.all())
            ).exclude(project__status__name__in=['Review Pending', 'Archived'])

        context['allocation_status_active'] = AllocationStatusChoice.objects.get(name='Active')
        context['allocation_list'] = allocation_list
        context['PROJECT_ENABLE_PROJECT_REVIEW'] = PROJECT_ENABLE_PROJECT_REVIEW
        context['ALLOCATION_DEFAULT_ALLOCATION_LENGTH'] = ALLOCATION_DEFAULT_ALLOCATION_LENGTH
        return context


class AllocationRenewView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_renew.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.has_perm(self.request.user, AllocationPermission.MANAGER, 'can_review_allocation_requests'):
            return True

        messages.error(self.request, 'You do not have permission to renew allocation.')
        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))
        
        if not allocation_obj.project.requires_review:
            messages.error(
                request, 'Your allocation does not need to be renewed.'
            )
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if not ALLOCATION_ENABLE_ALLOCATION_RENEWAL:
            messages.error(
                request, 'Allocation renewal is disabled. Request a new allocation to this resource if you want to continue using it after the active until date.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.status.name not in ['Active', 'Expired', 'Revoked', ]:
            messages.error(request, 'You cannot renew an allocation with status "{}".'.format(
                allocation_obj.status.name))
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.project.status.name in ['Review Pending', 'Denied', 'Expired', 'Archived', ]:
            messages.error(
                request, 'You cannot renew an allocation with project status "{}".'.format(
                    allocation_obj.project.status.name
                )
            )
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.project.needs_review or allocation_obj.project.can_be_reviewed:
            messages.error(
                request, 'You cannot renew your allocation until you review your project first.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.expires_in > ALLOCATION_DAYS_TO_REVIEW_BEFORE_EXPIRING:
            messages.error(
                request, 'It is too soon to renew your allocation.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING > 0 and allocation_obj.expires_in < -ALLOCATION_DAYS_TO_REVIEW_AFTER_EXPIRING:
            messages.error(
                request, 'It is too late to renew your allocation.'
            )
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
        
        if allocation_obj.is_locked:
            messages.error(
                request, 'You cannot renew this allocation.'
            )
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
                            'Active', 'Denied', 'New', 'Billing Information Submitted', 'Paid', 'Payment Pending',
                                'Payment Requested', 'Payment Declined', 'Renewal Requested', 'Unpaid',)):

                            allocation_user_obj = active_allocation.allocationuser_set.filter(
                                user=user_obj)
                            if not allocation_user_obj.exists():
                                continue
                            allocation_user_obj = allocation_user_obj[0]
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

            project_obj = allocation_obj.project

            if EMAIL_ENABLED:
                template_context = {
                    'project_title': project_obj.title,
                    'project_id': project_obj.pk,
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

            logger.info(
                f'User {request.user.username} sent a {allocation_obj.get_parent_resource.name} '
                f'allocation renewal request (allocation pk={allocation_obj.pk})'
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
        if self.request.user.is_superuser:
            resource_objs = Resource.objects.filter(
                requires_payment=True
            )
        else:
            resource_objs = Resource.objects.filter(
                review_groups__in=list(self.request.user.groups.all()),
                requires_payment=True
            )
        resources = []
        for resource in resource_objs:
            resources.append(
                (resource.name, resource.name)
            )
        context['allocation_invoice_export_form'] = AllocationInvoiceExportForm(resources=resources)
        return context

    def get_queryset(self):
        if self.request.user.is_superuser:
            allocations = Allocation.objects.filter(
                status__name__in=['Active', ]
            )
        else:
            allocations = Allocation.objects.filter(
                status__name__in=['Active', ],
                resources__review_groups__in=list(self.request.user.groups.all())
            )
        allocations_require_payment = []
        for allocation in allocations:
            if allocation.get_parent_resource.requires_payment:
                allocations_require_payment.append(allocation)

        return allocations_require_payment


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

        messages.error(
            self.request, 'You do not have permission to manage invoices.')

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

            # if initial_data.get('status') != status and status.name in ['Paid', ]:
            #     AllocationInvoice.objects.create(
            #         allocation=allocation_obj,
            #         account_number=allocation_obj.account_number,
            #         sub_account_number=allocation_obj.sub_account_number,
            #         status=status
            #     )

            logger.info(
                f'Admin {request.user.username} updated an invoice\'s status (allocation pk={allocation_obj.pk})'
            )
            create_admin_action(
                request.user,
                {'status': status},
                allocation_obj
            )

            allocation_obj.status = status
            allocation_obj.save()
            messages.success(request, 'Allocation updated!')
        else:
            for error in form.errors:
                messages.error(request, error)
        return HttpResponseRedirect(reverse('allocation-invoice-detail', kwargs={'pk': pk}))


class AllocationAllInvoicesListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = AllocationInvoice
    template_name = 'allocation/allocation_all_invoices_list.html'
    context_object_name = 'allocation_invoice_list'
    paginate_by = 25

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

        allocation_invoice_search_form = AllocationInvoiceSearchForm(self.request.GET)

        if allocation_invoice_search_form.is_valid():
            data = allocation_invoice_search_form.cleaned_data

            if self.request.user.is_superuser:
                invoices = AllocationInvoice.objects.all().order_by(order_by)
            else:
                invoices = AllocationInvoice.objects.filter(
                    allocation__resources__review_groups__in=list(self.request.user.groups.all())
                ).order_by(order_by)

            # Resource Type
            if data.get('resource_type'):
                invoices = invoices.filter(
                    allocation__resources__resource_type=data.get('resource_type')
                )

            # Resource Name
            if data.get('resource_name'):
                invoices = invoices.filter(
                    allocation__resources__in=data.get('resource_name')
                )

            # Start Date
            if data.get('start_date'):
                invoices = invoices.filter(
                    created__gt=data.get('start_date')
                ).order_by('created')

            # End Date
            if data.get('end_date'):
                invoices = invoices.filter(
                    created__lt=data.get('end_date')
                ).order_by('created')

        else:
            if self.request.user.is_superuser:
                invoices = AllocationInvoice.objects.all().order_by(order_by)
            else:
                invoices = AllocationInvoice.objects.filter(
                    allocation__resources__review_groups__in=list(self.request.user.groups.all())
                ).order_by(order_by)

        return invoices

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        allocation_invoice_search_form = AllocationInvoiceSearchForm(self.request.GET)
        if allocation_invoice_search_form.is_valid():
            context['allocation_invoice_search_form'] = allocation_invoice_search_form
            data = allocation_invoice_search_form.cleaned_data
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
        else:
            filter_parameters = ''
            context['allocation_invoice_search_form'] - AllocationInvoiceSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                'order_by={}&direction={}&'.format(order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        allocation_invoice_list = context.get('allocation_invoice_list')
        paginator = Paginator(allocation_invoice_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            allocation_invoice_list = paginator.page(page)
        except PageNotAnInteger:
            allocation_invoice_list = paginator.page(1)
        except EmptyPage:
            allocation_invoice_list = paginator.page(paginator.num_pages)

        if self.request.user.is_superuser:
            resource_objs = Resource.objects.filter(
                requires_payment=True
            )
        else:
            resource_objs = Resource.objects.filter(
                review_groups__in=list(self.request.user.groups.all()),
                requires_payment=True
            )

        resources = []
        for resource in resource_objs:
            resources.append(
                (resource.name, resource.name)
            )

        context['allocation_invoice_export_form'] = AllocationInvoiceExportForm(resources=resources)

        return context


class AllocationAllInvoicesExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_manage_invoice'):
            return True

        messages.error(self.request, 'You do not have permission to download invoices.')

    def post(self, request):
        file_name = request.POST['file_name']
        resource = request.POST['resource']
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']

        initial_data = {
            'file_name': file_name,
            'resource': resource,
            'start_date': start_date,
            'end_date': end_date
        }

        if self.request.user.is_superuser:
            resource_objs = Resource.objects.filter(
                requires_payment=True
            )
        else:
            resource_objs = Resource.objects.filter(
                review_groups__in=list(self.request.user.groups.all()),
                requires_payment=True
            )

        resources = []
        for resource_obj in resource_objs:
            resources.append(
                (resource_obj.name, resource_obj.name)
            )

        form = AllocationInvoiceExportForm(
            request.POST,
            initial=initial_data,
            resources=resources
        )

        if form.is_valid():
            data = form.cleaned_data
            file_name = data.get('file_name')
            resource = data.get('resource')
            start_date = data.get('start_date')
            end_date = data.get('end_date')

            if file_name[-4:] != '.csv':
                file_name += '.csv'

            invoices = AllocationInvoice.objects.filter(
                allocation__resources__review_groups__in=list(request.user.groups.all())
            ).order_by('-created')

            if start_date:
                invoices = invoices.filter(
                    created__gt=start_date
                ).order_by('-created')

            if end_date:
                invoices = invoices.filter(
                    created__lt=end_date
                ).order_by('-created')

            rows = []
            if resource == 'RStudio Connect':
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
                        ' '.join((invoice.allocation.project.pi.first_name, invoice.allocation.project.pi.last_name)),
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
            return HttpResponseRedirect(reverse('allocation-all-invoices-list'))


class AllocationAllInvoicesDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_all_invoices_detail.html'

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
        pk = self.kwargs.get('pk')
        invoice_obj = get_object_or_404(AllocationInvoice, pk=pk)

        context = super().get_context_data(**kwargs)
        context['invoice'] = invoice_obj
        return context


class AllocationAddInvoiceNoteView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = AllocationUserNote
    template_name = 'allocation/allocation_add_invoice_note.html'
    fields = ('is_private', 'note',)

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'can_manage_invoice'
        )
        if group_exists:
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

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'can_manage_invoice'
        )
        if group_exists:
            return True

    def get_success_url(self):
        return reverse_lazy('allocation-invoice-detail', kwargs={'pk': self.object.allocation.pk})


class AllocationDeleteInvoiceNoteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_delete_invoice_note.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'can_manage_invoice'
        )
        if group_exists:
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

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'can_manage_invoice'
        )
        if group_exists:
            return True

        messages.error(self.request, 'You do not have permission to download invoices.')

    def post(self, request):
        file_name = request.POST['file_name']
        resource = request.POST['resource']
        allocation_status = request.POST['allocation_status']
        # start_date = request.POST['start_date']
        # end_date = request.POST['end_date']

        initial_data = {
            'file_name': file_name,
            'resource': resource,
            'allocation_status': allocation_status,
            # 'start_date': start_date,
            # 'end_date': end_date
        }

        if self.request.user.is_superuser:
            resource_objs = Resource.objects.filter(
                requires_payment=True
            )
        else:
            resource_objs = Resource.objects.filter(
                review_groups__in=list(self.request.user.groups.all()),
                requires_payment=True
            )

        resources = []
        for resource_obj in resource_objs:
            resources.append(
                (resource_obj.name, resource_obj.name)
            )
        form = AllocationInvoiceExportForm(
            request.POST,
            initial=initial_data,
            resources=resources
        )

        if form.is_valid():
            data = form.cleaned_data
            file_name = data.get('file_name')
            resource = data.get('resource')
            allocation_status = data.get('allocation_status')
            # start_date = data.get('start_date')
            # end_date = data.get('end_date')

            if file_name[-4:] != ".csv":
                file_name += ".csv"

            invoices = Allocation.objects.prefetch_related('project', 'status').filter(
                Q(status__pk__in=allocation_status) &
                Q(resources__name=resource)
            ).order_by('-created')

            # if start_date:
            #     invoices = invoices.filter(
            #         created__gt=start_date
            #     ).order_by('-created')

            # if end_date:
            #     invoices = invoices.filter(
            #         created__lt=end_date
            #     ).order_by('-created')

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
            elif resource == "Geode-Projects":
                header = [
                    'PI',
                    'Fiscal Officer',
                    'Account Number',
                    'Sub-account Number',
                    'Share Name',
                    'Org',
                    'Quota Data (GiBs)',
                    'Quota Files (M)',
                    'Billing Rate',
                    'Billable Amount Annual',
                    'Billable Amount Monthly',
                    'Billing Start Date',
                    'Billing End Date',
                    'Status'
                ]

                for invoice in invoices:
                    fiscal_officer_user_exists = User.objects.filter(username=invoice.fiscal_officer).exists()
                    fiscal_officer = invoice.fiscal_officer
                    if fiscal_officer_user_exists:
                        fiscal_officer_user_obj = User.objects.get(username=invoice.fiscal_officer)
                        fiscal_officer = ' '.join((fiscal_officer_user_obj.first_name, fiscal_officer_user_obj.last_name))

                    row = [
                        ' '.join((invoice.project.pi.first_name, invoice.project.pi.last_name)),
                        fiscal_officer,
                        invoice.account_number,
                        invoice.sub_account_number,
                        invoice.share_name,
                        invoice.organization,
                        invoice.storage_space,
                        invoice.quota_files,
                        invoice.billing_rate,
                        invoice.billable_amount_annual,
                        invoice.billable_amount_monthly,
                        invoice.billing_start_date,
                        invoice.billing_end_date,
                        invoice.status
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


class AllocationChangeDetailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    formset_class = AllocationAttributeUpdateForm
    template_name = 'allocation/allocation_change_detail.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        allocation_change_obj = get_object_or_404(AllocationChangeRequest, pk=self.kwargs.get('pk'))

        if self.request.user.has_perm('allocation.can_view_all_allocations'):
            return True

        if allocation_change_obj.allocation.has_perm(self.request.user, AllocationPermission.MANAGER, 'view_allocationchangerequest'):
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

        allocation_obj = allocation_change_obj.allocation
        context['user_has_permissions'] = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'view_allocationchangerequest'
        )

        if self.request.user.is_superuser:
            context['user_has_permissions'] = True

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
        if (
            not self.request.user.has_perm('allocation.can_view_all_allocations')
            and not self.request.user.is_superuser
        ):
            allocation_change_form.fields['end_date_extension'].disabled = True

        note_form = AllocationChangeNoteForm(
            initial={'notes': allocation_change_obj.notes})

        context = self.get_context_data()

        context['allocation_change_form'] = allocation_change_form
        context['note_form'] = note_form
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        if not request.user.is_superuser:
            group_exists = check_if_groups_in_review_groups(
                allocation_obj.get_parent_resource.review_groups.all(),
                self.request.user.groups.all(),
                'change_allocationchangerequest'
            )
            if not group_exists:
                messages.error(
                    request,
                    'You do not have permission to manage this allocation change request with this resource.'
                )
                return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': allocation_change_obj.pk}))

        allocation_change_obj = get_object_or_404(
            AllocationChangeRequest, pk=pk)
        allocation_obj = allocation_change_obj.allocation
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

        if not note_form.is_valid():
            allocation_change_form = AllocationChangeForm(
                initial={'justification': allocation_change_obj.justification})
            allocation_change_form.fields['justification'].disabled = True

            context = self.get_context_data()

            context['note_form'] = note_form
            context['allocation_change_form'] = allocation_change_form
            return render(request, self.template_name, context)

        notes = note_form.cleaned_data.get('notes')

        action = request.POST.get('action')
        if action not in ['update', 'approve', 'deny']:
            return HttpResponseBadRequest("Invalid request")

        if action == 'deny':
            create_admin_action(request.user, {'notes': notes}, allocation_obj, allocation_change_obj)
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

            send_allocation_customer_email(allocation_change_obj.allocation,
                                           'Allocation Change Denied',
                                           'email/allocation_change_denied.txt',
                                           domain_url=get_domain_url(self.request))

            logger.info(
                f'Admin {request.user.username} denied a {allocation_obj.get_parent_resource.name} '
                f'allocation change request (allocation pk={allocation_obj.pk})'
            )
            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

        if not allocation_change_form.is_valid():
            for error in allocation_change_form.errors:
                messages.error(request, error)
            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

        allocation_change_obj.notes = notes

        if action == 'update' and allocation_change_obj.status.name != 'Pending':
            allocation_change_obj.save()
            messages.success(request, 'Allocation change request updated!')
            logger.info(
                f'Admin {request.user.username} updated a {allocation_obj.get_parent_resource.name} '
                f'allocation change request (allocation pk={allocation_obj.pk})'
            )
            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))
        
        if allocation_attributes_to_change and not formset.is_valid():
            attribute_errors = ""
            for error in formset.errors:
                if error:
                    attribute_errors += error.get('__all__')
            messages.error(request, attribute_errors)
            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))


        form_data = allocation_change_form.cleaned_data
        end_date_extension = form_data.get('end_date_extension')

        if not allocation_attributes_to_change and end_date_extension == 0:
            messages.error(request, 'You must make a change to the allocation.')
            return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))

        if end_date_extension != allocation_change_obj.end_date_extension:
            create_admin_action(request.user, {'new_value': end_date_extension}, allocation_obj, attribute_change)
            allocation_change_obj.end_date_extension = end_date_extension

        if allocation_attributes_to_change:
            for entry in formset:
                formset_data = entry.cleaned_data
                new_value = formset_data.get('new_value')
                attribute_change = AllocationAttributeChangeRequest.objects.get(
                                            pk=formset_data.get('change_pk'))

                if new_value != attribute_change.new_value:
                    create_admin_action(request.user, {'new_value': new_value}, allocation_obj, attribute_change)
                    attribute_change.new_value = new_value
                    attribute_change.save()


        if action == 'update':
            allocation_change_obj.save()
            messages.success(request, 'Allocation change request updated!')
            logger.info(
                f'Admin {request.user.username} updated a {allocation_obj.get_parent_resource.name} '
                f'allocation change request (allocation pk={allocation_obj.pk})'
            )


        elif action == 'approve':
            allocation_obj = allocation_change_obj.allocation
            allocation_change_status_active_obj = AllocationChangeStatusChoice.objects.get(
                name='Approved')
            allocation_change_obj.status = allocation_change_status_active_obj

            if allocation_change_obj.end_date_extension > 0:
                create_admin_action(
                    request.user,
                    {'end_date_extension': form_data.get('end_date_extension')},
                    allocation_obj,
                    allocation_change_obj
                )
                new_end_date = allocation_change_obj.allocation.end_date + relativedelta(
                    days=allocation_change_obj.end_date_extension)
                allocation_change_obj.allocation.end_date = new_end_date

                allocation_change_obj.allocation.save()

            allocation_change_obj.save()
            if allocation_attributes_to_change:
                attribute_change_list = allocation_change_obj.allocationattributechangerequest_set.all()
                for attribute_change in attribute_change_list:
                    create_admin_action(request.user, {'new_value': attribute_change.new_value}, allocation_obj, attribute_change)
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

            send_allocation_customer_email(allocation_change_obj.allocation,
                                           'Allocation Change Approved',
                                           'email/allocation_change_approved.txt',
                                           domain_url=get_domain_url(self.request))
            
            logger.info(
                f'Admin {request.user.username} approved a {allocation_obj.get_parent_resource.name} '
                f'allocation change request (allocation pk={allocation_obj.pk})'
            )

        return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': pk}))


class AllocationChangeListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_change_list.html'
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.view_allocationchangerequest'):
            return True

        messages.error(
            self.request, 'You do not have permission to review allocation requests.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            allocation_change_list = AllocationChangeRequest.objects.filter(
                status__name__in=['Pending', ]
            )
        else:
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
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.has_perm(self.request.user, AllocationPermission.MANAGER, 'add_allocationchangerequest'):
            return True

        messages.error(self.request, 'You do not have permission to request changes to this allocation.')

        return False

    def dispatch(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.project.needs_review:
            messages.error(
                request, 'You cannot request a change to this allocation because you have to review your project first.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.project.status.name in ['Denied', 'Expired', 'Revoked', ]:
            messages.error(
                request, 'You cannot request a change to an allocation in a project with status "{}".'.format(allocation_obj.project.status.name))
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.is_locked:
            messages.error(
                request, 'You cannot request a change to a locked allocation.')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        if allocation_obj.status.name not in ['Active', 'Billing Information Submitted', 'Renewal Requested', 'Payment Pending', 'Payment Requested', 'Paid']:
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

                if form_data.get('end_date_extension') != 0:
                    change_requested = True

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

                    logger.info(
                        f'User {request.user.username} requested a {allocation_obj.get_parent_resource.name} '
                        f'allocation change (allocation pk={allocation_obj.pk})'
                    )

                    pi_name = '{} {} ({})'.format(allocation_obj.project.pi.first_name,
                                                allocation_obj.project.pi.last_name, allocation_obj.project.pi.username)
                    resource_name = allocation_obj.get_parent_resource
                    domain_url = get_domain_url(self.request)
                    url = '{}{}'.format(domain_url, reverse('allocation-change-list'))

                    project_obj = allocation_obj.project

                    if EMAIL_ENABLED:
                        template_context = {
                            'project_title': project_obj.title,
                            'project_id': project_obj.pk,
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
                attribute_errors = []
                for error in form.errors:
                    messages.error(request, error)
                for error in formset.errors:
                    if error.get('__all__') is not None:
                        attribute_errors.append(error.get('__all__')[0])

                if attribute_errors:
                    messages.error(request,  ', '.join(attribute_errors))
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
                            'project_title': project_obj.title,
                            'project_id': project_obj.pk,
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

        allocation_change_request_obj = get_object_or_404(AllocationChangeRequest, pk=self.kwargs.get('pk'))
        allocation_obj = allocation_change_request_obj.allocation

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'change_allocationchangerequest'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to approve an allocation change request.')

    def get(self, request, pk):
        allocation_change_obj = get_object_or_404(AllocationChangeRequest, pk=pk)

        allocation_change_status_active_obj = AllocationChangeStatusChoice.objects.get(
            name='Approved')

        allocation_change_obj.status = allocation_change_status_active_obj

        if allocation_change_obj.end_date_extension != 0:
            new_end_date = allocation_change_obj.allocation.end_date + relativedelta(
                days=allocation_change_obj.end_date_extension)

            allocation_change_obj.allocation.end_date = new_end_date

        create_admin_action(
            request.user,
            {'status': allocation_change_status_active_obj},
            allocation_change_obj.allocation,
            allocation_change_obj
        )

        allocation_change_obj.allocation.save()
        allocation_change_obj.save()

        attribute_change_list = allocation_change_obj.allocationattributechangerequest_set.all()
        for attribute_change in attribute_change_list:
            attribute_change.allocation_attribute.value = attribute_change.new_value
            attribute_change.allocation_attribute.save()

        # If the resource requires payment set the allocations status to payment pending.
        # allocation_obj = allocation_change_obj.allocation
        # resource_obj = allocation_obj.get_parent_resource
        # print('activated')
        # if resource_obj.requires_payment:
        #     print('requires payment')
        #     if resource_obj.name == 'Slate-Project':
        #         allocation_attribute_obj = AllocationAttribute.get(
        #             allocation_attribute_type__name='Storage Quota(TB)'
        #         )
        #         print('Slate-project')
        #         if allocation_attribute_obj.value > 15:
        #             allocation_obj.status = AllocationStatusChoice.objects.get(
        #                 name='Payment Pending'
        #             )
        #             print('payment pending')

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
                'signature': EMAIL_SIGNATURE
            }

            email_receiver_list = get_allocation_user_emails(allocation_change_obj.allocation)
            send_email_template(
                'Allocation Change Approved',
                'email/allocation_change_approved.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

        logger.info(
            f'Admin {request.user.username} approved a {allocation_change_obj.allocation.get_parent_resource.name} '
            f'allocation change request (allocation pk={allocation_change_obj.allocation.pk})'
        )
        return HttpResponseRedirect(reverse('allocation-change-list'))


class AllocationChangeDenyView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        allocation_change_request_obj = get_object_or_404(AllocationChangeRequest, pk=self.kwargs.get('pk'))
        allocation_obj = allocation_change_request_obj.allocation

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'change_allocationchangerequest'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to deny an allocation change request.')

    def get(self, request, pk):
        allocation_change_obj = get_object_or_404(AllocationChangeRequest, pk=pk)

        allocation_change_status_denied_obj = AllocationChangeStatusChoice.objects.get(
            name='Denied')

        create_admin_action(
            request.user,
            {'status': allocation_change_status_denied_obj},
            allocation_change_obj.allocation,
            allocation_change_obj
        )

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
                'signature': EMAIL_SIGNATURE
            }

            email_receiver_list = get_allocation_user_emails(
                allocation_change_obj.allocation, True
            )
            send_email_template(
                'Allocation Change Denied',
                'email/allocation_change_denied.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

        logger.info(
            f'Admin {request.user.username} denied a {allocation_change_obj.allocation.get_parent_resource.name} '
            f'allocation change request (allocation pk={allocation_change_obj.allocation.pk})'
        )
        return HttpResponseRedirect(reverse('allocation-change-list'))


class AllocationChangeDeleteAttributeView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        """ UserPassesTestMixin Tests"""

        if self.request.user.is_superuser:
            return True

        allocation_attribute_change_obj = get_object_or_404(
            AllocationAttributeChangeRequest,
            pk=self.kwargs.get('pk')
        )
        allocation_obj = allocation_attribute_change_obj.allocation_change_request.allocation
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'delete_allocationattributechangerequest'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to delete an allocation attribute change request.')

    def get(self, request, pk):
        allocation_attribute_change_obj = get_object_or_404(AllocationAttributeChangeRequest, pk=pk)
        allocation_change_pk = allocation_attribute_change_obj.allocation_change_request.pk

        create_admin_action_for_deletion(
            request.user,
            allocation_attribute_change_obj,
            allocation_attribute_change_obj.allocation_change_request.allocation,
            allocation_attribute_change_obj.allocation_change_request
        )

        allocation_attribute_change_obj.delete()

        allocation_pk = allocation_attribute_change_obj.allocation_change_request.allocation.pk
        allocation_resource_name = allocation_attribute_change_obj.allocation_change_request.allocation.get_parent_resource.name
        logger.info(
            f'Admin {request.user.username} deleted a {allocation_resource_name} allocation '
            f'attribute change request (allocation pk={allocation_pk})'
        )
        messages.success(
            request, 'Allocation attribute change request successfully deleted.')
        return HttpResponseRedirect(reverse('allocation-change-detail', kwargs={'pk': allocation_change_pk}))


class AllocationExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_view_all_allocations'):
            return True

        messages.error(self.request, 'You do not have permission to download allocations.')

    def post(self, request):
        file_name = request.POST.get('file_name')
        allocation_creation_range_start = request.POST.get('allocation_creation_range_start')
        allocation_creation_range_stop = request.POST.get('allocation_creation_range_stop')
        allocation_statuses = request.POST.get('allocation_statuses')
        allocation_resources = request.POST.get('allocation_resources')

        initial_data = {
            'file_name': file_name,
            'project_creation_range_start': allocation_creation_range_start,
            'allocation_creation_range_stop': allocation_creation_range_stop,
            'allocation_statuses': allocation_statuses,
            'allocation_resources': allocation_resources
        }

        form = AllocationExportForm(
            request.POST,
            initial=initial_data
        )

        if form.is_valid():
            data = form.cleaned_data
            file_name = data.get('file_name')
            allocation_creation_range_start = data.get('allocation_creation_range_start')
            allocation_creation_range_stop = data.get('allocation_creation_range_stop')
            allocation_statuses = data.get('allocation_statuses')
            allocation_resources = data.get('allocation_resources')

            if file_name[-4:] != ".csv":
                file_name += ".csv"

            if allocation_statuses:
                allocations = Allocation.objects.filter(status__in=allocation_statuses).order_by('created')
            else:
                allocations = Allocation.objects.all().order_by('created')

            if allocation_resources:
                allocations = allocations.filter(resources__in=allocation_resources).order_by('created')

            if allocation_creation_range_start:
                allocations = allocations.filter(
                    created__gte=allocation_creation_range_start
                ).order_by('created')

            if allocation_creation_range_stop:
                allocations = allocations.filter(
                    created__lte=allocation_creation_range_stop
                ).order_by('created')

            rows = []
            header = [
                'Allocation Name',
                'Allocation ID',
                'Allocation Status',
                'Creation Date',
                'Username',
                'Email',
                'Status'
            ]

            for allocation in allocations:
                allocation_users = allocation.allocationuser_set.filter(status__name__in=['Active', 'Inactive', 'Eligible', 'Disabled', 'Retired']).order_by('user__username')

                for allocation_user in allocation_users:
                    row = [
                        allocation.get_parent_resource.name,
                        allocation.pk,
                        allocation.status.name,
                        allocation.created,
                        allocation_user.user.username,
                        allocation_user.user.email,
                        allocation_user.status.name
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

            logger.info(f'Admin {request.user.username} exported the allocation list')

            return response
        else:
            messages.error(
                request,
                'Please correct the errors for the following fields: {}'
                .format(' '.join(form.errors))
            )
            return HttpResponseRedirect(reverse('allocation-list'))


class AllocationUserDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_user_detail.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        if allocation_obj.project.pi == self.request.user:
            return True

        if allocation_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

    def get(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        allocation_user_pk = self.kwargs.get('allocation_user_pk')

        if allocation_obj.allocationuser_set.filter(pk=allocation_user_pk).exists():
            allocation_user_obj = allocation_obj.allocationuser_set.get(
                pk=allocation_user_pk)

            allocation_user_update_form = AllocationUserUpdateForm(
                resource=allocation_obj.get_parent_resource,
                initial={
                    'role': allocation_user_obj.role,
                },
            )

            context = {}
            context['can_update'] = not allocation_obj.project.pi == allocation_user_obj.user
            context['allocation_obj'] = allocation_obj
            context['allocation_user_update_form'] = allocation_user_update_form
            context['allocation_user_obj'] = allocation_user_obj
            context['allocation_user_roles_enabled'] = check_if_roles_are_enabled(allocation_obj)

            return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        project_obj = allocation_obj.project
        allocation_user_pk = self.kwargs.get('allocation_user_pk')

        if allocation_obj.status.name not in ['Active', 'Billing Information Submitted', 'New']:
            messages.error(
                request, f'You cannot update a user in a(n) {allocation_obj.status.name} allocation.'
            )
            return HttpResponseRedirect(
                reverse('allocation-user-detail', kwargs={'pk': allocation_user_pk})
            )

        if allocation_obj.allocationuser_set.filter(id=allocation_user_pk).exists():
            allocation_user_obj = allocation_obj.allocationuser_set.get(
                pk=allocation_user_pk
            )

            if allocation_user_obj.user == allocation_user_obj.allocation.project.pi:
                messages.error(request, 'PI role cannot be changed.')
                return HttpResponseRedirect(
                    reverse(
                        'allocation-user-detail',
                        kwargs={'pk': allocation_obj.pk, 'allocation_user_pk': allocation_user_obj.pk}
                    )
                )

            allocation_user_update_form = AllocationUserUpdateForm(
                request.POST,
                resource=allocation_obj.get_parent_resource,
                initial={
                    'role': allocation_user_obj.role,
                },
            )

            if allocation_user_update_form.is_valid():
                form_data = allocation_user_update_form.cleaned_data
                if allocation_user_obj.role == form_data.get('role'):
                    return HttpResponseRedirect(
                        reverse(
                            'allocation-user-detail',
                            kwargs={
                                'pk': allocation_obj.pk, 'allocation_user_pk': allocation_user_obj.pk
                            }
                        )
                    )
                allocation_user_obj.role = form_data.get('role')
                allocation_user_obj.save()
                allocation_change_user_role.send(
                    sender=self.__class__,
                    allocation_user_pk=allocation_user_obj.pk,
                )

                logger.info(
                    f'User {request.user.username} updated {allocation_user_obj.user.username}\'s '
                    f'role (allocation pk={project_obj.pk})'
                )

                messages.success(request, 'User details updated.')
                return HttpResponseRedirect(
                    reverse(
                        'allocation-user-detail',
                        kwargs={'pk': allocation_obj.pk, 'allocation_user_pk': allocation_user_obj.pk}
                    )
                )
            else:
                messages.error(request, allocation_user_update_form.errors.get('__all__'))
                return HttpResponseRedirect(
                    reverse(
                        'allocation-user-detail',
                        kwargs={'pk': allocation_obj.pk, 'allocation_user_pk': allocation_user_obj.pk}
                    )
                )


class AllocationRemoveView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_remove.html'

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk')
        )

        if allocation_obj.project.pi == user:
            return True

        if allocation_obj.project.projectuser_set.filter(user=user, role__name='Manager', status__name='Active').exists():
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'can_remove_allocation'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to remove this allocation from this project.'
        )

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        allocation_obj = get_object_or_404(
            Allocation, pk=self.kwargs.get('pk')
        )
        # This checks if a string exists, do not set from_project if you want this to be false
        if self.request.GET.get('from_project'):
            project_pk = allocation_obj.project.pk
            http_response_redirect = HttpResponseRedirect(
                reverse('project-detail', kwargs={'pk': project_pk})
            )
        else:
            http_response_redirect = HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            )

        if not allocation_obj.get_parent_resource.requires_payment:
            messages.error(request, 'This allocation cannot be removed')
            return http_response_redirect

        if allocation_obj.status.name not in ['Active', 'Billing Information Submitted', ]:
            messages.error(
                request,
                f'Cannot remove an allocation with status "{allocation_obj.status}"'
            )
            return http_response_redirect

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_obj = Allocation.objects.get(pk=self.kwargs.get('pk'))
        allocation_users = allocation_obj.allocationuser_set.filter(status__name__in=['Active', 'Eligible', 'Disabled', 'Retired'])

        users = []
        for allocation_user in allocation_users:
            users.append(
                f'{allocation_user.user.first_name} {allocation_user.user.last_name} ({allocation_user.user.username})'
            )
        context['from_project'] = False
        # This checks if a string exists, do not set from_project if you want this to be false
        if self.request.GET.get('from_project'):
            context['from_project'] = True
        context['users'] = ', '.join(users)
        context['allocation'] = allocation_obj
        context['is_admin'] = True
        if allocation_obj.project.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            context['is_admin'] = False
        return context

    def post(self, request, *args, **kwargs):
        pk=self.kwargs.get('pk')
        allocation_obj = Allocation.objects.get(pk=pk)
        if allocation_obj.project.projectuser_set.filter(user=request.user, role__name='Manager', status__name='Active').exists():
            new_status = AllocationStatusChoice.objects.get(name='Removal Requested')
            message = 'Allocation removal request sent'
            removal_request_status = AllocationRemovalStatusChoice.objects.get(name='Pending')

        else:
            new_status = AllocationStatusChoice.objects.get(name='Removed')
            allocation_obj.end_date = datetime.date.today()
            message = 'Allocation has been removed'
            removal_request_status = AllocationRemovalStatusChoice.objects.get(name='Approved')

            create_admin_action(
                request.user,
                {'status': new_status},
                allocation_obj
            )

        AllocationRemovalRequest.objects.create(
            project_pi=allocation_obj.project.pi,
            requestor=request.user,
            allocation=allocation_obj,
            allocation_prior_status=allocation_obj.status,
            status=removal_request_status
        )

        allocation_obj.status = new_status
        allocation_obj.save()

        if new_status.name == 'Removed':
            allocation_remove.send(sender=self.__class__, allocation_pk=allocation_obj.pk)
            allocation_users = allocation_obj.allocationuser_set.filter(status__name__in=['Active', 'Inactive', 'Eligible', 'Disabled', 'Retired'])
            for allocation_user in allocation_users:
                allocation_remove_user.send(
                    sender=self.__class__, allocation_user_pk=allocation_user.pk)
            logger.info(
                f'Admin {request.user.username} removed a {allocation_obj.get_parent_resource.name} '
                f'allocation (allocation pk={allocation_obj.pk})'
            )
        else:
            logger.info(
                f'User {request.user.username} sent a removal request for a '
                f'{allocation_obj.get_parent_resource.name} '
                f'allocation (allocation pk={allocation_obj.pk})'
            )

        if EMAIL_ENABLED:
            if new_status.name == 'Removed':
                email_receiver_list = get_allocation_user_emails(allocation_obj)
                resource_name = allocation_obj.get_parent_resource
                domain_url = get_domain_url(self.request)
                allocation_detail_url = reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
                allocation_url = f'{domain_url}{allocation_detail_url}'
                template_context = {
                    'center_name': EMAIL_CENTER_NAME,
                    'resource': resource_name,
                    'allocation_url': allocation_url,
                    'signature': EMAIL_SIGNATURE
                }

                send_email_template(
                    'Allocation Removed',
                    'email/allocation_removed.txt',
                    template_context,
                    EMAIL_TICKET_SYSTEM_ADDRESS,
                    email_receiver_list
                )
            else:
                email_recipient = get_email_recipient_from_groups(
                    allocation_obj.get_parent_resource.review_groups.all()
                )
                resource_name = allocation_obj.get_parent_resource
                domain_url = get_domain_url(self.request)
                allocation_removal_list_url = reverse('allocation-removal-request-list')
                allocation_url = f'{domain_url}{allocation_removal_list_url}'
                project_obj = allocation_obj.project
                template_context = {
                    'project_title': project_obj.title,
                    'project_id': project_obj.pk,
                    'requestor': request.user,
                    'resource': resource_name,
                    'url': allocation_url,
                    'pi': project_obj.pi.username
                }

                send_email_template(
                    'Allocation Removal Request',
                    'email/new_allocation_removal_request.txt',
                    template_context,
                    EMAIL_SENDER,
                    [email_recipient, ]
                )

        messages.success(request, message)

        # Checking if the string exists, do not set from_project if you want this to be false
        from_project = self.request.GET.get('from_project')
        if from_project:
            allocation_obj = Allocation.objects.get(pk=pk)
            project_pk = allocation_obj.project.pk
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_pk}))

        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationRemovalListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_removal_request_list.html'
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.can_review_allocation_requests'):
            return True

        messages.error(
            self.request, 'You do not have permission to view allocation removal requests.'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            allocation_removal_list = AllocationRemovalRequest.objects.filter(
                status__name='Pending'
            )
        else:
            allocation_removal_list = AllocationRemovalRequest.objects.filter(
                status__name='Pending',
                allocation__resources__review_groups__in=list(self.request.user.groups.all())
            )

        context['allocation_removal_list'] = allocation_removal_list
        return context

class AllocationApproveRemovalRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        allocation_removal_obj = get_object_or_404(AllocationRemovalRequest, pk=self.kwargs.get('pk'))
        allocation_obj = allocation_removal_obj.allocation
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'can_remove_allocation'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to approve this allocation removal request.'
        )

    def get(self, request, pk):
        allocation_removal_obj = get_object_or_404(AllocationRemovalRequest, pk=pk)
        allocation_obj = allocation_removal_obj.allocation

        allocation_removal_status_obj = AllocationRemovalStatusChoice.objects.get(name='Approved')
        allocation_status_obj = AllocationStatusChoice.objects.get(name='Removed')
        end_date = datetime.datetime.now()

        create_admin_action(
            request.user,
            {'status': allocation_status_obj},
            allocation_obj
        )

        allocation_removal_obj.status = allocation_removal_status_obj
        allocation_removal_obj.save()

        allocation_obj.status = allocation_status_obj
        allocation_obj.end_date = end_date
        allocation_obj.save()

        allocation_remove.send(sender=self.__class__, allocation_pk=allocation_obj.pk)
        allocation_users = allocation_obj.allocationuser_set.filter(status__name__in=['Active', 'Inactive', 'Eligible', 'Disabled', 'Retired'])
        for allocation_user in allocation_users:
            allocation_remove_user.send(
                sender=self.__class__, allocation_user_pk=allocation_user.pk)

        messages.success(
            request,
            f'Allocation has been removed from project "{allocation_obj.project.title}"'
        )

        if EMAIL_ENABLED:
            email_receiver_list = get_allocation_user_emails(allocation_obj)
            resource_name = allocation_obj.get_parent_resource
            domain_url = get_domain_url(self.request)
            allocation_detail_url = reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            allocation_url = f'{domain_url}{allocation_detail_url}'
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'allocation_url': allocation_url,
                'signature': EMAIL_SIGNATURE
            }

            send_email_template(
                'Allocation Removed',
                'email/allocation_removed.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

        logger.info(
            f'Admin {request.user.username} approved a removal request for a '
            f'{allocation_obj.get_parent_resource.name} allocation (allocation pk={allocation_obj.pk})'
        )
        return HttpResponseRedirect(reverse('allocation-removal-request-list'))


class AllocationDenyRemovalRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        allocation_removal_obj = get_object_or_404(AllocationRemovalRequest, pk=self.kwargs.get('pk'))
        allocation_obj = allocation_removal_obj.allocation
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'can_review_allocation_requests'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to deny this allocation removal request.'
        )

    def get(self, request, pk):
        allocation_removal_obj = get_object_or_404(AllocationRemovalRequest, pk=pk)
        allocation_obj = allocation_removal_obj.allocation

        allocation_removal_status_obj = AllocationRemovalStatusChoice.objects.get(name='Denied')
        allocation_status_obj = AllocationStatusChoice.objects.get(
            name=allocation_removal_obj.allocation_prior_status
        )

        create_admin_action(
            request.user,
            {'status': allocation_status_obj},
            allocation_obj
        )

        allocation_removal_obj.status = allocation_removal_status_obj
        allocation_removal_obj.save()

        allocation_obj.status = allocation_status_obj
        allocation_obj.save()

        messages.success(
            request,
            f'Allocation has not been removed from project "{allocation_obj.project.title}"'
        )

        if EMAIL_ENABLED:
            email_receiver_list = get_allocation_user_emails(allocation_obj, True)
            resource_name = allocation_obj.get_parent_resource
            domain_url = get_domain_url(self.request)
            allocation_detail_url = reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})
            allocation_url = f'{domain_url}{allocation_detail_url}'
            template_context = {
                'center_name': EMAIL_CENTER_NAME,
                'resource': resource_name,
                'allocation_url': allocation_url,
                'signature': EMAIL_SIGNATURE
            }

            send_email_template(
                'Allocation Removal Denied',
                'email/allocation_removal_denied.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

        logger.info(
            f'Admin {request.user.username} denied a removal request for a '
            f'{allocation_obj.get_parent_resource.name} allocation (allocation pk={allocation_obj.pk})'
        )
        return HttpResponseRedirect(reverse('allocation-removal-request-list'))


class AllocationUserRequestListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_user_request_list.html'
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.view_allocationuserrequest'):
            return True

        messages.error(self.request, 'You do not have access to view allocation user requests.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            context['request_list'] = AllocationUserRequest.objects.filter(
                status__name='Pending'
            )
        else:
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

        allocation_user_request_obj = get_object_or_404(AllocationUserRequest, pk=self.kwargs.get('pk'))
        allocation_obj = allocation_user_request_obj.allocation_user.allocation
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'change_allocationuserrequest'
        )
        if group_exists:
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

        create_admin_action(
            request.user,
            {'status': allocation_user_request_status_choice},
            allocation_user.allocation,
            allocation_user_request
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
                'center_name': EMAIL_CENTER_NAME,
                'user': allocation_user.user.username,
                'project': allocation_user.allocation.project.title,
                'allocation': allocation_user.allocation.get_parent_resource,
                'url': url,
                'signature': EMAIL_SIGNATURE
            }

            if action == 'Add':
                email_receiver_list = list(allocation_user.allocation.project.projectuser_set.filter(
                    user__in=[allocation_user.user, allocation_user_request.requestor_user],
                    enable_notifications=True
                ).values_list('user__email', flat=True))
                send_email_template(
                    'Add User Request Approved',
                    'email/add_allocation_user_request_approved.txt',
                    template_context,
                    EMAIL_TICKET_SYSTEM_ADDRESS,
                    email_receiver_list
                )
            else:
                email_receiver_list = list(allocation_user.allocation.project.projectuser_set.filter(
                    user__in=[allocation_user.user, allocation_user_request.requestor_user],
                    enable_notifications=True
                ).values_list('user__email', flat=True))

                send_email_template(
                    'Remove User Request Approved',
                    'email/remove_allocation_user_request_approved.txt',
                    template_context,
                    EMAIL_TICKET_SYSTEM_ADDRESS,
                    email_receiver_list
                )

        logger.info(
            f'Admin {request.user.username} approved a {allocation_user.allocation.get_parent_resource.name} '
            f'allocation user request (allocation pk={allocation_user.allocation.pk})'
        )
        messages.success(request, 'User {}\'s status has been APPROVED'.format(allocation_user.user.username))

        return HttpResponseRedirect(reverse('allocation-user-request-list'))


class AllocationUserDenyRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        allocation_user_request_obj = get_object_or_404(AllocationUserRequest, pk=self.kwargs.get('pk'))
        allocation_obj = allocation_user_request_obj.allocation_user.allocation
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'change_allocationuserrequest'
        )
        if group_exists:
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

        create_admin_action(
            request.user,
            {'status': allocation_user_request_status_choice},
            allocation_user.allocation,
            allocation_user_request
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
                'center_name': EMAIL_CENTER_NAME,
                'user': allocation_user.user.username,
                'project': allocation_user.allocation.project.title,
                'allocation': allocation_user.allocation.get_parent_resource,
                'url': url,
                'signature': EMAIL_SIGNATURE
            }

            if action == 'Add':
                email_receiver_list = [
                    allocation_user_request.requestor_user.email
                ]

                send_email_template(
                    'Add User Request Denied',
                    'email/add_allocation_user_request_denied.txt',
                    template_context,
                    EMAIL_TICKET_SYSTEM_ADDRESS,
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
                    EMAIL_TICKET_SYSTEM_ADDRESS,
                    email_receiver_list
                )

        logger.info(
            f'Admin {request.user.username} denied a {allocation_user.allocation.get_parent_resource.name} '
            f'allocation user request (allocation pk={allocation_user.allocation.pk})'
        )
        messages.success(request, 'User {}\'s status has been DENIED'.format(allocation_user.user.username))

        return HttpResponseRedirect(reverse('allocation-user-request-list'))


class AllocationUserRequestInfoView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation/allocation_user_request_info.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        allocation_user_request_obj = get_object_or_404(AllocationUserRequest, pk=self.kwargs.get('pk'))
        allocation_obj = allocation_user_request_obj.allocation_user.allocation
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'view_allocationuserrequest'
        )
        if group_exists:
            return True

        messages.error(self.request, 'You do not have access to view allocation user request info.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        context['request_info'] = get_object_or_404(AllocationUserRequest, pk=pk)

        return context