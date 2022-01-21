from copy import deepcopy

from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.project.forms import MemorandumSignedForm
from coldfront.core.project.forms import SavioProjectRechargeExtraFieldsForm
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

import logging

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

    def dispatch(self, request, *args, **kwargs):
        """TODO"""
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
        """TODO"""
        context = super().get_context_data(**kwargs)

        initial = deepcopy(self.request_obj.extra_fields)
        initial['num_service_units'] = self.request_obj.num_service_units
        context['purchase_details_form'] = SavioProjectRechargeExtraFieldsForm(
            initial=initial, disable_fields=True)

        # context['checklist'] = self.get_checklist()
        context['is_checklist_complete'] = False
        context['review_controls_visible'] = (
            self.request.user.is_superuser and
            self.request_obj.status.name not in ('Denied', 'Complete'))

        return context

    def get_redirect_url(self, pk):
        """TODO"""
        # TODO
        return '/'

    def is_checklist_complete(self):
        """Return whether the request is ready for final submission."""
        # TODO
        return False

    def test_func(self):
        """Allow TODO"""
        return True


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


class AllocationAdditionReviewMemorandumSignedView(LoginRequiredMixin,
                                                   UserPassesTestMixin,
                                                   FormView):
    """A view that allows administrators to confirm that the Memorandum
    of Understanding has been signed and that funds have been
    transferred."""

    form_class = MemorandumSignedForm
    template_name = (
        'project/project_allocation_addition/review_memorandum_signed.html')
    login_url = '/'

    request_obj = None

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

    def get_context_data(self, **kwargs):
        """TODO"""
        context = super().get_context_data(**kwargs)
        context['addition_request'] = self.request_obj
        initial = deepcopy(self.request_obj.extra_fields)
        initial['num_service_units'] = self.request_obj.num_service_units
        context['purchase_details_form'] = SavioProjectRechargeExtraFieldsForm(
            initial=initial, disable_fields=True)
        return context

    def get_initial(self):
        """TODO"""
        initial = super().get_initial()
        memorandum_signed = self.request_obj.state['memorandum_signed']
        initial['status'] = memorandum_signed['status']
        return initial

    def get_success_url(self):
        """TODO"""
        return reverse(
            'service-units-purchase-request-detail', kwargs={'pk': pk})

    def test_func(self):
        """Allow superusers."""
        if self.request.user.is_superuser:
            return True
        message = 'You do not have permission to view the previous page.'
        messages.error(self.request, message)
        return False
