from coldfront.core.project.models import Project
from coldfront.core.project.models import savio_project_request_recharge_extra_fields_schema
from coldfront.core.project.utils_.permissions_utils import can_project_buy_service_units
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project
from coldfront.core.project.utils_.permissions_utils import is_user_member_of_project
from coldfront.core.user.utils import access_agreement_signed

from decimal import Decimal
from decimal import DivisionByZero
from decimal import DivisionUndefined
from decimal import InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

"""Views relating to buying more Service Units for a Project."""


class AllocationAdditionRequestLandingView(LoginRequiredMixin,
                                           UserPassesTestMixin, TemplateView):
    """A view that provides information regarding buying more Service
    Units for the given Project. Eligible Project types include:
    Recharge."""

    template_name = 'project/project_allocation_addition/request_landing.html'
    login_url = '/'

    project_obj = None

    def dispatch(self, request, *args, **kwargs):
        """Store the Project object for reuse. If it is ineligible,
        redirect."""
        pk = self.kwargs.get('pk')
        self.project_obj = get_object_or_404(Project, pk=pk)

        if not can_project_buy_service_units(self.project_obj):
            message = (
                f'Project {self.project_obj.name} is ineligible to buy more '
                f'Service Units.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('project-detail', kwargs={'pk': self.project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Set the following variables:
            - project: Project instance
            - current_allowance: Decimal
            - current_usage: Decimal
            - usage_percentage: str
        """
        context = super().get_context_data(**kwargs)
        context['project'] = self.project_obj

        # TODO
        context['current_allowance'] = Decimal('0.00')
        context['current_usage'] = Decimal('0.00')
        try:
            quotient = (
                context['current_usage'] / context['current_allowance'])
        except (DivisionByZero, DivisionUndefined, InvalidOperation):
            quotient = Decimal('0.00')
        context['usage_percentage'] = f'{quotient * 100}%'

        return context

    def test_func(self):
        """Allow superusers and staff. Allow active project members who
        have signed the User Access Agreement."""
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return True
        if not access_agreement_signed(user):
            message = 'You must sign the User Access Agreement.'
            messages.error(self.request, message)
            return False
        if is_user_member_of_project(user, self.project_obj):
            return True
        message = 'You must be an active member of the Project.'
        messages.error(self.request, message)


class AllocationAdditionRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                    FormView):
    """A view for creating requests to buy more Service Units for the
    given Project."""

    template_name = 'project/project_allocation_addition/request_form.html'
    login_url = '/'

    project_obj = None

    def dispatch(self, request, *args, **kwargs):
        """Store the Project object for reuse. If it is ineligible,
        redirect."""
        pk = self.kwargs.get('pk')
        self.project_obj = get_object_or_404(Project, pk=pk)

        if not can_project_buy_service_units(self.project_obj):
            message = (
                f'Project {self.project_obj.name} is ineligible to buy more '
                f'Service Units.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('project-detail', kwargs={'pk': self.project_obj.pk}))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Create an AllocationAdditionRequest."""
        form_data = form.cleaned_data
        extra_fields = savio_project_request_recharge_extra_fields_schema()
        for field in extra_fields:
            extra_fields[field] = form_data[field]
        # TODO
        return super().form_valid(form)

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
