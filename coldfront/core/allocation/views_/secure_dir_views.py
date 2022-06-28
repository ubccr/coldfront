import logging
from urllib.parse import urljoin

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import IntegrityError
from django.db.models import Q
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, FormView, DetailView
from django.views.generic.base import TemplateView, View
from formtools.wizard.views import SessionWizardView
from iso8601 import iso8601

from coldfront.core.allocation.forms_.secure_dir_forms import (
    SecureDirManageUsersForm,
    SecureDirManageUsersSearchForm,
    SecureDirManageUsersRequestUpdateStatusForm,
    SecureDirManageUsersRequestCompletionForm, SecureDirDataDescriptionForm,
    SecureDirRDMConsultationForm, SecureDirExistingPIForm,
    SecureDirExistingProjectForm, SecureDirReviewStatusForm,
    SecureDirRequestReviewDenyForm, SecureDirDirectoryNamesForm)
from coldfront.core.allocation.models import (Allocation,
                                              SecureDirAddUserRequest,
                                              SecureDirRemoveUserRequest,
                                              AllocationUserStatusChoice,
                                              AllocationUser,
                                              SecureDirRequestStatusChoice,
                                              SecureDirRequest)
from coldfront.core.allocation.utils import has_cluster_access
from coldfront.core.allocation.utils_.secure_dir_utils import \
    get_secure_dir_manage_user_request_objects, secure_dir_request_state_status, \
    SecureDirRequestDenialRunner, SecureDirRequestApprovalRunner, \
    get_secure_dir_allocations
from coldfront.core.project.models import ProjectUser
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware, \
    session_wizard_all_form_data
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)


