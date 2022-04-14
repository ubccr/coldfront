import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms import formset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import ListView, FormView
from django.views.generic.base import TemplateView, View

from coldfront.core.allocation.forms import SecureDirManageUsersForm, \
    SecureDirManageUsersSearchForm
from coldfront.core.allocation.models import Allocation, \
    SecureDirAddUserRequest, SecureDirAddUserRequestStatusChoice, \
    SecureDirRemoveUserRequest, SecureDirRemoveUserRequestStatusChoice, \
    AllocationUserAttribute
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.mail import send_email, send_email_template


class SecureDirManageUsersView(LoginRequiredMixin,
                               UserPassesTestMixin,
                               TemplateView):
    template_name = 'secure_dir/secure_dir_manage_users.html'
    action = 'Add'

    logger = logging.getLogger(__name__)

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
        if alloc_obj.status.name not in ['Active', 'New', ]:
            messages.error(
                request, 'You can only add users to an active allocation.')
            return HttpResponseRedirect(
                reverse('allocation-detail', kwargs={'pk': alloc_obj.pk}))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_users_to_add(self, alloc_obj):
        savio_compute = Resource.objects.get(name='Savio Compute')
        compute_alloc = Allocation.objects.get(project=alloc_obj.project,
                                               resources=savio_compute)

        # Adding active AllocationUsers from main compute allocation.
        users_to_add = set(alloc_user.user for alloc_user in
                           compute_alloc.allocationuser_set.filter(
                               status__name='Active'))

        # Excluding active users that are already part of the allocation.
        users_to_exclude = set(alloc_user.user for alloc_user in
                               alloc_obj.allocationuser_set.filter(
                                   status__name='Active'))

        # Excluding users that have active join requests.
        users_to_exclude |= \
            set(request.user for request in
                SecureDirAddUserRequest.objects.filter(
                    allocation=alloc_obj,
                    status__name__in=['Pending - Add',
                                      'Processing - Add']))

        # Excluding users that have active removal requests.
        users_to_exclude |= \
            set(request.user for request in
                SecureDirRemoveUserRequest.objects.filter(
                    allocation=alloc_obj,
                    status__name__in=['Pending - Remove',
                                      'Processing - Remove']))

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

        users_to_remove -= set(request.user for request in
                               SecureDirRemoveUserRequest.objects.filter(
                                   allocation=alloc_obj,
                                   status__name__in=['Pending - Remove',
                                                     'Processing - Remove']))

        # PIs cannot request to remove themselves from their
        # own secure directories
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

        if self.action == 'Add':
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

        directory_name = 'scratch2' if \
            alloc_obj.resources.filter(name__icontains='Scratch').exists() \
            else 'group'
        context['title'] = f'secure {directory_name} directory for ' \
                           f'{alloc_obj.project.name}'

        context['action'] = self.action
        context['url'] = 'secure-dir-add-users' \
            if self.action == 'Add' else 'secure-dir-remove-users'

        context['button'] = 'btn-success' if self.action == 'Add' \
            else 'btn-danger'

        context['preposition'] = 'to' if self.action == 'Add' else 'from'

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

        if self.action == 'Add':
            user_list = self.get_users_to_add(alloc_obj)
        else:
            user_list = self.get_users_to_remove(alloc_obj)

        formset = formset_factory(
            SecureDirManageUsersForm, max_num=len(user_list))
        formset = formset(
            request.POST, initial=user_list, prefix='userform')

        reviewed_users_count = 0

        decision = request.POST.get('decision', None)
        if decision not in ['Add', 'Remove']:
            return HttpResponse('', status=400)

        if formset.is_valid():
            if decision == 'Add':
                pending_status = \
                    SecureDirAddUserRequestStatusChoice.objects.get(
                        name='Pending - Add')
            else:
                pending_status = \
                    SecureDirRemoveUserRequestStatusChoice.objects.get(
                        name='Pending - Remove')

            for form in formset:
                user_form_data = form.cleaned_data
                if user_form_data['selected']:
                    reviewed_users_count += 1
                    user_obj = User.objects.get(
                        username=user_form_data.get('username'))

                    # Create a new SecureDirAddUserRequest for the user.
                    if decision == 'Add':
                        secure_dir_add_request = \
                            SecureDirAddUserRequest.objects.create(
                                user=user_obj,
                                allocation=alloc_obj,
                                status=pending_status
                            )
                    else:
                        secure_dir_remove_request = \
                            SecureDirRemoveUserRequest.objects.create(
                                user=user_obj,
                                allocation=alloc_obj,
                                status=pending_status
                            )

                    # TODO: do we email admins? Probably

            # TODO: alter message or is it already informative enough?
            directory_name = 'scratch2' if \
                alloc_obj.resources.filter(name__icontains='Scratch').exists() \
                else 'group'

            message = (
                f'Successfully requested to {decision.lower()} '
                f'{reviewed_users_count} user'
                f'{"s" if reviewed_users_count > 1 else ""} '
                f'{"to" if decision == "Add" else "from"} the secure '
                f'{directory_name} directory for {alloc_obj.project.name}. '
                f'BRC staff have been notified.')
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
    login_url = '/'
    completed = False
    action = 'Add'
    paginate_by = 30

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            f'You do not have permission to review secure directory '
            f'{self.action.lower()} requests.')
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

        if self.action == 'Add':
            pending_status = \
                SecureDirAddUserRequestStatusChoice.objects.filter(
                    name__in=['Pending - Add', 'Processing - Add'])
            complete_status = \
                SecureDirAddUserRequestStatusChoice.objects.filter(
                    name__in=['Completed', 'Denied'])

        else:
            pending_status = \
                SecureDirRemoveUserRequestStatusChoice.objects.filter(
                    name__in=['Pending - Remove', 'Processing - Remove'])
            complete_status = \
                SecureDirRemoveUserRequestStatusChoice.objects.filter(
                    name__in=['Completed', 'Denied'])

        secure_dir_request_search_form = \
            SecureDirManageUsersSearchForm(self.request.GET)

        request_obj = SecureDirAddUserRequest if self.action == 'Add' else \
            SecureDirRemoveUserRequest

        if self.completed:
            request_list = request_obj.objects.filter(
                status__in=complete_status)
        else:
            request_list = request_obj.objects.filter(status__in=pending_status)

        if secure_dir_request_search_form.is_valid():
            data = secure_dir_request_search_form.cleaned_data

            if data.get('username'):
                request_list = request_list.filter(
                    user__username__icontains=data.get('username'))

            if data.get('email'):
                request_list = request_list.filter(
                    user__email__icontains=data.get('email'))

            if data.get('allocation_name'):
                request_list = \
                    request_list.filter(
                        allocation__project__name__icontains=data.get(
                            'allocation_name'))

            if data.get('resource_name'):
                request_list = \
                    request_list.filter(
                        allocation__resources__name__icontains=data.get(
                            'resource_name'))

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
        if self.action == 'Add':
            context['pending_url'] = \
                'secure-dir-add-users-request-list'
            context['completed_url'] = \
                'secure-dir-add-users-request-list-completed'
        else:
            context['pending_url'] = \
                'secure-dir-remove-users-request-list'
            context['completed_url'] = \
                'secure-dir-remove-users-request-list-completed'

        context['preposition'] = 'to' if self.action == 'Add' else 'from'

        return context


