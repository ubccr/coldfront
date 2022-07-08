from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.utils import annotate_queryset_with_allocation_period_not_started_bool
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.forms import ReviewDenyForm
from coldfront.core.project.forms import ReviewStatusForm
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalApprovalRunner
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalDenialRunner
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalProcessingRunner
from coldfront.core.project.utils_.renewal_utils import allocation_renewal_request_denial_reason
from coldfront.core.project.utils_.renewal_utils import allocation_renewal_request_latest_update_timestamp
from coldfront.core.project.utils_.renewal_utils import allocation_renewal_request_state_status
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import format_date_month_name_day_year
from coldfront.core.utils.common import utc_now_offset_aware

from decimal import Decimal

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

import iso8601
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
        return annotate_queryset_with_allocation_period_not_started_bool(
            AllocationRenewalRequest.objects.order_by(order_by))

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)

        args, kwargs = [], {}

        request_list = self.get_queryset()
        user = self.request.user
        permission = 'allocation.view_allocationrenewalrequest'
        if not (user.is_superuser or user.has_perm(permission)):
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

    allocation_period_obj = None
    request_obj = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['allocation_amount'] = self.get_service_units_to_allocate()
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
            context['allocation_amount'] = 'Failed to compute.'
        return context

    @staticmethod
    def get_redirect_url(pk):
        return reverse(
            'pi-allocation-renewal-request-detail', kwargs={'pk': pk})

    def get_service_units_to_allocate(self):
        """Return the number of service units to allocate to the project
        if it were to be approved now."""
        num_service_units = Decimal(
            ComputingAllowanceInterface().service_units_from_name(
                self.computing_allowance_obj.get_name()))
        return prorated_allocation_amount(
            num_service_units, self.request_obj.request_time,
            self.allocation_period_obj)

    def set_common_context_data(self, context):
        """Given a dictionary of context variables to include in the
        template, add additional, commonly-used variables."""
        context['renewal_request'] = self.request_obj
        context['computing_allowance_name'] = \
            self.computing_allowance_obj.get_name()

    def set_objs(self, pk):
        self.request_obj = get_object_or_404(
            AllocationRenewalRequest.objects.prefetch_related(
                'pi', 'post_project', 'pre_project', 'requester'), pk=pk)
        self.allocation_period_obj = self.request_obj.allocation_period
        self.computing_allowance_obj = ComputingAllowance(
            self.request_obj.computing_allowance)


