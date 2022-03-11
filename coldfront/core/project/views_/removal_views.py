from itertools import chain

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import ListView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from coldfront.core.allocation.models import (Allocation,
                                              AllocationAttributeType,
                                              AllocationUserStatusChoice)

from coldfront.core.project.forms_.removal_forms import \
    (ProjectRemovalRequestSearchForm,
     ProjectRemovalRequestUpdateStatusForm,
     ProjectRemovalRequestCompletionForm)
from coldfront.core.project.models import (Project,
                                           ProjectUserStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserRemovalRequestStatusChoice)
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestRunner
from coldfront.core.utils.common import (import_from_settings,
                                         utc_now_offset_aware)
from coldfront.core.utils.mail import send_email_template

import logging

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)

if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    SUPPORT_EMAIL = import_from_settings('CENTER_HELP_EMAIL')

logger = logging.getLogger(__name__)


class ProjectRemoveUsersView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'project/project_removal/project_remove_users.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        if project_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You cannot remove users from an archived project.')
            return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': project_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_remove(self, project_obj):

        num_managers = project_obj.projectuser_set.filter(
            role__name='Manager',
            status__name='Active').count()

        if num_managers > 1:
            query_set = project_obj.projectuser_set.filter(
                status__name='Active').exclude(
                role__name='Principal Investigator').order_by(
                'user__username')
        else:
            query_set = project_obj.projectuser_set.filter(
                status__name='Active').exclude(
                role__name__in=['Principal Investigator', 'Manager']).order_by(
                'user__username')

        users_to_remove = [

            {'username': ele.user.username,
             'first_name': ele.user.first_name,
             'last_name': ele.user.last_name,
             'email': ele.user.email,
             'role': ele.role,
             'status': ele.status.name}

            for ele in query_set if ele.user != self.request.user
        ]

        users_pending_removal = [

            ele

            for ele in project_obj.projectuser_set.filter(
                status__name='Pending - Remove').exclude(
                role__name='Principal Investigator').order_by(
                'user__username')
        ]

        return users_to_remove, users_pending_removal

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        users_to_remove_list, users_pending_removal = self.get_users_to_remove(project_obj)
        context = {}
        context['project'] = get_object_or_404(Project, pk=pk)
        context['users_pending_removal'] = users_pending_removal

        page = request.GET.get('page', 1)

        paginator = Paginator(users_to_remove_list, 25)
        try:
            users_to_remove = paginator.page(page)
        except PageNotAnInteger:
            users_to_remove = paginator.page(1)
        except EmptyPage:
            users_to_remove = paginator.page(paginator.num_pages)

        context['users_to_remove'] = users_to_remove

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)
        user_obj = User.objects.get(
            username=self.request.POST['username'])

        try:
            request_runner = ProjectRemovalRequestRunner(
                self.request.user, user_obj, project_obj)
            runner_result = request_runner.run()
            success_messages, error_messages = request_runner.get_messages()

            if runner_result:
                request_runner.send_emails()
                for m in success_messages:
                    messages.success(request, m)
            else:
                for m in error_messages:
                    messages.error(request, m)

        except Exception as e:
            logger.exception(e)
            error_message = \
                'Unexpected error. Please contact an administrator.'
            messages.error(self.request, error_message)

        return HttpResponseRedirect(reverse('project-detail', kwargs={'pk': pk}))


class ProjectRemoveSelf(LoginRequiredMixin, UserPassesTestMixin, TemplateView):

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name='User',
                status__name='Active').exists():
            return True

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name='Manager',
                status__name='Active').exists() and \
                len(project_obj.projectuser_set.filter(role__name='Manager')) > 1:
            return True

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        project_obj = get_object_or_404(Project, pk=pk)

        try:
            request_runner = ProjectRemovalRequestRunner(
                self.request.user, self.request.user, project_obj)
            runner_result = request_runner.run()
            success_messages, error_messages = request_runner.get_messages()

            if runner_result:
                request_runner.send_emails()
                for message in success_messages:
                    messages.success(request, message)
            else:
                for message in error_messages:
                    messages.error(request, message)
        except Exception as e:
            logger.exception(e)
            error_message = \
                'Unexpected error. Please contact an administrator.'
            messages.error(self.request, error_message)

        return HttpResponseRedirect(reverse('home'))