class SecureDirManageUsersUpdateStatusView(LoginRequiredMixin,
                                           UserPassesTestMixin,
                                           FormView):
    form_class = None
    login_url = '/'
    template_name = ''

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        # TODO: alter message
        message = (
            'You do not have permission to update secure dir requests.')
        messages.error(self.request, message)


class SecureDirManageUsersCompleteStatusView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             FormView):
    form_class = None
    login_url = '/'
    template_name = ''

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        # TODO: alter message
        message = (
            'You do not have permission to update secure dir requests.')
        messages.error(self.request, message)


class SecureDirManageUsersDenyRequestView(LoginRequiredMixin,
                                          UserPassesTestMixin,
                                          View):
    login_url = '/'
    action = 'Add'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        # TODO: alter message
        message = (
            'You do not have permission to deny a secure directory request.')
        messages.error(self.request, message)

    def get(self, request, *args, **kwargs):
        action = self.kwargs.get('action')
        request_type = SecureDirAddUserRequest \
            if action == 'Add' else SecureDirRemoveUserRequest
        request_status_type = SecureDirAddUserRequestStatusChoice \
            if action == 'Add' else SecureDirRemoveUserRequestStatusChoice
        secure_dir_manage_user_request = \
            get_object_or_404(request_type, pk=self.kwargs.get('pk'))

        secure_dir_manage_user_request.status = request_status_type.objects.get(name='Denied')
        secure_dir_manage_user_request.completion_time = utc_now_offset_aware()
        secure_dir_manage_user_request.save()

        # TODO: new message
        message = f'DENIED {action.upper()} REQUEST'
        messages.success(request, message)

        # TODO: send email after denial

        return HttpResponseRedirect(
            reverse(f'secure-dir-{action.lower()}-users-request-list'))