class SecureDirManageUsersView(LoginRequiredMixin,
                               UserPassesTestMixin,
                               TemplateView):
    template_name = 'secure_dir/secure_dir_manage_users.html'

    def test_func(self):
        """ UserPassesTestMixin Tests"""
        if self.request.user.is_superuser:
            return True

        alloc_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))

        if alloc_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name='Principal Investigator',
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        alloc_obj = get_object_or_404(Allocation, pk=self.kwargs.get('pk'))
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.directory = \
            alloc_obj.allocationattribute_set.get(
                allocation_attribute_type__name='Cluster Directory Access').value

        if alloc_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, f'You can only {self.language_dict["verb"]} users '
                         f'{self.language_dict["preposition"]} an '
                         f'active allocation.')
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': alloc_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_add(self, alloc_obj):
        # Users in any projects that the PI runs should be available to add.
        alloc_pis = [proj_user.user for proj_user in
                     alloc_obj.project.projectuser_set.filter(
                         Q(role__name__in=['Manager',
                                           'Principal Investigator']) &
                         Q(status__name='Active'))]

        projects = [proj_user.project for proj_user in
                    ProjectUser.objects.filter(
                        Q(role__name__in=['Manager',
                                          'Principal Investigator']) &
                        Q(status__name='Active') &
                        Q(user__in=alloc_pis))]

        # Users must have active cluster access to be added.
        users_to_add = set([proj_user.user for proj_user in
                            ProjectUser.objects.filter(project__in=projects,
                                                       status__name='Active')
                            if has_cluster_access(proj_user.user)])

        # Excluding active users that are already part of the allocation.
        users_to_exclude = set(alloc_user.user for alloc_user in
                               alloc_obj.allocationuser_set.filter(
                                   status__name='Active'))

        # Excluding users that have active join requests.
        users_to_exclude |= \
            set(request.user for request in
                SecureDirAddUserRequest.objects.filter(
                    allocation=alloc_obj,
                    status__name__in=['Pending',
                                      'Processing']))

        # Excluding users that have active removal requests.
        users_to_exclude |= \
            set(request.user for request in
                SecureDirRemoveUserRequest.objects.filter(
                    allocation=alloc_obj,
                    status__name__in=['Pending',
                                      'Processing']))

        users_to_add -= users_to_exclude

        user_data_list = []
        for user in users_to_add:
            user_data = {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
            user_data_list.append(user_data)

        return user_data_list

    def get_users_to_remove(self, alloc_obj):
        users_to_remove = set(alloc_user.user for alloc_user in
                              alloc_obj.allocationuser_set.filter(
                                  status__name='Active'))

        # Exclude users that have active removal requests.
        users_to_remove -= set(request.user for request in
                               SecureDirRemoveUserRequest.objects.filter(
                                   allocation=alloc_obj,
                                   status__name__in=['Pending',
                                                     'Processing']))

        # PIs cannot request to remove themselves from their
        # own secure directories.
        users_to_remove -= set(proj_user.user for proj_user in
                               alloc_obj.project.projectuser_set.filter(
                                   role__name='Principal Investigator',
                                   status__name='Active'))

        user_data_list = []
        for user in users_to_remove:
            user_data = {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            }
            user_data_list.append(user_data)

        return user_data_list

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        alloc_obj = get_object_or_404(Allocation, pk=pk)

        if self.add_bool:
            user_list = self.get_users_to_add(alloc_obj)
        else:
            user_list = self.get_users_to_remove(alloc_obj)

        context = {}

        if user_list:
            formset = formset_factory(
                SecureDirManageUsersForm, max_num=len(user_list))
            formset = formset(initial=user_list, prefix='userform')
            context['formset'] = formset

        context['allocation'] = alloc_obj

        context['can_manage_users'] = False
        if self.request.user.is_superuser:
            context['can_manage_users'] = True

        if alloc_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name='Principal Investigator',
                status__name='Active').exists():
            context['can_manage_users'] = True

        context['directory'] = self.directory

        context['action'] = self.action
        context['url'] = f'secure-dir-manage-users'

        context['button'] = 'btn-success' if self.add_bool else 'btn-danger'

        context['preposition'] = self.language_dict['preposition']

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        alloc_obj = get_object_or_404(Allocation, pk=pk)

        allowed_to_manage_users = False
        if alloc_obj.project.projectuser_set.filter(
                user=self.request.user,
                role__name='Principal Investigator',
                status__name='Active').exists():
            allowed_to_manage_users = True

        if self.request.user.is_superuser:
            allowed_to_manage_users = True

        if not allowed_to_manage_users:
            message = 'You do not have permission to view the this page.'
            messages.error(request, message)

            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': pk}))

        if self.add_bool:
            user_list = self.get_users_to_add(alloc_obj)
        else:
            user_list = self.get_users_to_remove(alloc_obj)

        formset = formset_factory(
            SecureDirManageUsersForm, max_num=len(user_list))
        formset = formset(
            request.POST, initial=user_list, prefix='userform')

        reviewed_users_count = 0
        if formset.is_valid():
            pending_status = \
                self.request_status_obj.objects.get(name__icontains='Pending')

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    reviewed_users_count += 1
                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

                    # Create the request object
                    self.request_obj.objects.create(
                        user=user_obj,
                        allocation=alloc_obj,
                        status=pending_status,
                        directory=self.directory
                    )

            # Email admins that there are new request(s)
            if settings.EMAIL_ENABLED:
                context = {
                    'noun': self.language_dict['noun'],
                    'verb': 'are' if reviewed_users_count > 1 else 'is',
                    'plural': 's' if reviewed_users_count > 1 else '',
                    'determiner': 'these' if reviewed_users_count > 1 else 'this',
                    'num_requests': reviewed_users_count,
                    'project_name': alloc_obj.project.name,
                    'directory_name': self.directory,
                    'review_url': 'secure-dir-manage-users-request-list',
                    'action': self.action
                }

                try:
                    subject = f'Pending Secure Directory '\
                              f'{self.language_dict["noun"]} Requests'
                    plain_template = 'email/secure_dir_request/'\
                                     'pending_secure_dir_manage_' \
                                     'user_requests.txt'
                    html_template = 'email/secure_dir_request/' \
                                    'pending_secure_dir_manage_' \
                                    'user_requests.html'
                    send_email_template(subject,
                                        plain_template,
                                        context,
                                        settings.EMAIL_SENDER,
                                        settings.EMAIL_ADMIN_LIST,
                                        html_template=html_template)

                except Exception as e:
                    message = f'Failed to send notification email.'
                    messages.error(request, message)
                    logger.error(message)
                    logger.exception(e)

            message = (
                f'Successfully requested to {self.action} '
                f'{reviewed_users_count} user'
                f'{"s" if reviewed_users_count > 1 else ""} '
                f'{self.language_dict["preposition"]} the secure '
                f'directory {self.directory}. BRC staff have '
                f'been notified.')
            messages.success(request, message)

        else:
            for error in formset.errors:
                messages.error(request, error)

        return HttpResponseRedirect(
            reverse('allocation-detail', kwargs={'pk': pk}))


