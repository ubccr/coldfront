import logging
import urllib

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, FormView, View
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.contrib.auth.models import User

from coldfront.core.allocation.models import (Allocation,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationAttribute,
                                              AllocationUserStatusChoice,
                                              AllocationUser)
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.plugins.customizable_forms.forms import GenericForm
from coldfront.core.allocation.utils import (set_default_allocation_user_role,
                                             send_allocation_user_request_email,
                                             send_added_user_email)
from coldfront.core.resource.models import ResourceAttribute
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.slack import send_message
from coldfront.core.utils.mail import send_email_template, get_email_recipient_from_groups
from coldfront.plugins.ldap_user_info.utils import get_user_info


ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT = import_from_settings(
    'ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT', True
)
ALLOCATION_ACCOUNT_ENABLED = import_from_settings('ALLOCATION_ACCOUNT_ENABLED', False)
ALLOCATION_ACCOUNT_MAPPING = import_from_settings('ALLOCATION_ACCOUNT_MAPPING', {})
SLACK_MESSAGING_ENABLED = import_from_settings('SLACK_MESSAGING_ENABLED', False)
INVOICE_ENABLED = import_from_settings('INVOICE_ENABLED', False)
if INVOICE_ENABLED:
    INVOICE_DEFAULT_STATUS = import_from_settings('INVOICE_DEFAULT_STATUS', 'Pending Payment')
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')

logger = logging.getLogger(__name__)


class AllocationResourceSelectionView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'customizable_forms/resource_selection.html'

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

        messages.error(self.request, 'You do not have permission to create a new allocation.')

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.needs_review:
            messages.error(
                request, 'You cannot request a new allocation because you have to review your project first.'
            )
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
            Project, pk=self.kwargs.get('project_pk')
        )
        project_allocations = project_obj.allocation_set.filter(
            status__name__in=[
                'Active',
                'New',
                'Renewal Requested',
                'Billing Information Submitted',
                'Paid',
                'Payment Pending',
                'Payment Requested'
            ]
        )
        project_resource_count = {}
        for project_allocation in project_allocations:
            resource_name = project_allocation.get_parent_resource.name
            if project_resource_count.get(resource_name) is None:
                project_resource_count[resource_name] = 0
            project_resource_count[resource_name] += 1

        resource_objs = Resource.objects.filter(
            is_allocatable=True
        ).prefetch_related('resource_type', 'resourceattribute_set').order_by('resource_type')
        accounts = get_user_info(self.request.user.username, ['memberOf']).get('memberOf')
        resource_categories = {}
        for resource_obj in resource_objs:
            resource_type_name = resource_obj.resource_type.name
            if not resource_categories.get(resource_type_name):
                resource_categories[resource_type_name] = {'allocated': set(), 'resources': []}

            limit_reached = False
            limit_objs = resource_obj.resourceattribute_set.filter(resource_attribute_type__name='allocation_limit')
            count = project_resource_count.get(resource_obj.name)
            if count is not None:
                resource_categories[resource_type_name]['allocated'].add(resource_obj.name)
                if limit_objs.exists() and count >= int(limit_objs[0].value):
                    limit_reached = True

            help_url = resource_obj.resourceattribute_set.filter(resource_attribute_type__name='help_url')
            if help_url.exists():
                help_url = help_url[0].value
            else:
                help_url = None

            has_account = True
            if not resource_obj.check_user_account_exists(self.request.user.username, accounts):
                has_account = False

            pi_request_only = resource_obj.resourceattribute_set.filter(resource_attribute_type__name='pi_request_only')
            if not pi_request_only.exists() or self.request.user.is_superuser:
                can_request = True
            else:
                can_request = True
                if pi_request_only[0].value.lower() == 'true' and project_obj.pi != self.request.user:
                    can_request = False

            resource_categories[resource_type_name]['resources'].append(
                {
                    'resource': resource_obj,
                    'info_link': help_url,
                    'limit_reached': limit_reached,
                    'has_account': has_account,
                    'can_request': can_request 
                }
            )

        after_project_creation = self.request.GET.get('after_project_creation')
        if after_project_creation is None:
            after_project_creation = 'false'
        context['after_project_creation'] = after_project_creation
        context['resource_types'] = resource_categories
        context['project_obj'] = project_obj

        return context


class DispatchView(LoginRequiredMixin, View):
    def dispatch(self, request, project_pk, resource_pk, *args, **kwargs):
        resource_obj = get_object_or_404(Resource, pk=resource_pk)
        resource_name = resource_obj.name
        resource_name = ''.join(resource_name.lower().split(' '))
        return HttpResponseRedirect(
            self.reverse_with_params(
                reverse(
                    'resource-form',
                    kwargs={'project_pk': project_pk, 'resource_pk': resource_pk, 'resource_name': resource_name}
                ),
                after_project_creation = self.request.GET.get('after_project_creation')
            )
        )

    def reverse_with_params(self, path, **kwargs):
        return path + '?' + urllib.parse.urlencode(kwargs)