class ProjectRemovalRequestListView(LoginRequiredMixin,
                                    UserPassesTestMixin,
                                    ListView):
    template_name = 'project/project_removal/project_removal_request_list.html'
    login_url = '/'
    completed = False
    paginate_by = 30
    context_object_name = "project_removal_request_list"

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
            order_by = 'id'

        project_removal_status_complete, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name='Complete')

        project_removal_status_pending, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name='Pending')

        project_removal_status_processing, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name='Processing')

        project_removal_status_not_complete = [project_removal_status_pending,
                                               project_removal_status_processing]

        removal_request_search_form = ProjectRemovalRequestSearchForm(self.request.GET)

        if self.completed:
            project_removal_request_list = ProjectUserRemovalRequest.objects.filter(
                status=project_removal_status_complete)
        else:
            project_removal_request_list = ProjectUserRemovalRequest.objects.filter(
                status__in=project_removal_status_not_complete)

        if removal_request_search_form.is_valid():
            data = removal_request_search_form.cleaned_data

            if data.get('username'):
                project_removal_request_list = \
                    project_removal_request_list.filter(
                        project_user__user__username__icontains=data.get(
                            'username'))

            if data.get('email'):
                project_removal_request_list = \
                    project_removal_request_list.filter(
                        project_user__user__email__icontains=data.get(
                            'email'))

            if data.get('project_name'):
                project_removal_request_list = \
                    project_removal_request_list.filter(
                        project_user__project__name__icontains=data.get(
                            'project_name'))

            if data.get('requester'):
                project_removal_request_list = \
                    project_removal_request_list.filter(
                        requester__user__username__icontains=data.get(
                            'username'))

        return project_removal_request_list.order_by(order_by)

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.view_projectuserremovalrequest'):
            return True

        message = (
            'You do not have permission to review project removal requests.')
        messages.error(self.request, message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        removal_request_search_form = ProjectRemovalRequestSearchForm(self.request.GET)
        if removal_request_search_form.is_valid():
            context['removal_request_search_form'] = removal_request_search_form
            data = removal_request_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['removal_request_search_form'] = removal_request_search_form
        else:
            filter_parameters = None
            context['removal_request_search_form'] = ProjectRemovalRequestSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = "toggle"

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = filter_parameters_with_order_by

        context['request_filter'] = (
            'completed' if self.completed else 'pending')
        removal_request_list = self.get_queryset()

        paginator = Paginator(removal_request_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            removal_requests = paginator.page(page)
        except PageNotAnInteger:
            removal_requests = paginator.page(1)
        except EmptyPage:
            removal_requests = paginator.page(paginator.num_pages)

        context['removal_request_list'] = removal_requests

        context['actions_visible'] = not self.completed

        return context


class ProjectRemovalRequestUpdateStatusView(LoginRequiredMixin,
                                            UserPassesTestMixin, FormView):
    form_class = ProjectRemovalRequestUpdateStatusForm
    login_url = '/'
    template_name = \
        'project/project_removal/project_removal_request_update_status.html'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to update project removal requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.project_removal_request_obj = get_object_or_404(
            ProjectUserRemovalRequest, pk=self.kwargs.get('pk'))
        self.user_obj = self.project_removal_request_obj.project_user.user
        status = self.project_removal_request_obj.status.name
        if status != 'Pending':
            message = f'Project removal request has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('project-removal-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data.get('status')

        project_removal_status_choice, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name=status)
        self.project_removal_request_obj.status = project_removal_status_choice
        self.project_removal_request_obj.save()

        message = (
            f'Project removal request initiated by '
            f'{self.project_removal_request_obj.requester.username} for User '
            f'{self.user_obj.username} under '
            f'Project {self.project_removal_request_obj.project_user.project.name} '
            f'has been marked as {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_removal_request'] = self.project_removal_request_obj
        return context

    def get_initial(self):
        initial = {
            'status': self.project_removal_request_obj.status.name,
        }
        return initial

    def get_success_url(self):
        return reverse('project-removal-request-list')


class ProjectRemovalRequestCompleteStatusView(LoginRequiredMixin,
                                              UserPassesTestMixin,
                                              FormView):
    form_class = ProjectRemovalRequestCompletionForm
    login_url = '/'
    template_name = \
        'project/project_removal/project_removal_request_complete_status.html'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to update project removal requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.project_removal_request_obj = get_object_or_404(
            ProjectUserRemovalRequest, pk=self.kwargs.get('pk'))
        self.user_obj = self.project_removal_request_obj.project_user.user
        status = self.project_removal_request_obj.status.name
        if status != 'Processing':
            message = f'Project removal request has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('project-removal-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data.get('status')

        project_removal_status_choice, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name=status)

        project_obj = self.project_removal_request_obj.project_user.project
        removed_user = self.project_removal_request_obj.project_user
        requester = self.project_removal_request_obj.requester

        self.project_removal_request_obj.status = project_removal_status_choice
        if status == 'Complete':
            self.project_removal_request_obj.completion_time = utc_now_offset_aware()

        self.project_removal_request_obj.save()

        if status == 'Complete':
            project_user_status_removed, _ = \
                ProjectUserStatusChoice.objects.get_or_create(
                    name='Removed')
            removed_user.status = project_user_status_removed
            removed_user.save()

            try:
                allocation_obj = Allocation.objects.get(project=project_obj)
                allocation_user = \
                    allocation_obj.allocationuser_set.get(user=removed_user.user)
                allocation_user_status_choice_removed = \
                    AllocationUserStatusChoice.objects.get(name='Removed')
                allocation_user.status = allocation_user_status_choice_removed
                allocation_user.save()

                cluster_account_status = \
                    allocation_user.allocationuserattribute_set.get(
                        allocation_attribute_type=AllocationAttributeType.objects.get(
                            name='Cluster Account Status'))
                cluster_account_status.value = 'Denied'
                cluster_account_status.save()

            except Exception as e:
                message = f'Unexpected error setting AllocationAttributeType' \
                          f'Cluster Account Status to "Denied" and ' \
                          f'AllocationUserStatusChoice to "Removed" ' \
                          f'for user {removed_user.user.username}.'
                messages.error(self.request, message)

        message = (
            f'Project removal request initiated by '
            f'{self.project_removal_request_obj.requester.username} for User '
            f'{self.user_obj.username} under '
            f'Project {self.project_removal_request_obj.project_user.project.name} '
            f'has been marked as {status}.')
        messages.success(self.request, message)

        if EMAIL_ENABLED and status == 'Complete':
            pi_condition = Q(
                role__name='Principal Investigator', status__name='Active',
                enable_notifications=True)
            manager_condition = Q(role__name='Manager', status__name='Active')
            manager_pi_queryset = project_obj.projectuser_set.filter(
                pi_condition | manager_condition)

            for proj_user in list(chain(manager_pi_queryset, [removed_user])):
                curr_user = proj_user.user
                template_context = {
                    'user_first_name': curr_user.first_name,
                    'user_last_name': curr_user.last_name,
                    'removed_user_first_name': removed_user.user.first_name,
                    'removed_user_last_name': removed_user.user.last_name,
                    'requester_first_name': requester.first_name,
                    'requester_last_name': requester.last_name,
                    'project_name': project_obj.name,
                    'signature': EMAIL_SIGNATURE,
                    'support_email': SUPPORT_EMAIL,
                }

                send_email_template(
                    'Project Removal Request Completed',
                    'email/project_removal/project_removal_complete.txt',
                    template_context,
                    EMAIL_SENDER,
                    [curr_user.email]
                )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project_removal_request'] = self.project_removal_request_obj
        return context

    def get_initial(self):
        initial = {
            'status': self.project_removal_request_obj.status.name,
        }
        return initial

    def get_success_url(self):
        return reverse('project-removal-request-list')