class AllocationRenewalRequestDetailView(LoginRequiredMixin,
                                         UserPassesTestMixin,
                                         AllocationRenewalRequestMixin,
                                         DetailView):
    model = AllocationRenewalRequest
    template_name = (
        'project/project_renewal/project_renewal_request_detail.html')
    login_url = '/'

    error_message = 'Unexpected failure. Please contact an administrator.'
    request_obj = None

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        permission = 'allocation.view_allocationrenewalrequest'
        if self.request.user.has_perm(permission):
            return True

        if (self.request.user == self.request_obj.requester or
                self.request.user == self.request_obj.pi):
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_objs(pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)

        is_superuser = self.request.user.is_superuser

        try:
            latest_update_timestamp = \
                allocation_renewal_request_latest_update_timestamp(
                    self.request_obj)
            if not latest_update_timestamp:
                latest_update_timestamp = 'No updates yet.'
            else:
                latest_update_timestamp = iso8601.parse_date(
                    latest_update_timestamp)
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
            latest_update_timestamp = 'Failed to determine timestamp.'
        context['latest_update_timestamp'] = latest_update_timestamp

        if self.request_obj.status.name == 'Denied':
            try:
                denial_reason = allocation_renewal_request_denial_reason(
                    self.request_obj)
                category = denial_reason.category
                justification = denial_reason.justification
                timestamp = denial_reason.timestamp
            except Exception as e:
                logger.exception(e)
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

        context['has_allocation_period_started'] = \
            self.__has_request_allocation_period_started()
        context['is_allowed_to_manage_request'] = is_superuser
        if is_superuser:
            context['checklist'] = self.__get_checklist()
        context['is_checklist_complete'] = self.__is_checklist_complete()
        return context

    def post(self, request, *args, **kwargs):
        """Approve the request. Process it if its AllocationPeriod has
        already started."""
        pk = self.request_obj.pk
        if not request.user.is_superuser:
            message = 'You do not have permission to POST to this page.'
            messages.error(request, message)
            return HttpResponseRedirect(self.get_redirect_url(pk))
        if not self.__is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            return HttpResponseRedirect(self.get_redirect_url(pk))
        try:
            has_allocation_period_started = \
                self.__has_request_allocation_period_started()
            num_service_units = self.get_service_units_to_allocate()

            # Skip sending an approval email if a processing email will be sent
            # immediately afterward.
            approval_runner = AllocationRenewalApprovalRunner(
                self.request_obj, num_service_units,
                send_email=not has_allocation_period_started)
            approval_runner.run()

            if has_allocation_period_started:
                self.request_obj.refresh_from_db()
                processing_runner = AllocationRenewalProcessingRunner(
                    self.request_obj, num_service_units)
                processing_runner.run()
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            if not has_allocation_period_started:
                formatted_start_date = format_date_month_name_day_year(
                    self.request_obj.allocation_period.start_date)
                phrase = f'is scheduled for renewal on {formatted_start_date}.'
            else:
                phrase = 'has been renewed.'
            message = (
                f'PI {self.request_obj.pi.username}\'s allocation {phrase}')
            messages.success(self.request, message)
            logger.info(message)

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
                new_project_request.latest_update_timestamp(),
                True,
                reverse(
                    'new-project-request-detail',
                    kwargs={'pk': new_project_request.pk}),
            ])
        else:
            eligibility = self.request_obj.state['eligibility']
            checklist.append([
                (f'Confirm that the requested PI is still eligible for a  '
                 f'{self.computing_allowance_obj.get_name()}.'),
                eligibility['status'],
                eligibility['timestamp'],
                True,
                reverse(
                    'pi-allocation-renewal-request-review-eligibility',
                    kwargs={'pk': self.request_obj.pk}),
            ])
        return checklist

    def __has_request_allocation_period_started(self):
        """Return whether the request's AllocationPeriod has started."""
        return (
            self.request_obj.allocation_period.start_date <=
            display_time_zone_current_date())

    def __is_checklist_complete(self):
        """Return whether the request is ready for final submission."""
        new_project_request = self.request_obj.new_project_request
        if new_project_request:
            complete_status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')
            if new_project_request.status != complete_status:
                return False
        else:
            eligibility = self.request_obj.state['eligibility']
            if eligibility['status'] != 'Approved':
                return False
        return True


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
        self.set_objs(pk)
        response_redirect = HttpResponseRedirect(self.get_redirect_url(pk))
        status_name = self.request_obj.status.name
        if status_name in ['Approved', 'Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return response_redirect
        if self.request_obj.new_project_request:
            message = (
                'This request involves creating a new project. Eligibility '
                'review must be handled in the associated project request.')
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
        self.request_obj.status = allocation_renewal_request_state_status(
            self.request_obj)
        self.request_obj.save()

        if status == 'Denied':
            runner = AllocationRenewalDenialRunner(self.request_obj)
            runner.run()

        message = (
            f'Eligibility status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        context['is_allowance_one_per_pi'] = \
            self.computing_allowance_obj.is_one_per_pi()
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.request_obj.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def get_success_url(self):
        return self.get_redirect_url(self.kwargs.get('pk'))


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
        self.set_objs(pk)
        response_redirect = HttpResponseRedirect(self.get_redirect_url(pk))

        status_name = self.request_obj.status.name
        if status_name in ['Approved', 'Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return response_redirect

        new_project_request = self.request_obj.new_project_request
        if new_project_request:
            if new_project_request.status.name != 'Denied':
                message = (
                    'Deny the associated Savio Project request first, which '
                    'should automatically deny this request.')
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
        self.request_obj.status = allocation_renewal_request_state_status(
            self.request_obj)

        runner = AllocationRenewalDenialRunner(self.request_obj)
        runner.run()

        self.request_obj.save()

        message = (
            f'Status for {self.request_obj.pk} has been set to '
            f'{self.request_obj.status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.set_common_context_data(context)
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.request_obj.state['other']
        initial['justification'] = other['justification']
        return initial

    def get_success_url(self):
        return self.get_redirect_url(self.kwargs.get('pk'))


# This is disabled because a PI may always make a new request.
# In addition, checks need to be done to ensure that a request cannot be
# un-denied if the PI has already renewed elsewhere.
# class AllocationRenewalRequestUndenyView(LoginRequiredMixin,
#                                          UserPassesTestMixin,
#                                          AllocationRenewalRequestMixin,
#                                          View):
#     login_url = '/'
#
#     def test_func(self):
#         """UserPassesTestMixin tests."""
#         if self.request.user.is_superuser:
#             return True
#         message = 'You do not have permission to view the previous page.'
#         messages.error(self.request, message)
#
#     def dispatch(self, request, *args, **kwargs):
#         pk = self.kwargs.get('pk')
#         self.set_objs(pk)
#         response_redirect = HttpResponseRedirect(self.get_redirect_url(pk))
#
#         status_name = self.request_obj.status.name
#         if status_name != 'Denied':
#             message = (
#                 f'You cannot un-deny a request with status '
#                 f'\'{status_name}\'.')
#             messages.error(request, message)
#             return response_redirect
#
#         new_project_request = self.request_obj.new_project_request
#         if new_project_request:
#             if new_project_request.status.name == 'Complete':
#                 message = (
#                     f'You cannot un-deny a request that has an associated '
#                     f'new project request with status \'Complete\'.')
#                 messages.error(request, message)
#                 return response_redirect
#
#         return super().dispatch(request, *args, **kwargs)
#
#     def get(self, request, *args, **kwargs):
#         message = 'Unsupported method.'
#         messages.error(request, message)
#         return HttpResponseRedirect(
#             self.get_redirect_url(self.request_obj.pk))
#
#     def post(self, request, *args, **kwargs):
#         request_obj = self.request_obj
#         response_redirect = HttpResponseRedirect(
#             self.get_redirect_url(request_obj.pk))
#
#         new_project_request = request_obj.new_project_request
#         if new_project_request:
#             if new_project_request.status == 'Denied':
#                 message = (
#                     'Un-deny the associated Savio Project request before '
#                     'un-denying this request.')
#                 messages.error(request, message)
#                 return response_redirect
#
#         eligibility = request_obj.state['eligibility']
#         if eligibility['status'] == 'Denied':
#             eligibility['status'] = 'Pending'
#
#         other = request_obj.state['other']
#         if other['timestamp']:
#             other['justification'] = ''
#             other['timestamp'] = ''
#
#         request_obj.status = allocation_renewal_request_state_status(
#             request_obj)
#         request_obj.save()
#
#         message = (
#             f'Status for {request_obj.pk} has been set to '
#             f'{request_obj.status}.')
#         messages.success(request, message)
#
#         return HttpResponseRedirect(self.get_redirect_url(request_obj.pk))
