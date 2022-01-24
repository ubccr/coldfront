from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.forms import SavioProjectRechargeExtraFieldsForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import savio_project_request_recharge_extra_fields_schema
from coldfront.core.project.utils_.addition_utils import can_project_purchase_service_units
from coldfront.core.project.utils_.addition_utils import has_pending_allocation_addition_request
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project
from coldfront.core.user.utils import access_agreement_signed

from decimal import Decimal
from decimal import DivisionByZero
from decimal import DivisionUndefined
from decimal import InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

import logging

"""Views relating to making requests to purchase more Service Units for
a Project."""


logger = logging.getLogger(__name__)


class AllocationAdditionRequestLandingView(LoginRequiredMixin,
                                           UserPassesTestMixin, TemplateView):
    """A view that provides information regarding purchasing more
    Service Units for the given Project. Eligible Project types include:
    Recharge."""

    template_name = 'project/project_allocation_addition/request_landing.html'
    login_url = '/'

    project_obj = None

    def dispatch(self, request, *args, **kwargs):
        """Store the Project object for reuse. If it is ineligible,
        redirect."""
        pk = self.kwargs.get('pk')
        self.project_obj = get_object_or_404(Project, pk=pk)

        if not can_project_purchase_service_units(self.project_obj):
            message = (
                f'Project {self.project_obj.name} is ineligible to purchase '
                f'more Service Units.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('project-detail', kwargs={'pk': self.project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Set the following variables:
            - project: Project instance
            - has_pending_request: boolean
            - current_allowance: Decimal
            - current_usage: Decimal
            - usage_percentage: str
        """
        context = super().get_context_data(**kwargs)
        context['project'] = self.project_obj

        context['has_pending_request'] = \
            has_pending_allocation_addition_request(self.project_obj)

        try:
            allocation = get_project_compute_allocation(self.project_obj)
            allocation_attribute = allocation.allocationattribute_set.get(
                allocation_attribute_type__name='Service Units')
            allocation_attribute_usage = \
                allocation_attribute.allocationattributeusage
            current_allowance = Decimal(allocation_attribute.value)
            current_usage = Decimal(allocation_attribute_usage.value)
        except Exception as e:
            log_message = (
                f'Failed to retrieve allowance details for Project '
                f'{self.project_obj.pk}. Details:')
            logger.error(log_message)
            logger.exception(e)
            current_allowance = settings.ALLOCATION_MIN
            current_usage = settings.ALLOCATION_MIN
        context['current_allowance'] = current_allowance
        context['current_usage'] = current_usage

        try:
            quotient = (
                context['current_usage'] / context['current_allowance'])
        except (DivisionByZero, DivisionUndefined, InvalidOperation):
            quotient = Decimal('0.00')
        context['usage_percentage'] = f'{quotient * 100:.2f}%'

        return context

    def test_func(self):
        """Allow superusers and staff. Allow active PIs and Managers of
        the Project who have signed the User Access Agreement."""
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return True
        if not access_agreement_signed(user):
            message = 'You must sign the User Access Agreement.'
            messages.error(self.request, message)
            return False
        if is_user_manager_or_pi_of_project(user, self.project_obj):
            return True
        message = 'You must be an active PI or manager of the Project.'
        messages.error(self.request, message)


class AllocationAdditionRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                    FormView):
    """A view for creating requests to purchase more Service Units for
    the given Project."""

    form_class = SavioProjectRechargeExtraFieldsForm
    template_name = 'project/project_allocation_addition/request_form.html'
    login_url = '/'

    project_obj = None

    def dispatch(self, request, *args, **kwargs):
        """Store the Project object for reuse. If it is ineligible,
        redirect."""
        pk = self.kwargs.get('pk')
        self.project_obj = get_object_or_404(Project, pk=pk)

        redirect = HttpResponseRedirect(
            reverse('project-detail', kwargs={'pk': self.project_obj.pk}))

        if not can_project_purchase_service_units(self.project_obj):
            message = (
                f'Project {self.project_obj.name} is ineligible to purchase '
                f'more Service Units.')
            messages.error(request, message)
            return redirect

        if has_pending_allocation_addition_request(self.project_obj):
            message = (
                f'Project {self.project_obj.name} already has a pending '
                f'request to purchase more Service Units.')
            messages.error(request, message)
            return redirect

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Create an AllocationAdditionRequest."""
        try:
            requester = self.request.user
            project = self.project_obj

            form_data = form.cleaned_data
            extra_fields = savio_project_request_recharge_extra_fields_schema()
            for field in extra_fields:
                extra_fields[field] = form_data[field]
            num_service_units = extra_fields.pop('num_service_units')

            request_kwargs = {
                'requester': requester,
                'project': project,
                'status': AllocationAdditionRequestStatusChoice.objects.get(
                    name='Under Review'),
                'num_service_units': num_service_units,
                'extra_fields': extra_fields,
            }
            request = AllocationAdditionRequest.objects.create(
                **request_kwargs)

            log_message = (
                f'User {requester.pk} created AllocationAdditionRequest '
                f'{request.pk} to purchase {num_service_units} Service Units '
                f'for Project {project.pk}.')
            logger.info(log_message)
        except Exception as e:
            log_message = (
                f'Encountered unexpected exception when creating an '
                f'AllocationAdditionRequest by User {requester.pk} to '
                f'purchase {num_service_units} Service Units for Project '
                f'{project.pk}. Details:')
            logger.error(log_message)
            logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Set the following variables:
            - project: Project instance
        """
        context = super().get_context_data(**kwargs)
        context['project'] = self.project_obj
        return context

    def get_success_url(self):
        """Redirect to the Project Detail view on success."""
        return reverse('project-detail', kwargs={'pk': self.project_obj.pk})

    def test_func(self):
        """Allow active PIs and Managers of the Project who have signed
        the User Access Agreement."""
        user = self.request.user
        if not access_agreement_signed(user):
            message = 'You must sign the User Access Agreement.'
            messages.error(self.request, message)
            return False
        if is_user_manager_or_pi_of_project(user, self.project_obj):
            return True
        message = 'You must be an active PI or manager of the Project.'
        messages.error(self.request, message)
