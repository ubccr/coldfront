from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.forms import ReviewDenyForm
from coldfront.core.project.forms import ReviewStatusForm
from coldfront.core.project.utils import project_allocation_request_latest_update_timestamp
from coldfront.core.utils.common import utc_now_offset_aware

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import DetailView
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

import logging


logger = logging.getLogger(__name__)


class AllocationRenewalRequestListView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_renewal/project_renewal_request_list.html'
    login_url = '/'
    completed = False

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
        return AllocationRenewalRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)

        args, kwargs = [], {}

        request_list = self.get_queryset()
        user = self.request.user
        if not user.is_superuser:
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = ['Approved', 'Complete', 'Denied']
        else:
            status__name__in = ['Under Review']
        kwargs['status__name__in'] = status__name__in
        context['renewal_request_list'] = request_list.filter(*args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class AllocationRenewalRequestMixin(object):

    request_obj = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['allocation_amount'] = \
                self.__get_service_units_to_allocate()
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
            context['allocation_amount'] = 'Failed to compute.'
        return context

    @staticmethod
    def get_redirect_url(pk):
        return reverse(
            'pi-allocation-renewal-request-detail', kwargs={'pk': pk})

    @staticmethod
    def __get_service_units_to_allocate():
        """Return the number of service units to allocate to the project
        if it were to be approved now."""
        now = utc_now_offset_aware()
        return prorated_allocation_amount(settings.FCA_DEFAULT_ALLOCATION, now)

    def set_request_obj(self, pk):
        self.request_obj = get_object_or_404(
            AllocationRenewalRequest.objects.prefetch_related(
                'pi', 'post_project', 'pre_project', 'requester'), pk=pk)


class AllocationRenewalRequestDetailView(LoginRequiredMixin,
                                         UserPassesTestMixin,
                                         AllocationRenewalRequestMixin,
                                         DetailView):
    model = AllocationRenewalRequest
    template_name = (
        'project/project_renewal/project_renewal_request_detail.html')
    login_url = '/'
    context_object_name = 'renewal_request'

    error_message = 'Unexpected failure. Please contact an administrator.'
    request_obj = None

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True
        if (self.request.user == self.request_obj.requester or
                self.request.user == self.request.pi):
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        is_superuser = self.request.user.is_superuser

        # TODO: Use the actual timestamp.
        from datetime import datetime
        context['latest_update_timestamp'] = datetime.utcnow()

        context['is_allowed_to_manage_request'] = is_superuser

        if is_superuser:
            context['checklist'] = self.__get_checklist()

        context['is_checklist_complete'] = self.__is_checklist_complete()

        return context

    def post(self, request, *args, **kwargs):
        if not self.__is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(self.get_redirect_url(pk))
        try:
            num_service_units = self.__get_service_units_to_allocate()
            # TODO
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            # TODO
            message = (
                'TODO'
            )
            messages.success(self.request, message)

        return HttpResponseRedirect(
            reverse_lazy('pi-allocation-renewal-pending-request-list'))

    def __get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.

        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage"
        button]."""
        checklist = []
        new_project_request = self.request_obj.new_project_request
        if new_project_request:
            checklist.append([
                'Approve and process the new project request.',
                new_project_request.status.name,
                project_allocation_request_latest_update_timestamp(
                    new_project_request),
                True,
                reverse(
                    'savio-project-request-detail',
                    kwargs={'pk': new_project_request.pk}),
            ])
        else:
            eligibility = self.request_obj.state['eligibility']
            checklist.append([
                ('Confirm that the requested PI is eligible for a Savio '
                 'allowance.'),
                eligibility['status'],
                eligibility['timestamp'],
                True,
                reverse(
                    'pi-allocation-renewal-request-review-eligibility',
                    kwargs={'pk': self.request_obj.pk}),
            ])
        return checklist

    def __is_checklist_complete(self):
        """Return whether the request is ready for final submission."""
        # TODO
        return False


class AllocationRenewalRequestReviewEligibilityView(LoginRequiredMixin,
                                                    UserPassesTestMixin,
                                                    AllocationRenewalRequestMixin,
                                                    FormView):
    form_class = ReviewStatusForm
    template_name = 'project/project_renewal/review_eligibility.html'
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
        response_redirect = HttpResponseRedirect(self.get_redirect_url(pk))
        status_name = self.request_obj.status.name
        if status_name in ['Approved', 'Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return response_redirect
        if self.request_obj.new_project_request:
            message = (
                f'This request involves creating a new project. Eligibility '
                f'review must be handled in the associated project request.')
            messages.error(request, message)
            return response_redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['eligibility'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        # TODO
        self.request_obj.status = None

        if status == 'Denied':
            # TODO
            pass

        self.request_obj.save()

        message = (
            f'Eligibility status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)


class AllocationRenewalRequestReviewDenyView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             AllocationRenewalRequestMixin,
                                             FormView):
    form_class = ReviewDenyForm
    template_name = 'project/project_renewal/review_deny.html'
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
        response_redirect = HttpResponseRedirect(self.get_redirect_url(pk))
        status_name = self.request_obj.status.name
        if status_name in ['Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return response_redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['other'] = {
            'justification': justification,
            'timestamp': timestamp,
        }
        # TODO
        self.request_obj.status = None

        # TODO

        self.request_obj.save()

        message = (
            f'Status for {self.request_obj.pk} has been set to '
            f'{self.request_obj.status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['renewal_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.request_obj.state['other']
        initial['justification'] = other['justification']
        return initial

    def get_success_url(self):
        return self.get_redirect_url(self.kwargs.get('pk'))
