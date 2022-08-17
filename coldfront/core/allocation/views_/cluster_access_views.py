import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.validators import validate_email
from django.core.validators import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView
from django.views.generic.edit import FormView

from coldfront.core.allocation.forms import AllocationClusterAccountRequestActivationForm
from coldfront.core.allocation.forms import AllocationClusterAccountUpdateStatusForm
from coldfront.core.allocation.forms import ClusterRequestSearchForm
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import ClusterAccessRequest
from coldfront.core.allocation.models import ClusterAccessRequestStatusChoice
from coldfront.core.allocation.utils_.cluster_access_utils import ClusterAccessRequestCompleteRunner
from coldfront.core.allocation.utils_.cluster_access_utils import ClusterAccessRequestDenialRunner
from coldfront.core.allocation.utils_.cluster_access_utils import ClusterAccessRequestRunner
from coldfront.core.utils.common import utc_now_offset_aware


logger = logging.getLogger(__name__)


class AllocationRequestClusterAccountView(LoginRequiredMixin,
                                          UserPassesTestMixin,
                                          View):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allocation_user_obj = None

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

        allocation_user_objs = allocation_obj.allocationuser_set.filter(
            user=user_obj, status__name='Active')
        if not allocation_user_objs.exists():
            message = (
                f'User {user_obj.username} is not a member of allocation '
                f'{allocation_obj.pk}.')
            messages.error(self.request, message)
            return redirect
        self.allocation_user_obj = allocation_user_objs.first()

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

        request_runner = ClusterAccessRequestRunner(self.allocation_user_obj)
        try:
            request_runner.run()
        except Exception as e:
            message = (
                'Unexpected failure. Please try again, or contact an '
                'administrator if the problem persists.')
            messages.error(self.request, message)
        else:
            message = (
                f'Created a cluster access request for User {user_obj.pk} '
                f'under Project {project_obj.pk}.')
            messages.success(self.request, message)
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

        cluster_search_form = ClusterRequestSearchForm(self.request.GET)

        if self.completed:
            cluster_access_request_list = ClusterAccessRequest.objects.filter(
                status__name__in=['Denied', 'Complete'])
        else:
            cluster_access_request_list = ClusterAccessRequest.objects.filter(
                status__name__in=['Pending - Add', 'Processing'])

        if cluster_search_form.is_valid():
            data = cluster_search_form.cleaned_data

            if data.get('username'):
                cluster_access_request_list = \
                    cluster_access_request_list.filter(
                        allocation_user__user__username__icontains=data.get(
                            'username'))

            if data.get('email'):
                cluster_access_request_list = \
                    cluster_access_request_list.filter(
                        allocation_user__user__email__icontains=data.get(
                            'email'))

            if data.get('project_name'):
                cluster_access_request_list = \
                    cluster_access_request_list.filter(
                        allocation_user__allocation__project__name__icontains=data.get(
                            'project_name'))

            if data.get('request_status'):
                cluster_access_request_list = \
                    cluster_access_request_list.filter(
                        status__name__icontains=data.get('request_status'))

        return cluster_access_request_list.order_by(order_by)

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
                                              'order_by=%s&direction=%s&' % \
                                              (order_by, direction)
        else:
            filter_parameters_with_order_by = filter_parameters

        context['expand_accordion'] = 'show'

        context['filter_parameters'] = filter_parameters
        context['filter_parameters_with_order_by'] = \
            filter_parameters_with_order_by

        context['request_filter'] = (
            'completed' if self.completed else 'pending')
        cluster_access_request_list = self.get_queryset()

        paginator = Paginator(cluster_access_request_list, self.paginate_by)

        page = self.request.GET.get('page')

        try:
            cluster_access_requests = paginator.page(page)
        except PageNotAnInteger:
            cluster_access_requests = paginator.page(1)
        except EmptyPage:
            cluster_access_requests = paginator.page(paginator.num_pages)

        context['cluster_access_request_list'] = cluster_access_requests

        context['actions_visible'] = not self.completed

        return context