class SecureDirManageUsersRequestListView(LoginRequiredMixin,
                                          UserPassesTestMixin,
                                          ListView):
    template_name = 'secure_dir/secure_dir_manage_user_request_list.html'
    paginate_by = 30

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.view_securediradduserrequest') and \
                self.request.user.has_perm('allocation.view_securedirremoveuserrequest'):
            return True

        message = (
            f'You do not have permission to review secure directory '
            f'{self.action} user requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.status = self.kwargs.get('status')
        self.completed = self.status == 'completed'
        return super().dispatch(request, *args, **kwargs)

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

        pending_status = self.request_status_obj.objects.filter(
            Q(name__icontains='Pending') | Q(name__icontains='Processing'))

        complete_status = self.request_status_obj.objects.filter(
            name__in=['Complete', 'Denied'])

        secure_dir_request_search_form = \
            SecureDirManageUsersSearchForm(self.request.GET)

        if self.completed:
            request_list = self.request_obj.objects.filter(
                status__in=complete_status)
        else:
            request_list = self.request_obj.objects.filter(
                status__in=pending_status)

        if secure_dir_request_search_form.is_valid():
            data = secure_dir_request_search_form.cleaned_data

            if data.get('username'):
                request_list = request_list.filter(
                    user__username__icontains=data.get('username'))

            if data.get('email'):
                request_list = request_list.filter(
                    user__email__icontains=data.get('email'))

            if data.get('project_name'):
                request_list = \
                    request_list.filter(
                        allocation__project__name__icontains=data.get(
                            'project_name'))

            if data.get('directory_name'):
                request_list = \
                    request_list.filter(
                        directory__icontains=data.get(
                            'directory_name'))

        return request_list.order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        secure_dir_request_search_form = \
            SecureDirManageUsersSearchForm(self.request.GET)
        if secure_dir_request_search_form.is_valid():
            data = secure_dir_request_search_form.cleaned_data
            filter_parameters = ''
            for key, value in data.items():
                if value:
                    if isinstance(value, list):
                        for ele in value:
                            filter_parameters += '{}={}&'.format(key, ele)
                    else:
                        filter_parameters += '{}={}&'.format(key, value)
            context['secure_dir_request_search_form'] = \
                secure_dir_request_search_form
        else:
            filter_parameters = None
            context['secure_dir_request_search_form'] = \
                SecureDirManageUsersSearchForm()

        order_by = self.request.GET.get('order_by')
        if order_by:
            direction = self.request.GET.get('direction')
            filter_parameters_with_order_by = filter_parameters + \
                                              'order_by=%s&direction=%s&' % (
                                                  order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        if filter_parameters:
            context['expand_accordion'] = 'show'
        else:
            context['expand_accordion'] = 'toggle'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = \
            filter_parameters_with_order_by

        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        request_list = self.get_queryset()
        paginator = Paginator(request_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            request_list = paginator.page(page)
        except PageNotAnInteger:
            request_list = paginator.page(1)
        except EmptyPage:
            request_list = paginator.page(paginator.num_pages)

        context['request_list'] = request_list

        context['actions_visible'] = not self.completed

        context['action'] = self.action

        context['preposition'] = self.language_dict['preposition']

        return context


class SecureDirManageUsersUpdateStatusView(LoginRequiredMixin,
                                           UserPassesTestMixin,
                                           FormView):
    form_class = SecureDirManageUsersRequestUpdateStatusForm
    template_name = \
        'secure_dir/secure_dir_manage_user_request_update_status.html'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.change_securediradduserrequest') or \
                self.request.user.has_perm(
                    'allocation.change_securedirremoveuserrequest'):
            return True

        message = (
            'You do not have permission to update secure directory '
            'join or removal requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.secure_dir_request = get_object_or_404(
            self.request_obj, pk=self.kwargs.get('pk'))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cur_status = self.secure_dir_request.status.name
        if 'Pending' not in cur_status:
            message = f'Secure directory user {self.language_dict["noun"]} ' \
                      f'request has unexpected status "{cur_status}."'
            messages.error(self.request, message)
            return HttpResponseRedirect(
                reverse('secure-dir-manage-users-request-list',
                        kwargs={'action': self.action, 'status': 'pending'}))

        form_data = form.cleaned_data
        status = form_data.get('status')

        secure_dir_status_choice = \
            self.request_status_obj.objects.filter(
                name__icontains=status).first()
        self.secure_dir_request.status = secure_dir_status_choice
        self.secure_dir_request.save()

        message = (
            f'Secure directory {self.language_dict["noun"]} request for user '
            f'{self.secure_dir_request.user.username} for '
            f'{self.secure_dir_request.directory} has been '
            f'marked as "{status}".')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request'] = self.secure_dir_request
        context['action'] = self.action
        context['noun'] = self.language_dict['noun']
        context['step'] = 'pending'
        return context

    def get_initial(self):
        initial = {
            'status': self.secure_dir_request.status.name,
        }
        return initial

    def get_success_url(self):
        return reverse('secure-dir-manage-users-request-list',
                       kwargs={'action': self.action, 'status': 'pending'})


class SecureDirManageUsersCompleteStatusView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             FormView):
    form_class = SecureDirManageUsersRequestCompletionForm
    template_name = \
        'secure_dir/secure_dir_manage_user_request_update_status.html'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm(
                'allocation.change_securediradduserrequest') or \
                self.request.user.has_perm(
                    'allocation.change_securedirremoveuserrequest'):
            return True

        message = (
            'You do not have permission to update secure directory '
            'join or removal requests.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.secure_dir_request = get_object_or_404(
            self.request_obj, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        cur_status = self.secure_dir_request.status.name
        if 'Processing' not in cur_status:
            message = f'Secure directory user {self.language_dict["noun"]} ' \
                      f'request has unexpected status "{cur_status}."'
            messages.error(self.request, message)
            return HttpResponseRedirect(
                reverse(f'secure-dir-manage-users-request-list',
                        kwargs={'action': self.action, 'status': 'pending'}))

        form_data = form.cleaned_data
        status = form_data.get('status')
        complete = 'Complete' in status

        secure_dir_status_choice = \
            self.request_status_obj.objects.filter(
                name__icontains=status).first()
        self.secure_dir_request.status = secure_dir_status_choice
        if complete:
            self.secure_dir_request.completion_time = utc_now_offset_aware()
        self.secure_dir_request.save()

        if complete:
            # Creates an allocation user with an active status is the request
            # was an addition request.
            alloc_user, created = \
                AllocationUser.objects.get_or_create(
                    allocation=self.secure_dir_request.allocation,
                    user=self.secure_dir_request.user,
                    status=AllocationUserStatusChoice.objects.get(name='Active')
                )

            # Sets the allocation user status to removed if the request
            # was a removal request.
            if not self.add_bool:
                alloc_user.status = \
                    AllocationUserStatusChoice.objects.get(name='Removed')
                alloc_user.save()

            # Send notification email to PIs and the user that the
            # request has been completed.
            pis = self.secure_dir_request.allocation.project.projectuser_set.filter(
                role__name='Principal Investigator',
                status__name='Active',
                enable_notifications=True)
            users_to_notify = [x.user for x in pis]
            users_to_notify.append(self.secure_dir_request.user)

            for user in users_to_notify:
                try:
                    context = {
                        'user_first_name': user.first_name,
                        'user_last_name': user.last_name,
                        'managed_user_first_name':
                            self.secure_dir_request.user.first_name,
                        'managed_user_last_name':
                            self.secure_dir_request.user.last_name,
                        'managed_user_username':
                            self.secure_dir_request.user.username,
                        'verb': self.language_dict['verb'],
                        'preposition': self.language_dict['preposition'],
                        'directory': self.secure_dir_request.directory,
                        'removed': 'now' if self.add_bool else 'no longer',
                        'signature': settings.EMAIL_SIGNATURE,
                        'support_email': settings.CENTER_HELP_EMAIL,
                    }

                    send_email_template(
                        f'Secure Directory '
                        f'{self.language_dict["noun"].title()} '
                        f'Request Complete',
                        f'email/secure_dir_request/'
                        f'secure_dir_manage_user_request_complete.txt',
                        context,
                        settings.EMAIL_SENDER,
                        [user.email])

                except Exception as e:
                    message = f'Failed to send notification email.'
                    messages.error(self.request, message)
                    logger.error(message)
                    logger.exception(e)

        message = (
            f'Secure directory {self.language_dict["noun"]} request for user '
            f'{self.secure_dir_request.user.username} for '
            f'{self.secure_dir_request.directory} has been marked '
            f'as "{status}".')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request'] = self.secure_dir_request
        context['action'] = self.action
        context['noun'] = self.language_dict['noun']
        context['step'] = 'processing'
        return context

    def get_initial(self):
        initial = {
            'status': self.secure_dir_request.status.name,
        }
        return initial

    def get_success_url(self):
        return reverse(f'secure-dir-manage-users-request-list',
                       kwargs={'action': self.action, 'status': 'pending'})


class SecureDirManageUsersDenyRequestView(LoginRequiredMixin,
                                          UserPassesTestMixin,
                                          View):
    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to deny a secure directory join or '
            'removal request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        get_secure_dir_manage_user_request_objects(self,
                                                   self.kwargs.get('action'))
        self.secure_dir_request = get_object_or_404(
            self.request_obj, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        status = self.secure_dir_request.status.name
        if ('Processing' not in status) and ('Pending' not in status):
            message = f'Secure directory user {self.language_dict["noun"]} ' \
                      f'request has unexpected status "{status}."'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse(f'secure-dir-manage-users-request-list',
                        kwargs={'action': self.action, 'status': 'pending'}))

        reason = self.request.POST['reason']
        self.secure_dir_request.status = \
            self.request_status_obj.objects.get(name='Denied')
        self.secure_dir_request.completion_time = utc_now_offset_aware()
        self.secure_dir_request.save()

        message = (
            f'Secure directory {self.language_dict["noun"]} request for user '
            f'{self.secure_dir_request.user.username} for the secure directory '
            f'{self.secure_dir_request.directory} has been '
            f'denied.')
        messages.success(request, message)

        if settings.EMAIL_ENABLED:
            # Send notification email to PIs and the user that the
            # request has been denied.
            pis = \
                self.secure_dir_request.allocation.project. \
                    projectuser_set.filter(
                    role__name='Principal Investigator',
                    status__name='Active',
                    enable_notifications=True)
            users_to_notify = [x.user for x in pis]
            users_to_notify.append(self.secure_dir_request.user)

            for user in users_to_notify:
                try:
                    context = {
                        'user_first_name': user.first_name,
                        'user_last_name': user.last_name,
                        'managed_user_first_name':
                            self.secure_dir_request.user.first_name,
                        'managed_user_last_name':
                            self.secure_dir_request.user.last_name,
                        'managed_user_username':
                            self.secure_dir_request.user.username,
                        'verb': self.language_dict['verb'],
                        'preposition': self.language_dict['preposition'],
                        'directory': self.secure_dir_request.directory,
                        'reason': reason,
                        'signature': settings.EMAIL_SIGNATURE,
                        'support_email': settings.CENTER_HELP_EMAIL,
                    }

                    send_email_template(
                        f'Secure Directory '
                        f'{self.language_dict["noun"].title()} Request Denied',
                        f'email/secure_dir_request/'
                        f'secure_dir_manage_user_request_denied.txt',
                        context,
                        settings.EMAIL_SENDER,
                        [user.email])

                except Exception as e:
                    message = 'Failed to send notification email.'
                    messages.error(self.request, message)
                    logger.error(message)
                    logger.exception(e)

        return HttpResponseRedirect(
            reverse(f'secure-dir-manage-users-request-list',
                    kwargs={'action': self.action, 'status': 'pending'}))


class SecureDirRequestWizard(LoginRequiredMixin,
                             UserPassesTestMixin,
                             SessionWizardView):

    FORMS = [
        ('data_description', SecureDirDataDescriptionForm),
        ('rdm_consultation', SecureDirRDMConsultationForm),
        ('existing_pi', SecureDirExistingPIForm),
        ('existing_project', SecureDirExistingProjectForm),
        ('directory_name', SecureDirDirectoryNamesForm)
    ]

    TEMPLATES = {
        'data_description':
            'secure_dir/secure_dir_request/data_description.html',
        'rdm_consultation':
            'secure_dir/secure_dir_request/rdm_consultation.html',
        'existing_pi':
            'secure_dir/secure_dir_request/existing_pi.html',
        'existing_project':
            'secure_dir/secure_dir_request/existing_project.html',
        'directory_name':
            'secure_dir/secure_dir_request/directory_name.html'
    }

    form_list = [
        SecureDirDataDescriptionForm,
        SecureDirRDMConsultationForm,
        SecureDirExistingPIForm,
        SecureDirExistingProjectForm,
        SecureDirDirectoryNamesForm
    ]

    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define a lookup table from form name to step number.
        self.step_numbers_by_form_name = {
            name: i for i, (name, _) in enumerate(self.FORMS)}

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)

        eligible_project = Q(project__name__startswith='fc_') | \
                           Q(project__name__startswith='ic_') | \
                           Q(project__name__startswith='co_') & \
                           Q(project__status__name='Active')

        eligible_pi = ProjectUser.objects.filter(
            eligible_project,
            user=self.request.user,
            role__name='Principal Investigator',
            status__name='Active',
        ).exists()

        if eligible_pi and signed_date is not None:
            return True

        message = (
            'You must sign the User Access Agreement before you can request a '
            'new secure directory.')
        messages.error(self.request, message)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self.__set_data_from_previous_steps(current_step, context)
        return context

    def get_form_kwargs(self, step=None):
        kwargs = {}
        step = int(step)
        # The names of steps that require the past data.
        step_names = [
            'rdm_consultation',
            'existing_pi',
            'existing_project'
        ]
        step_numbers = [
            self.step_numbers_by_form_name[name] for name in step_names]
        if step in step_numbers:
            self.__set_data_from_previous_steps(step, kwargs)
        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def done(self, form_list, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = '/'
        try:
            form_data = session_wizard_all_form_data(
                form_list, kwargs['form_dict'], len(self.form_list))

            request_kwargs = {
                'requester': self.request.user,
            }

            data_description = self.__get_data_description(form_data)
            rdm_consultation = self.__get_rdm_consultation(form_data)
            pi = self.__handle_pi_data(form_data)
            existing_project = self.__get_existing_project(form_data)
            directory_name = self.__get_directory_name(form_data)

            # Store transformed form data in a request.
            request_kwargs['data_description'] = data_description
            request_kwargs['rdm_consultation'] = rdm_consultation
            request_kwargs['pi'] = pi
            request_kwargs['project'] = existing_project
            request_kwargs['directory_name'] = directory_name
            request_kwargs['status'] = \
                SecureDirRequestStatusChoice.objects.get(
                    name='Under Review')
            request_kwargs['request_time'] = utc_now_offset_aware()

            # Check that the project does not have an existing Secure
            # Directory or Secure Directory Request.
            sec_dir_allocations = \
                get_secure_dir_allocations().filter(project=existing_project)
            sec_dir_requests = \
                SecureDirRequest.objects.\
                    filter(project=existing_project).\
                    exclude(status__name='Denied')

            if sec_dir_allocations.exists() or sec_dir_requests.exists():
                message = f'The project {existing_project.name} already has ' \
                          f'a secure directory associated with it.'
                messages.error(self.request, message)
                return HttpResponseRedirect(redirect_url)

            request = SecureDirRequest.objects.create(
                **request_kwargs)

            # Send a notification email to admins.
            if settings.EMAIL_ENABLED:
                try:
                    self.send_admin_notification_email(request)
                except Exception as e:
                    self.logger.error(
                        'Failed to send notification email. Details:\n')
                    self.logger.exception(e)
                # Send a notification email to the PI if the requester differs.
                if request.requester != request.pi:
                    try:
                        self.send_pi_notification_email(request)
                    except Exception as e:
                        self.logger.error(
                            'Failed to send notification email. Details:\n')
                        self.logger.exception(e)

        except Exception as e:
            self.logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return HttpResponseRedirect(redirect_url)

    @staticmethod
    def condition_dict():
        view = SecureDirRequestWizard
        return {
            '1': view.show_rdm_consultation_form_condition
        }

    def show_rdm_consultation_form_condition(self):
        step_name = 'data_description'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        return cleaned_data.get('rdm_consultation', False)

    def __get_data_description(self, form_data):
        """Return the data description the user submitted."""
        step_number = self.step_numbers_by_form_name['data_description']
        data = form_data[step_number]
        return data.get('data_description')

    def __get_rdm_consultation(self, form_data):
        """Return the consultants the user spoke to."""
        step_number = self.step_numbers_by_form_name['rdm_consultation']
        data = form_data[step_number]
        return data.get('rdm_consultants', None)

    def __get_directory_name(self, form_data):
        """Return the name of the directory."""
        step_number = self.step_numbers_by_form_name['directory_name']
        data = form_data[step_number]
        return data.get('directory_name', None)

    def __handle_pi_data(self, form_data):
        """Return the requested PI."""
        step_number = self.step_numbers_by_form_name['existing_pi']
        data = form_data[step_number]
        return data.get('PI', None)

    def __get_existing_project(self, form_data):
        """Return the project the user selected."""
        step_number = self.step_numbers_by_form_name['existing_project']
        data = form_data[step_number]
        return data.get('project', None)

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        rdm_consultation_step = \
            self.step_numbers_by_form_name['rdm_consultation']
        if step > rdm_consultation_step:
            rdm_consultation_form_data = self.get_cleaned_data_for_step(
                str(rdm_consultation_step))
            dictionary.update({'breadcrumb_rdm_consultation':
                                   'Yes' if rdm_consultation_form_data
                                   else 'No'})

        existing_pi_step = self.step_numbers_by_form_name['existing_pi']
        if step > existing_pi_step:
            existing_pi_form_data = self.get_cleaned_data_for_step(
                str(existing_pi_step))
            if existing_pi_form_data:
                if existing_pi_form_data['PI'] is not None:
                    pi = existing_pi_form_data['PI']
                    dictionary.update({
                        'breadcrumb_pi': (
                            f'PI: {pi.first_name} {pi.last_name} '
                            f'({pi.email})')
                    })

        existing_project_step = \
            self.step_numbers_by_form_name['existing_project']
        if step > existing_project_step:
            existing_project_form_data = self.get_cleaned_data_for_step(
                str(existing_project_step))
            if existing_project_form_data:
                project = existing_project_form_data['project']

                dictionary.update({'breadcrumb_project':
                                       f'Project: {project.name}'})

    def send_admin_notification_email(self, request):
        requester = request.requester
        requester_str = (
            f'{requester.first_name} {requester.last_name} ({requester.email})')

        pi = request.pi
        pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

        review_url = urljoin(
            settings.CENTER_BASE_URL,
            reverse('secure-dir-request-detail', kwargs={'pk': request.pk}))

        context = {
            'project_name': request.project.name,
            'requester_str': requester_str,
            'pi_str': pi_str,
            'review_url': review_url,
        }

        send_email_template(
            f'New Secure Directory Request',
            'email/secure_dir_request/secure_dir_new_request_admin.txt',
            context,
            settings.EMAIL_SENDER,
            settings.EMAIL_ADMIN_LIST)

    def send_pi_notification_email(self, request):
        requester = request.requester
        requester_str = (
            f'{requester.first_name} {requester.last_name} ({requester.email})')

        pi = request.pi
        pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

        review_url = urljoin(
            settings.CENTER_BASE_URL,
            reverse('secure-dir-request-detail', kwargs={'pk': request.pk}))

        context = {
            'project_name': request.project.name,
            'requester_str': requester_str,
            'pi_str': pi_str,
            'review_url': review_url,
        }

        send_email_template(
            f'New Secure Directory Request',
            'email/secure_dir_request/secure_dir_new_request_pi.txt',
            context,
            settings.EMAIL_SENDER,
            [pi.email])


class SecureDirRequestListView(LoginRequiredMixin,
                               UserPassesTestMixin,
                               TemplateView):

    template_name = 'secure_dir/secure_dir_request/secure_dir_request_list.html'
    login_url = '/'
    # Show completed requests if True; else, show pending requests.
    completed = False

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.view_securedirrequest'):
            return True

        message = (
            'You do not have permission to view the previous page.')
        messages.error(self.request, message)

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

        return SecureDirRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests."""
        context = super().get_context_data(**kwargs)
        kwargs = {}

        request_list = self.get_queryset()

        if self.completed:
            status__name__in = [
                'Approved - Complete', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']

        kwargs['status__name__in'] = status__name__in
        context['secure_dir_request_list'] = request_list.filter(**kwargs)

        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class SecureDirRequestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_obj = None

    def redirect_if_disallowed_status(self, http_request,
                                      disallowed_status_names=(
                                              'Approved - Complete',
                                              'Denied')):
        """Return a redirect response to the detail view for this
        project request if its status has one of the given disallowed
        names, after sending a message to the user. Otherwise, return
        None."""
        if not isinstance(self.request_obj, SecureDirRequest):
            raise TypeError(
                f'Request object has unexpected type '
                f'{type(self.request_obj)}.')
        status_name = self.request_obj.status.name
        if status_name in disallowed_status_names:
            message = (
                f'You cannot perform this action on a request with status '
                f'{status_name}.')
            messages.error(http_request, message)
            return HttpResponseRedirect(
                self.request_detail_url(self.request_obj.pk))
        return None

    @staticmethod
    def request_detail_url(pk):
        """Return the URL to the detail view for the request with the
        given primary key."""
        return reverse('secure-dir-request-detail', kwargs={'pk': pk})

    def set_request_obj(self, pk):
        """Set this instance's request_obj to be the SecureDirRequest with
        the given primary key."""
        self.request_obj = get_object_or_404(SecureDirRequest, pk=pk)


class SecureDirRequestDetailView(LoginRequiredMixin,
                                 UserPassesTestMixin,
                                 SecureDirRequestMixin,
                                 DetailView):
    model = SecureDirRequest
    template_name = 'secure_dir/secure_dir_request/secure_dir_request_detail.html'
    login_url = '/'
    context_object_name = 'secure_dir_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    redirect = reverse_lazy('secure-dir-pending-request-list')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('allocation.view_securedirrequest'):
            return True

        pis = self.request_obj.project.projectuser_set.filter(
            role__name='Principal Investigator',
            status__name='Active').values_list('user__pk', flat=True)
        if self.request.user.pk in pis:
            return True

        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            latest_update_timestamp = \
                self.request_obj.latest_update_timestamp()
            if not latest_update_timestamp:
                latest_update_timestamp = 'No updates yet.'
            else:
                # TODO: Upgrade to Python 3.7+ to use this.
                # latest_update_timestamp = datetime.datetime.fromisoformat(
                #     latest_update_timestamp)
                latest_update_timestamp = iso8601.parse_date(
                    latest_update_timestamp)
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        if self.request_obj.status.name == 'Denied':
            try:
                denial_reason = self.request_obj.denial_reason()
                category = denial_reason.category
                justification = denial_reason.justification
                timestamp = denial_reason.timestamp
            except Exception as e:
                self.logger.exception(e)
                messages.error(self.request, self.error_message)
                category = 'Unknown Category'
                justification = (
                    'Failed to determine denial reason. Please contact an '
                    'administrator.')
                timestamp = 'Unknown Timestamp'
            context['denial_reason'] = {
                'category': category,
                'justification': justification,
                'timestamp': timestamp,
            }
            context['support_email'] = settings.CENTER_HELP_EMAIL

        context['setup_status'] = self.get_setup_status()
        context['is_checklist_complete'] = self.is_checklist_complete()

        context['is_allowed_to_manage_request'] = \
            self.request.user.is_superuser

        return context

    def post(self, request, *args, **kwargs):
        """Approve the request."""
        if not self.request.user.is_superuser:
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('secure-dir-request-detail', kwargs={'pk': pk}))

        if not self.is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('secure-dir-request-detail', kwargs={'pk': pk}))

        # Check that the project does not have any Secure Directories yet.
        sec_dir_allocations = get_secure_dir_allocations()
        if sec_dir_allocations.filter(project=self.request_obj.project).exists():
            message = f'The project {self.request_obj.project.name} already ' \
                      f'has a secure directory associated with it.'
            messages.error(self.request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('secure-dir-request-detail', kwargs={'pk': pk}))

        # Approve the request and send emails to the PI and requester.
        runner = SecureDirRequestApprovalRunner(self.request_obj)
        runner.run()

        message = f'The secure directory for {self.request_obj.project.name} ' \
                  f'was successfully created.'
        messages.success(request, message)

        return HttpResponseRedirect(self.redirect)

    def get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        state = self.request_obj.state
        if (state['rdm_consultation']['status'] == 'Denied' or
                state['mou']['status'] == 'Denied'):
            return 'N/A'
        return state['setup']['status']

    def is_checklist_complete(self):
        status_choice = secure_dir_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Completed')


class SecureDirRequestReviewRDMConsultView(LoginRequiredMixin,
                                           UserPassesTestMixin,
                                           SecureDirRequestMixin,
                                           FormView):
    form_class = SecureDirReviewStatusForm
    template_name = (
        'secure_dir/secure_dir_request/secure_dir_mou.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk=pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['rdm_consultation'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = secure_dir_request_state_status(self.request_obj)
        self.request_obj.save()

        if status == 'Denied':
            runner = SecureDirRequestDenialRunner(self.request_obj)
            runner.run()

        message = (
            f'RDM consultation status for {self.request_obj.project.name}\'s '
            f'secure directory request has been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secure_dir_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        rdm_consultation = self.request_obj.state['rdm_consultation']
        initial['status'] = rdm_consultation['status']
        initial['justification'] = rdm_consultation['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'secure-dir-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SecureDirRequestReviewMOUView(LoginRequiredMixin,
                                    UserPassesTestMixin,
                                    SecureDirRequestMixin,
                                    FormView):
    form_class = SecureDirReviewStatusForm
    template_name = (
        'secure_dir/secure_dir_request/secure_dir_mou.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk=pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['mou'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = secure_dir_request_state_status(self.request_obj)
        self.request_obj.save()

        if status == 'Denied':
            runner = SecureDirRequestDenialRunner(self.request_obj)
            runner.run()

        message = (
            f'MOU status for the secure directory request of project '
            f'{self.request_obj.project.pk} has been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secure_dir_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        mou = self.request_obj.state['mou']
        initial['status'] = mou['status']
        initial['justification'] = mou['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'secure-dir-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SecureDirRequestReviewSetupView(LoginRequiredMixin,
                                      UserPassesTestMixin,
                                      SecureDirRequestMixin,
                                      FormView):
    form_class = SecureDirReviewStatusForm
    template_name = (
        'secure_dir/secure_dir_request/secure_dir_setup.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk=pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['setup'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = secure_dir_request_state_status(self.request_obj)
        self.request_obj.save()

        if status == 'Denied':
            runner = SecureDirRequestDenialRunner(self.request_obj)
            runner.run()

        message = (
            f'Setup status for {self.request_obj.project.name}\'s '
            f'secure directory request has been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secure_dir_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        setup = self.request_obj.state['setup']
        initial['status'] = setup['status']
        initial['justification'] = setup['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'secure-dir-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SecureDirRequestReviewDenyView(LoginRequiredMixin, UserPassesTestMixin,
                                     SecureDirRequestMixin, FormView):
    form_class = SecureDirRequestReviewDenyForm
    template_name = (
        'secure_dir/secure_dir_request/secure_dir_review_deny.html')
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['other'] = {
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = secure_dir_request_state_status(self.request_obj)

        runner = SecureDirRequestDenialRunner(self.request_obj)
        runner.run()

        self.request_obj.save()

        message = (
            f'Status for {self.request_obj.project.name}\'s '
            f'secure directory request has been set to '
            f'{self.request_obj.status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secure_dir_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.request_obj.state['other']
        initial['justification'] = other['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'secure-dir-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SecureDirRequestUndenyRequestView(LoginRequiredMixin,
                                        UserPassesTestMixin,
                                        SecureDirRequestMixin,
                                        View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        message = (
            'You do not have permission to undeny a secure directory request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)

        disallowed_status_names = list(
            SecureDirRequestStatusChoice.objects.filter(
                ~Q(name='Denied')).values_list('name', flat=True))
        redirect = self.redirect_if_disallowed_status(
            request, disallowed_status_names=disallowed_status_names)
        if redirect is not None:
            return redirect

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        state = self.request_obj.state

        rdm_consultation = state['rdm_consultation']
        if rdm_consultation['status'] == 'Denied':
            rdm_consultation['status'] = 'Pending'
            rdm_consultation['timestamp'] = ''
            rdm_consultation['justification'] = ''

        mou = state['mou']
        if mou['status'] == 'Denied':
            mou['status'] = 'Pending'
            mou['timestamp'] = ''
            mou['justification'] = ''

        setup = state['setup']
        if setup['status'] != 'Pending':
            setup['status'] = 'Pending'
            setup['timestamp'] = ''
            setup['scratch'] = ''
            setup['groups'] = ''

        other = state['other']
        if other['timestamp']:
            other['justification'] = ''
            other['timestamp'] = ''

        self.request_obj.status = secure_dir_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Secure directory request for {self.request_obj.project.name} has '
            f'been un-denied and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse(
                'secure-dir-request-detail',
                kwargs={'pk': kwargs.get('pk')}))
