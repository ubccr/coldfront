import logging
import datetime

from django.urls import reverse
from django.contrib import messages
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect

from coldfront.core.utils.groups import check_if_groups_in_review_groups
from coldfront.core.utils.mail import send_allocation_customer_email, send_allocation_admin_email
from coldfront.core.allocation.utils import create_admin_action
from coldfront.core.allocation.models import Allocation, AllocationStatusChoice, AllocationPermission
from coldfront.core.allocation.signals import allocation_remove_user
from coldfront.plugins.allocation_removal_requests.signals import allocation_remove
from coldfront.plugins.allocation_removal_requests.models import AllocationRemovalRequest, AllocationRemovalStatusChoice

logger = logging.getLogger(__name__)


class AllocationRemovalRequestView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation_removal_requests/allocation_remove.html'

    def test_func(self):
        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.has_perm(self.request.user, AllocationPermission.MANAGER):
            return True

        messages.error(
            self.request, 'You do not have permission to remove this allocation from this project.')
        return False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.status.name not in ['Active', 'Billing Information Submitted', ]:
            messages.error(
                request, f'Cannot remove an allocation with status "{allocation_obj.status}"')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_obj = Allocation.objects.get(pk=self.kwargs.get('pk'))
        allocation_users = allocation_obj.allocationuser_set.filter(status__name__in=['Active', 'Invited', 'Disabled', 'Retired'])

        users = []
        for allocation_user in allocation_users:
            users.append(
                f'{allocation_user.user.first_name} {allocation_user.user.last_name} ({allocation_user.user.username})')

        context['users'] = ', '.join(users)
        context['allocation'] = allocation_obj
        context['is_admin'] = False
        return context

    def post(self, request, *args, **kwargs):
        pk=self.kwargs.get('pk')
        allocation_obj = Allocation.objects.get(pk=pk)

        AllocationRemovalRequest.objects.create(
            project_pi=allocation_obj.project.pi,
            requestor=request.user,
            allocation=allocation_obj,
            allocation_prior_status=allocation_obj.status,
            status=AllocationRemovalStatusChoice.objects.get(name='Pending')
        )

        allocation_obj.status = AllocationStatusChoice.objects.get(name='Removal Requested')
        allocation_obj.save()

        logger.info(
            f'User {request.user.username} sent a removal request for a '
            f'{allocation_obj.get_parent_resource.name} '
            f'allocation (allocation pk={allocation_obj.pk})'
        )

        send_allocation_admin_email(
            allocation_obj,
            'Allocation Removal Request',
            'allocation_removal_requests/new_allocation_removal_request.txt',
            url_path=reverse('allocation_removal_requests:allocation-removal-request-list'),
            addtl_context={
                'requestor': self.request.user,
                'project': allocation_obj.project
            }
        )

        messages.success(request, 'Allocation removal request sent')
        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationRemoveView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation_removal_requests/allocation_remove.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        group_exists = check_if_groups_in_review_groups(
            allocation_obj.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'add_allocationremovalrequest'
        )
        if group_exists:
            return True
        messages.error(
            self.request, 'You do not have permission to remove this allocation from this project.')

        return False

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        allocation_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        if allocation_obj.status.name not in ['Active', 'Billing Information Submitted', 'Removal Requested']:
            messages.error(
                request, f'Cannot remove an allocation with status "{allocation_obj.status}"')
            return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation_obj = Allocation.objects.get(pk=self.kwargs.get('pk'))
        allocation_users = allocation_obj.allocationuser_set.filter(status__name__in=['Active', 'Invited', 'Disabled', 'Retired'])

        users = []
        for allocation_user in allocation_users:
            users.append(
                f'{allocation_user.user.first_name} {allocation_user.user.last_name} ({allocation_user.user.username})')

        context['users'] = ', '.join(users)
        context['allocation'] = allocation_obj
        context['is_admin'] = True
        context['attributes'] = allocation_obj.allocationattribute_set.filter(allocation_attribute_type__is_private=False)
        return context

    def post(self, request, *args, **kwargs):
        pk=self.kwargs.get('pk')
        allocation_obj = Allocation.objects.get(pk=pk)
        new_status = AllocationStatusChoice.objects.get(name='Removed')
        allocation_obj.end_date = datetime.date.today()
        message = 'Allocation has been removed'
        removal_request_status = AllocationRemovalStatusChoice.objects.get(name='Approved')

        AllocationRemovalRequest.objects.create(
            project_pi=allocation_obj.project.pi,
            requestor=request.user,
            allocation=allocation_obj,
            allocation_prior_status=allocation_obj.status,
            status=removal_request_status
        )

        allocation_obj.status = new_status
        allocation_obj.save()

        allocation_remove.send(sender=self.__class__, allocation_pk=allocation_obj.pk)
        allocation_users = allocation_obj.allocationuser_set.filter(status__name__in=['Active', 'Inactive', 'Invited', 'Disabled', 'Retired'])
        for allocation_user in allocation_users:
            allocation_remove_user.send(
                sender=self.__class__, allocation_user_pk=allocation_user.pk)

        create_admin_action(request.user, {'status': new_status}, allocation_obj)
        logger.info(
            f'Admin {request.user.username} removed a {allocation_obj.get_parent_resource.name} '
            f'allocation (allocation pk={allocation_obj.pk})'
        )

        send_allocation_customer_email(
            allocation_obj,
            'Allocation Removed',
            'allocation_removal_requests/allocation_removed.txt',
            addtl_context={'resource': allocation_obj.get_parent_resource}
        )

        messages.success(request, message)
        return HttpResponseRedirect(reverse('allocation-detail', kwargs={'pk': pk}))


class AllocationRemovalListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'allocation_removal_requests/allocation_removal_request_list.html'
    login_url = '/'

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation_removal_requests.view_allocationremovalrequest'):
            return True

        messages.error(
            self.request, 'You do not have permission to view allocation removal requests.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            allocation_removal_list = AllocationRemovalRequest.objects.filter(
                status__name='Pending')
        else:
            allocation_removal_list = AllocationRemovalRequest.objects.filter(
                status__name='Pending',
                allocation__resources__review_groups__in=list(self.request.user.groups.all()))

        context['allocation_removal_list'] = allocation_removal_list
        return context

class AllocationApproveRemovalRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        allocation_removal_obj = get_object_or_404(AllocationRemovalRequest, pk=self.kwargs.get('pk'))
        if self.request.user.is_superuser:
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_removal_obj.allocation.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'change_allocationremovalrequest'
        )
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to approve this allocation removal request.')

        return False

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
        allocation_users = allocation_obj.allocationuser_set.filter(status__name__in=['Active', 'Inactive', 'Invited', 'Disabled', 'Retired'])
        for allocation_user in allocation_users:
            allocation_remove_user.send(
                sender=self.__class__, allocation_user_pk=allocation_user.pk)

        messages.success(
            request, f'Allocation has been removed from project "{allocation_obj.project.title}"')

        send_allocation_customer_email(
            allocation_obj,
            'Allocation Removal Approved',
            'allocation_removal_requests/allocation_removed.txt',
            addtl_context={'resource': allocation_obj.get_parent_resource}
        )

        logger.info(
            f'Admin {request.user.username} approved a removal request for a '
            f'{allocation_obj.get_parent_resource.name} allocation (allocation pk={allocation_obj.pk})'
        )
        return HttpResponseRedirect(reverse('allocation_removal_requests:allocation-removal-request-list'))


class AllocationDenyRemovalRequestView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = '/'

    def test_func(self):
        allocation_removal_obj = get_object_or_404(AllocationRemovalRequest, pk=self.kwargs.get('pk'))
        if self.request.user.is_superuser:
            return True

        group_exists = check_if_groups_in_review_groups(
            allocation_removal_obj.allocation.get_parent_resource.review_groups.all(),
            self.request.user.groups.all(),
            'change_allocationremovalrequest'
        )
        print(group_exists)
        if group_exists:
            return True

        messages.error(
            self.request, 'You do not have permission to deny this allocation removal request.')

    def get(self, request, pk):
        allocation_removal_obj = get_object_or_404(AllocationRemovalRequest, pk=pk)
        allocation_obj = allocation_removal_obj.allocation

        allocation_removal_status_obj = AllocationRemovalStatusChoice.objects.get(name='Denied')
        allocation_status_obj = AllocationStatusChoice.objects.get(
            name=allocation_removal_obj.allocation_prior_status)

        create_admin_action(
            request.user, {'status': allocation_status_obj}, allocation_obj)

        allocation_removal_obj.status = allocation_removal_status_obj
        allocation_removal_obj._change_reason = 'Denied an allocation removal request'
        allocation_removal_obj.save()

        allocation_obj.status = allocation_status_obj
        allocation_obj.save()

        messages.success(
            request, f'Allocation has not been removed from project "{allocation_obj.project.title}"')

        send_allocation_customer_email(
            allocation_obj,
            'Allocation Removal Denied',
            'allocation_removal_requests/allocation_removal_denied.txt',
            addtl_context={'resource': allocation_obj.get_parent_resource}
        )

        logger.info(
            f'Admin {request.user.username} denied a removal request for a '
            f'{allocation_obj.get_parent_resource.name} allocation (allocation pk={allocation_obj.pk})'
        )
        return HttpResponseRedirect(reverse('allocation_removal_requests:allocation-removal-request-list'))
