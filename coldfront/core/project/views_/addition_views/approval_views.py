from copy import deepcopy

from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.project.forms import MemorandumSignedForm
from coldfront.core.project.forms import SavioProjectRechargeExtraFieldsForm
from coldfront.core.project.forms import ReviewDenyForm
from coldfront.core.project.utils_.addition_utils import AllocationAdditionDenialRunner
from coldfront.core.project.utils_.addition_utils import AllocationAdditionProcessingRunner
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project
from coldfront.core.user.utils import access_agreement_signed
from coldfront.core.utils.common import utc_now_offset_aware

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

import iso8601
import logging
import os

"""Views relating to reviewing requests to purchase more Service Units
for a Project."""


logger = logging.getLogger(__name__)


class AllocationAdditionRequestDetailView(LoginRequiredMixin,
                                          UserPassesTestMixin, DetailView):
    """A view with details on a single request to purchase more service
    units under a Project."""

    model = AllocationAdditionRequest
    template_name = 'project/project_allocation_addition/request_detail.html'
    login_url = '/'
    context_object_name = 'addition_request'

    request_obj = None

    error_message = 'Unexpected failure. Please contact an administrator.'

    detail_view_name = 'service-units-purchase-request-detail'
    list_view_name = 'service-units-purchase-pending-request-list'

    def dispatch(self, request, *args, **kwargs):
        """Store the request object."""
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(AllocationAdditionRequest, pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_checklist(self):
        """Return a nested list, where each row contains the details of
        one item on the checklist.

        Each row is of the form: [task text, status name, latest update
        timestamp, is "Manage" button available, URL of "Manage"
        button]."""
        checklist = []
        memorandum_signed = self.request_obj.state['memorandum_signed']
        checklist.append([
            ('Confirm that the Memorandum of Understanding has been signed '
             'and that funds have been transferred.'),
            memorandum_signed['status'],
            memorandum_signed['timestamp'],
            True,
            reverse(
                'service-units-purchase-request-review-memorandum-signed',
                kwargs={'pk': self.request_obj.pk})
        ])
        return checklist

    def get_context_data(self, **kwargs):
        """Set the following variables:
            - num_service_units: Decimal
            - purchase_details_form: Form instance
            - checklist: List of lists
            - is_checklist_complete: boolean
            - review_controls_visible: boolean
        """
        context = super().get_context_data(**kwargs)

        try:
            latest_update_timestamp = \
                self.request_obj.latest_update_timestamp()
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
                denial_reason = self.request_obj.denial_reason()
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

        initial = deepcopy(self.request_obj.extra_fields)
        initial['num_service_units'] = self.request_obj.num_service_units
        context['purchase_details_form'] = SavioProjectRechargeExtraFieldsForm(
            initial=initial, disable_fields=True)

        context['checklist'] = self.get_checklist()
        context['is_checklist_complete'] = self.is_checklist_complete()
        context['review_controls_visible'] = (
            self.request.user.is_superuser and
            self.request_obj.status.name not in ('Denied', 'Complete'))

        return context

    def is_checklist_complete(self):
        """Return whether the request is ready for final submission."""
        memorandum_signed = self.request_obj.state['memorandum_signed']
        return memorandum_signed['status'] == 'Complete'

    def post(self, request, *args, **kwargs):
        """Process the request after validating that it is ready to be
        processed."""
        pk = self.request_obj.pk
        detail_view_redirect = HttpResponseRedirect(
            reverse(self.detail_view_name, kwargs={'pk': pk}))

        if not request.user.is_superuser:
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            return detail_view_redirect

        if not self.is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            return detail_view_redirect

        try:
            runner = AllocationAdditionProcessingRunner(self.request_obj)
            total_service_units = runner.run()
        except Exception as e:
            logger.exception(e)
            messages.error(request, self.error_message)
        else:
            message = (
                f'Project {self.request_obj.project.name}\'s allocation has '
                f'been set to {total_service_units} and its usage has been '
                f'reset to zero.')
            messages.success(request, message)

        return HttpResponseRedirect(reverse(self.list_view_name))

    def test_func(self):
        """Allow superusers and users with permission to view
        AllocationAdditionRequests. Allow active PIs and Managers of the
        Project who have signed the User Access Agreement."""
        user = self.request.user
        permission = 'allocation.view_allocationadditionrequest'
        if user.is_superuser or user.has_perm(permission):
            return True
        if not access_agreement_signed(user):
            message = 'You must sign the User Access Agreement.'
            messages.error(self.request, message)
            return False
        if is_user_manager_or_pi_of_project(user, self.request_obj.project):
            return True
        message = 'You must be an active PI or manager of the Project.'
        messages.error(self.request, message)


class AllocationAdditionRequestListView(LoginRequiredMixin, TemplateView):
    """A view that lists pending or completed requests to purchase more
    Service Units under Projects."""

    template_name = 'project/project_allocation_addition/request_list.html'
    login_url = '/'
    completed = False

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser or has the appropriate permissions, show all such
        requests. Otherwise, show only those for Projects of which the
        user is a PI or manager."""
        context = super().get_context_data(**kwargs)

        if self.completed:
            status__name__in = ['Complete', 'Denied']
        else:
            status__name__in = ['Under Review']
        order_by = self.get_order_by()
        request_list = AllocationAdditionRequest.objects.filter(
            status__name__in=status__name__in).order_by(order_by)

        user = self.request.user
        permission = 'allocation.view_allocationadditionrequest'
        if not (user.is_superuser or user.has_perm(permission)):
            request_ids = [
                r.id for r in request_list
                if is_user_manager_or_pi_of_project(user, r.project)]
            request_list = AllocationAdditionRequest.objects.filter(
                id__in=request_ids).order_by(order_by)

        context['addition_request_list'] = request_list
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context

    def get_order_by(self):
        """Return a string to be used to order results using the field
        and direction specified by the user. If not provided, default to
        sorting by ascending ID."""
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
        return order_by


class AllocationAdditionReviewBase(LoginRequiredMixin, UserPassesTestMixin,
                                   FormView):
    """A base class for views for reviewing an
    AllocationAdditionRequest."""

    login_url = '/'

    error_message = 'Unexpected failure. Please contact an administrator.'
    request_obj = None
    template_dir = 'project/project_allocation_addition'

    def dispatch(self, request, *args, **kwargs):
        """Store the AllocationAdditionRequest object for reuse. If it
        has an unexpected status, redirect."""
        pk = self.kwargs.get('pk')
        self.request_obj = get_object_or_404(AllocationAdditionRequest, pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse(
                    'service-units-purchase-request-detail',
                    kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Set the following variables:
            - addition_request: AllocationAdditionRequest instance
            - num_service_units: Decimal
            - purchase_details_form: Form instance
        """
        context = super().get_context_data(**kwargs)
        context['addition_request'] = self.request_obj
        initial = deepcopy(self.request_obj.extra_fields)
        initial['num_service_units'] = self.request_obj.num_service_units
        context['purchase_details_form'] = SavioProjectRechargeExtraFieldsForm(
            initial=initial, disable_fields=True)
        return context

    def get_form_class(self):
        raise NotImplementedError

    def get_initial(self):
        return super().get_initial()

    def get_success_url(self):
        """On success, redirect to the detail view."""
        return reverse(
            'service-units-purchase-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})

    def get_template_names(self):
        raise NotImplementedError

    def test_func(self):
        """Allow superusers."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False


class AllocationAdditionReviewDenyView(AllocationAdditionReviewBase):
    """A view that allows administrators to deny an
    AllocationAdditionRequest."""

    def form_valid(self, form):
        """Update the relevant entry in the request's state with the
        specified justification and the current timestamp. Run denial
        steps."""
        form_data = form.cleaned_data
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['other'] = {
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.save()

        try:
            runner = AllocationAdditionDenialRunner(self.request_obj)
            runner.run()
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            message = f'Request {self.request_obj.pk} has been denied.'
            messages.success(self.request, message)

        return super().form_valid(form)

    def get_form_class(self):
        return ReviewDenyForm

    def get_initial(self):
        """Pre-populate the form with the existing value of the relevant
        entry from the request's state."""
        initial = super().get_initial()
        other = self.request_obj.state['other']
        initial['justification'] = other['justification']
        return initial

    def get_template_names(self):
        return [os.path.join(self.template_dir, 'review_deny.html')]


class AllocationAdditionReviewMemorandumSignedView(AllocationAdditionReviewBase):
    """A view that allows administrators to confirm that the Memorandum
    of Understanding has been signed and that funds have been
    transferred."""

    def form_valid(self, form):
        """Update the relevant entry in the request's state with the
        specified status and the current timestamp."""
        form_data = form.cleaned_data
        status = form_data['status']
        timestamp = utc_now_offset_aware().isoformat()

        self.request_obj.state['memorandum_signed'] = {
            'status': status,
            'timestamp': timestamp,
        }

        self.request_obj.save()

        message = (
            f'Memorandum Signed status for request {self.request_obj.pk} has '
            f'been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_form_class(self):
        return MemorandumSignedForm

    def get_initial(self):
        """Pre-populate the form with the existing value of the relevant
        entry from the request's state."""
        initial = super().get_initial()
        memorandum_signed = self.request_obj.state['memorandum_signed']
        initial['status'] = memorandum_signed['status']
        return initial

    def get_template_names(self):
        return [
            os.path.join(self.template_dir, 'review_memorandum_signed.html')]