class AllocationClusterAccountUpdateStatusView(LoginRequiredMixin,
                                               UserPassesTestMixin,
                                               FormView):
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
        self.request_obj = get_object_or_404(
            ClusterAccessRequest, pk=self.kwargs.get('pk'))
        self.user_obj = self.request_obj.allocation_user.user
        status = self.request_obj.status.name
        if status != 'Pending - Add':
            message = f'Cluster access has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('allocation-cluster-account-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data.get('status')

        self.request_obj.status = \
            ClusterAccessRequestStatusChoice.objects.get(name=status)
        self.request_obj.save()

        allocation = self.request_obj.allocation_user.allocation
        project = allocation.project

        message = (
            f'Cluster access request from User {self.user_obj.email} under '
            f'Project {project.name} and Allocation {allocation.pk} '
            f'has been updated to have status "{status}".')
        messages.success(self.request, message)

        log_message = (
            f'Superuser {self.request.user.pk} changed the value of "Cluster '
            f'Account Status" AllocationUserAttribute {self.request_obj.pk} '
            f'from "Pending - Add" to "{status}".')
        logger.info(log_message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cluster_access_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = {
            'status': self.request_obj.status.name,
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
        self.request_obj = get_object_or_404(
            ClusterAccessRequest, pk=self.kwargs.get('pk'))
        self.user_obj = self.request_obj.allocation_user.user
        status = self.request_obj.status.name
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

        runner = None
        try:
            with transaction.atomic():
                self.request_obj.status = \
                    ClusterAccessRequestStatusChoice.objects.get(name='Complete')
                self.request_obj.completion_time = utc_now_offset_aware()
                self.request_obj.save()
                runner = \
                    ClusterAccessRequestCompleteRunner(self.request_obj)
                runner.run(username, cluster_uid)
        except Exception as e:
            message = f'Rolling back failed transaction. Details:\n{e}'
            logger.exception(message)
            message = (
                'Unexpected failure. Please try again, or contact an '
                'administrator if the problem persists.')
            messages.error(self.request, message)
        else:
            allocation = self.request_obj.allocation_user.allocation
            project = allocation.project

            message = (
                f'Cluster access request from User {self.user_obj.email} '
                f'under Project {project.name} and Allocation {allocation.pk} '
                f'has been ACTIVATED.')
            messages.success(self.request, message)

        if isinstance(runner, ClusterAccessRequestCompleteRunner):
            for message in runner.get_warning_messages():
                messages.warning(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cluster_access_request'] = self.request_obj
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


class AllocationClusterAccountDenyRequestView(LoginRequiredMixin,
                                              UserPassesTestMixin,
                                              View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to deny a cluster access request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(
            ClusterAccessRequest, pk=self.kwargs.get('pk'))
        self.user_obj = self.request_obj.allocation_user.user
        status = self.request_obj.status.name
        if status not in ('Pending - Add', 'Processing'):
            message = f'Cluster access has unexpected status {status}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('allocation-cluster-account-request-list'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        runner = None
        try:
            with transaction.atomic():
                self.request_obj.status = \
                    ClusterAccessRequestStatusChoice.objects.get(name='Denied')
                self.request_obj.completion_time = utc_now_offset_aware()
                self.request_obj.save()

                runner = ClusterAccessRequestDenialRunner(self.request_obj)
                runner.run()
        except Exception as e:
            message = f'Rolling back failed transaction. Details:\n{e}'
            logger.exception(message)
            message = (
                'Unexpected failure. Please try again, or contact an '
                'administrator if the problem persists.')
            messages.error(self.request, message)
        else:
            message = (
                f'Cluster access request from User {self.user_obj.email} under '
                f'Project {self.request_obj.allocation_user.allocation.project.name} '
                f'and Allocation {self.request_obj.allocation_user.allocation.pk} '
                f'has been DENIED.')
            messages.success(request, message)

        if isinstance(runner, ClusterAccessRequestDenialRunner):
            for message in runner.get_warning_messages():
                messages.warning(self.request, message)

        return HttpResponseRedirect(
            reverse('allocation-cluster-account-request-list'))