class GenericView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'customizable_forms/generic.html'
    form_class = GenericForm

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.pi == self.request.user:
            return True

        if project_obj.projectuser_set.filter(user=self.request.user, role__name='Manager', status__name='Active').exists():
            return True

        messages.error(self.request, 'You do not have permission to create a new allocation.')

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))

        if project_obj.needs_review:
            messages.error(
                request, 'You cannot request a new allocation because you have to review your project first.'
            )
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))

        if project_obj.status.name in ['Archived', 'Denied', 'Review Pending', 'Expired', ]:
            messages.error(
                request,
                'You cannot request a new allocation for a project with status "{}".'.format(project_obj.status.name)
            )
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        
        resource_obj = get_object_or_404(Resource, pk=self.kwargs.get('resource_pk'))
        allocation_limit_objs = resource_obj.resourceattribute_set.filter(
            resource_attribute_type__name='allocation_limit'
        )
        if allocation_limit_objs.exists():
            allocation_limit = int(allocation_limit_objs[0].value)
            allocation_count = project_obj.allocation_set.filter(
                resources=resource_obj,
                status__name__in=[
                    'Active',
                    'New',
                    'Renewal Requested',
                    'Billing Information Submitted',
                    'Paid',
                    'Payment Pending',
                    'Payment Requested'
                ]
            ).count()
            if allocation_count >= allocation_limit:
                messages.error(
                    request,
                    'Your project is at the allocation limit allowed for this resource.'
                )
                return HttpResponseRedirect(reverse('custom-allocation-create', kwargs={'project_pk': project_obj.pk}))
            
        pi_request_only = resource_obj.resourceattribute_set.filter(resource_attribute_type__name='pi_request_only')
        if not pi_request_only.exists() or self.request.user.is_superuser:
            can_request = True
        else:
            can_request = True
            if pi_request_only[0].value.lower() == 'true' and project_obj.pi != self.request.user:
                can_request = False
        if not can_request:
            messages.error(
                request,
                'Only the PI can request a new allocation for this resource.'
            )
            return HttpResponseRedirect(reverse('custom-allocation-create', kwargs={'project_pk': project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        resource_obj = get_object_or_404(Resource, pk=self.kwargs.get('resource_pk'))
        context["project_obj"] = project_obj
        context["resource_obj"] = resource_obj

        after_project_creation = self.request.GET.get('after_project_creation')
        if after_project_creation is None:
            after_project_creation = 'false'
        context['after_project_creation'] = after_project_creation

        return context

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
            
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        resource_obj = get_object_or_404(Resource, pk=self.kwargs.get('resource_pk'))
        resource_attributes = ResourceAttribute.objects.filter(resource__pk=self.kwargs.get('resource_pk'))
        return form_class(self.request.user, resource_attributes, project_obj, resource_obj, **self.get_form_kwargs())

    def add_allocation_attributes(self, resource_obj, form_data, allocation_obj):
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
                if value is not None and value is not '':
                    if type(value) == list:
                        value = ','.join(value)
                    AllocationAttribute.objects.create(
                        allocation_attribute_type=allocation_attribute_type_obj,
                        allocation=allocation_obj,
                        value=value
                    )

    def add_users(self, users, allocation_obj, resource_obj):
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

        return new_user_requests

    def send_messages(self, allocation_obj, project_obj, users, new_user_requests):
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

        return users

    def form_valid(self, form):
        form_data = form.cleaned_data
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('project_pk'))
        resource_obj =  get_object_or_404(Resource, pk=self.kwargs.get('resource_pk'))
        allocation_account = form_data.get('allocation_account', None)

        start_date = form_data.get('start_date', None)
        end_date = form_data.get('end_date', None)

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

        if INVOICE_ENABLED and resource_obj.requires_payment:
            allocation_status_obj = AllocationStatusChoice.objects.get(
                name=INVOICE_DEFAULT_STATUS)
        else:
            allocation_status_obj = AllocationStatusChoice.objects.get(
                name='New')

        allocation_obj = Allocation.objects.create(
            project=project_obj,
            status=allocation_status_obj,
            start_date=start_date,
            end_date=end_date
        )

        if ALLOCATION_ENABLE_CHANGE_REQUESTS_BY_DEFAULT:
            allocation_obj.is_changeable = True
            allocation_obj.save()

        allocation_obj.resources.add(resource_obj)

        self.add_allocation_attributes(resource_obj, form_data, allocation_obj)

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
        new_user_requests = self.add_users(users, allocation_obj, resource_obj)

        users = self.send_messages(allocation_obj, project_obj, users, new_user_requests)

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

        self.allocation_obj = allocation_obj
        return super().form_valid(form)

    def reverse_with_params(self, path, **kwargs):
        return path + '?' + urllib.parse.urlencode(kwargs)

    def get_success_url(self):
        after_project_creation = self.request.GET.get('after_project_creation')
        if after_project_creation is None or after_project_creation == 'false':
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
