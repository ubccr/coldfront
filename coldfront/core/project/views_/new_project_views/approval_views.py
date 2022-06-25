from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.utils import annotate_queryset_with_allocation_period_not_started_bool
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.forms import MemorandumSignedForm
from coldfront.core.project.forms import ReviewDenyForm
from coldfront.core.project.forms import ReviewStatusForm
from coldfront.core.project.forms_.new_project_forms.approval_forms import SavioProjectReviewSetupForm
from coldfront.core.project.forms_.new_project_forms.approval_forms import VectorProjectReviewSetupForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectICAExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectRechargeExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectSurveyForm
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.utils_.new_project_utils import ProjectDenialRunner
from coldfront.core.project.utils_.new_project_utils import SavioProjectApprovalRunner
from coldfront.core.project.utils_.new_project_utils import SavioProjectProcessingRunner
from coldfront.core.project.utils_.new_project_utils import savio_request_state_status
from coldfront.core.project.utils_.new_project_utils import send_project_request_pooling_email
from coldfront.core.project.utils_.new_project_utils import VectorProjectProcessingRunner
from coldfront.core.project.utils_.new_project_utils import vector_request_state_status
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import format_date_month_name_day_year
from coldfront.core.utils.common import utc_now_offset_aware

from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from flags.state import flag_enabled

import iso8601
import logging


# =============================================================================
# BRC: SAVIO
# =============================================================================


class SavioProjectRequestListView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_request/savio/project_request_list.html'
    login_url = '/'
    # Show completed requests if True; else, show pending requests.
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
            SavioProjectAllocationRequest.objects.order_by(order_by))

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)
        args, kwargs = [], {}

        request_list = self.get_queryset()
        user = self.request.user
        permission = 'project.view_savioprojectallocationrequest'
        if not (user.is_superuser or user.has_perm(permission)):
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = [
                'Approved - Complete', 'Approved - Scheduled', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']
        kwargs['status__name__in'] = status__name__in
        context['savio_project_request_list'] = request_list.filter(
            *args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class SavioProjectRequestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interface = ComputingAllowanceInterface()
        self.request_obj = None

    def assert_request_set(self):
        """Assert that the request_obj has been set."""
        assert isinstance(self.request_obj, SavioProjectAllocationRequest)

    def get_extra_fields_form(self):
        """Return a form of extra fields for the request, based on its
        computing allowance, and populated with initial data."""
        self.assert_request_set()
        computing_allowance = self.request_obj.computing_allowance
        extra_fields = self.request_obj.extra_fields

        kwargs = {
            'initial': extra_fields,
            'disable_fields': True,
        }

        allowance_name = computing_allowance.name
        form = SavioProjectExtraFieldsForm
        if flag_enabled('BRC_ONLY'):
            if allowance_name == BRCAllowances.ICA:
                form = SavioProjectICAExtraFieldsForm
            elif allowance_name == BRCAllowances.RECHARGE:
                form = SavioProjectRechargeExtraFieldsForm
        elif flag_enabled('LRC_ONLY'):
            if allowance_name == LRCAllowances.RECHARGE:
                # TODO
                form = SavioProjectRechargeExtraFieldsForm

        return form(**kwargs)

    def get_survey_form(self):
        """Return a disabled form containing the survey answers for the
        request."""
        self.assert_request_set()
        survey_answers = self.request_obj.survey_answers
        kwargs = {
            'initial': survey_answers,
            'disable_fields': True,
        }
        # TODO
        return SavioProjectSurveyForm(**kwargs)

    def redirect_if_disallowed_status(self, http_request,
                                      disallowed_status_names=(
            'Approved - Scheduled', 'Approved - Complete', 'Denied')):
        """Return a redirect response to the detail view for this
        project request if its status has one of the given disallowed
        names, after sending a message to the user. Otherwise, return
        None."""
        self.assert_request_set()
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
        return reverse('savio-project-request-detail', kwargs={'pk': pk})

    def requires_memorandum_of_understanding(self):
        """Return whether this request requires an MOU to be signed."""
        self.assert_request_set()
        allowance_name = self.request_obj.computing_allowance.name
        relevant_allowance_names = []
        if flag_enabled('BRC_ONLY'):
            relevant_allowance_names.append(BRCAllowances.ICA)
            relevant_allowance_names.append(BRCAllowances.RECHARGE)
        elif flag_enabled('LRC_ONLY'):
            relevant_allowance_names.append(LRCAllowances.RECHARGE)
        return allowance_name in relevant_allowance_names

    def requires_service_unit_prorating(self):
        """Return whether this request's service units should be
        prorated."""
        self.assert_request_set()
        allowance_name = self.request_obj.computing_allowance.name
        relevant_allowance_names = []
        if flag_enabled('BRC_ONLY'):
            relevant_allowance_names.append(BRCAllowances.FCA)
            relevant_allowance_names.append(BRCAllowances.PCA)
        elif flag_enabled('LRC_ONLY'):
            relevant_allowance_names.append(LRCAllowances.PCA)
        return allowance_name in relevant_allowance_names

    def set_request_obj(self, pk):
        """Set this instance's request_obj to be the
        SavioProjectAllocationRequest with the given primary key."""
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)


class SavioProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                    SavioProjectRequestMixin, DetailView):
    model = SavioProjectAllocationRequest
    template_name = 'project/project_request/savio/project_request_detail.html'
    login_url = '/'
    context_object_name = 'savio_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    redirect = reverse_lazy('savio-project-pending-request-list')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perm('project.view_savioprojectallocationrequest'):
            return True

        if (self.request.user == self.request_obj.requester or
                self.request.user == self.request_obj.pi):
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

        context['extra_fields_form'] = self.get_extra_fields_form()
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)

        try:
            context['allocation_amount'] = self.get_service_units_to_allocate()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            context['allocation_amount'] = 'Failed to compute.'

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

        context['has_allocation_period_started'] = \
            self.has_request_allocation_period_started()
        context['setup_status'] = self.get_setup_status()
        context['is_checklist_complete'] = self.is_checklist_complete()

        context['is_allowed_to_manage_request'] = \
            self.request.user.is_superuser

        return context

    def post(self, request, *args, **kwargs):
        """Approve the request. Process it if its AllocationPeriod has
        already started."""
        if not self.request.user.is_superuser:
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))

        if not self.is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))

        processing_runner = None
        project = self.request_obj.project
        try:
            has_allocation_period_started = \
                self.has_request_allocation_period_started()
            num_service_units = self.get_service_units_to_allocate()

            # Skip sending an approval email if a processing email will be sent
            # immediately afterward.
            approval_runner = SavioProjectApprovalRunner(
                self.request_obj, num_service_units,
                send_email=not has_allocation_period_started)
            approval_runner.run()

            if has_allocation_period_started:
                self.request_obj.refresh_from_db()
                processing_runner = SavioProjectProcessingRunner(
                    self.request_obj, num_service_units)
                project, _ = processing_runner.run()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            if not has_allocation_period_started:
                formatted_start_date = format_date_month_name_day_year(
                    self.request_obj.allocation_period.start_date)
                phrase = (
                    f'are scheduled for activation on {formatted_start_date}. '
                    f'A cluster access request will automatically be made for '
                    f'the requester then.')
            else:
                phrase = (
                    'have been activated. A cluster access request has '
                    'automatically been made for the requester.')
            message = f'Project {project.name} and its Allocation {phrase}'
            messages.success(self.request, message)
            self.logger.info(message)

        # Send any messages from the runner back to the user.
        if isinstance(processing_runner, SavioProjectProcessingRunner):
            try:
                for message in processing_runner.get_user_messages():
                    messages.info(self.request, message)
            except NameError:
                pass

        return HttpResponseRedirect(self.redirect)

    def get_service_units_to_allocate(self):
        """Return the possibly-prorated number of service units to
        allocate to the project.

        If the request was created as part of an allocation renewal, it
        may be associated with at most one AllocationRenewalRequest. If
        so, service units will be allocated when the latter request is
        approved."""
        if AllocationRenewalRequest.objects.filter(
                new_project_request=self.request_obj).exists():
            return settings.ALLOCATION_MIN

        # For RECHARGE, the user specifies the number of service units.
        if flag_enabled('BRC_ONLY'):
            recharge = BRCAllowances.RECHARGE
        elif flag_enabled('LRC_ONLY'):
            recharge = LRCAllowances.RECHARGE
        else:
            raise ImproperlyConfigured(
                'One of the following flags must be enabled: BRC_ONLY, '
                'LRC_ONLY.')

        allowance_name = self.request_obj.computing_allowance.name
        if allowance_name == recharge:
            num_service_units_int = self.request_obj.extra_fields[
                'num_service_units']
            num_service_units = Decimal(f'{num_service_units_int:.2f}')
        else:
            num_service_units = Decimal(
                self.interface.service_units_from_name(allowance_name))
            if self.requires_service_unit_prorating():
                num_service_units = prorated_allocation_amount(
                    num_service_units, self.request_obj.request_time,
                    self.request_obj.allocation_period)
        return num_service_units

    def get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        state = self.request_obj.state
        if (state['eligibility']['status'] == 'Denied' or
                state['readiness']['status'] == 'Denied'):
            return 'N/A'
        else:
            pending = 'Pending'
            if self.requires_memorandum_of_understanding():
                if state['memorandum_signed']['status'] == pending:
                    return pending
        return state['setup']['status']

    def has_request_allocation_period_started(self):
        """Return whether the request's AllocationPeriod has started. If
        the request has no period, return True."""
        allocation_period = self.request_obj.allocation_period
        if not allocation_period:
            return True
        return allocation_period.start_date <= display_time_zone_current_date()

    def is_checklist_complete(self):
        status_choice = savio_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Complete')


class SavioProjectReviewEligibilityView(LoginRequiredMixin,
                                        UserPassesTestMixin,
                                        SavioProjectRequestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/savio/project_review_eligibility.html')
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
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['eligibility'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = savio_request_state_status(self.request_obj)

        if status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Eligibility status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form()
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.request_obj.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewReadinessView(LoginRequiredMixin, UserPassesTestMixin,
                                      SavioProjectRequestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/savio/project_review_readiness.html')
    login_url = '/'

    logger = logging.getLogger(__name__)

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
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['readiness'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = savio_request_state_status(self.request_obj)

        if status == 'Approved':
            if self.request_obj.pool:
                try:
                    send_project_request_pooling_email(self.request_obj)
                except Exception as e:
                    self.logger.error(
                        'Failed to send notification email. Details:\n')
                    self.logger.exception(e)
        elif status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Readiness status for request {self.request_obj.pk} has been set '
            f'to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['extra_fields_form'] = self.get_extra_fields_form()
        context['savio_request'] = self.request_obj
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        readiness = self.request_obj.state['readiness']
        initial['status'] = readiness['status']
        initial['justification'] = readiness['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewMemorandumSignedView(LoginRequiredMixin,
                                             UserPassesTestMixin,
                                             SavioProjectRequestMixin,
                                             FormView):
    form_class = MemorandumSignedForm
    template_name = (
        'project/project_request/savio/project_review_memorandum_signed.html')
    login_url = '/'

    logger = logging.getLogger(__name__)

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
        if not self.requires_memorandum_of_understanding():
            message = (
                'A memorandum of understanding does not need to be signed for '
                'this request.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        redirect = self.redirect_if_disallowed_status(request)
        if redirect is not None:
            return redirect
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        timestamp = utc_now_offset_aware().isoformat()

        self.request_obj.state['memorandum_signed'] = {
            'status': status,
            'timestamp': timestamp,
        }

        self.request_obj.status = savio_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Memorandum Signed status for request {self.request_obj.pk} has '
            f'been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form()
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        memorandum_signed = self.request_obj.state['memorandum_signed']
        initial['status'] = memorandum_signed['status']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewSetupView(LoginRequiredMixin, UserPassesTestMixin,
                                  SavioProjectRequestMixin, FormView):
    form_class = SavioProjectReviewSetupForm
    template_name = 'project/project_request/savio/project_review_setup.html'
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
        status = form_data['status']
        requested_name = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        final_name = form_data['final_name']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()

        name_change = {
            'requested_name': requested_name,
            'final_name': final_name,
            'justification': justification,
        }
        self.request_obj.state['setup'] = {
            'status': status,
            'name_change': name_change,
            'timestamp': timestamp,
        }

        # Set the Project's name. This is the only modification performed prior
        # to the final submission because the name must be unique.
        self.request_obj.project.name = final_name
        self.request_obj.project.save()

        self.request_obj.status = savio_request_state_status(self.request_obj)

        self.request_obj.save()

        message = (
            f'Setup status for request {self.request_obj.pk} has been set to '
            f'{status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form()
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.request_obj.project.pk
        kwargs['requested_name'] = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        setup = self.request_obj.state['setup']
        initial['status'] = setup['status']
        initial['final_name'] = setup['name_change']['final_name']
        initial['justification'] = setup['name_change']['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectReviewDenyView(LoginRequiredMixin, UserPassesTestMixin,
                                 SavioProjectRequestMixin, FormView):
    form_class = ReviewDenyForm
    template_name = (
        'project/project_request/savio/project_review_deny.html')
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
        self.request_obj.status = savio_request_state_status(self.request_obj)

        runner = ProjectDenialRunner(self.request_obj)
        runner.run()

        self.request_obj.save()

        message = (
            f'Status for {self.request_obj.pk} has been set to '
            f'{self.request_obj.status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form()
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        other = self.request_obj.state['other']
        initial['justification'] = other['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'savio-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class SavioProjectUndenyRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                    SavioProjectRequestMixin, View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to undeny a project request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)

        disallowed_status_names = list(
            ProjectAllocationRequestStatusChoice.objects.filter(
                ~Q(name='Denied')).values_list('name', flat=True))
        redirect = self.redirect_if_disallowed_status(
            request, disallowed_status_names=disallowed_status_names)
        if redirect is not None:
            return redirect

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        state = self.request_obj.state

        eligibility = state['eligibility']
        if eligibility['status'] == 'Denied':
            eligibility['status'] = 'Pending'

        readiness = state['readiness']
        if readiness['status'] == 'Denied':
            readiness['status'] = 'Pending'

        other = state['other']
        if other['timestamp']:
            other['justification'] = ''
            other['timestamp'] = ''

        self.request_obj.status = savio_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Project request {self.request_obj.project.name} has been '
            f'un-denied and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse(
                'savio-project-request-detail',
                kwargs={'pk': kwargs.get('pk')}))


# =============================================================================
# BRC: VECTOR
# =============================================================================

class VectorProjectRequestListView(LoginRequiredMixin, TemplateView):
    template_name = 'project/project_request/vector/project_request_list.html'
    login_url = '/'
    # Show completed requests if True; else, show pending requests.
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
        return VectorProjectAllocationRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)

        args, kwargs = [], {}

        user = self.request.user

        request_list = self.get_queryset()
        permission = 'project.view_vectorprojectallocationrequest'
        if not (user.is_superuser or user.has_perm(permission)):
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = ['Approved - Complete', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']
        kwargs['status__name__in'] = status__name__in
        context['vector_project_request_list'] = request_list.filter(
            *args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class VectorProjectRequestMixin(object):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_obj = None

    def redirect_if_disallowed_status(self, http_request,
                                      disallowed_status_names=(
            'Approved - Complete', 'Denied')):
        """Return a redirect response to the detail view for this
        project request if its status has one of the given disallowed
        names, after sending a message to the user. Otherwise, return
        None."""
        if not isinstance(self.request_obj, VectorProjectAllocationRequest):
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
        return reverse('vector-project-request-detail', kwargs={'pk': pk})

    def set_request_obj(self, pk):
        """Set this instance's request_obj to be the
        VectorProjectAllocationRequest with the given primary key."""
        self.request_obj = get_object_or_404(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)


class VectorProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                     VectorProjectRequestMixin, DetailView):
    model = VectorProjectAllocationRequest
    template_name = (
        'project/project_request/vector/project_request_detail.html')
    login_url = '/'
    context_object_name = 'vector_request'

    logger = logging.getLogger(__name__)

    error_message = 'Unexpected failure. Please contact an administrator.'

    redirect = reverse_lazy('vector-project-pending-request-list')

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        permission = 'project.view_vectorprojectallocationrequest'
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

        context['is_checklist_complete'] = self.is_checklist_complete()

        context['is_allowed_to_manage_request'] = (
            self.request.user.is_superuser)

        return context

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            message = 'You do not have permission to view the this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))

        if not self.is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))

        runner = None
        try:
            runner = VectorProjectProcessingRunner(self.request_obj)
            project, allocation = runner.run()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            message = (
                f'Project {project.name} and Allocation {allocation.pk} have '
                f'been activated. A cluster access request has automatically '
                f'been made for the requester.')
            messages.success(self.request, message)

        # Send any messages from the runner back to the user.
        if isinstance(runner, VectorProjectProcessingRunner):
            try:
                for message in runner.get_user_messages():
                    messages.info(self.request, message)
            except NameError:
                pass

        return HttpResponseRedirect(self.redirect)

    def is_checklist_complete(self):
        status_choice = vector_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Complete')


class VectorProjectReviewEligibilityView(LoginRequiredMixin,
                                         UserPassesTestMixin,
                                         VectorProjectRequestMixin, FormView):
    form_class = ReviewStatusForm
    template_name = (
        'project/project_request/vector/project_review_eligibility.html')
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
        status = form_data['status']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()
        self.request_obj.state['eligibility'] = {
            'status': status,
            'justification': justification,
            'timestamp': timestamp,
        }
        self.request_obj.status = vector_request_state_status(self.request_obj)

        if status == 'Denied':
            runner = ProjectDenialRunner(self.request_obj)
            runner.run()

        self.request_obj.save()

        message = (
            f'Eligibility status for request {self.request_obj.pk} has been '
            f'set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vector_request'] = self.request_obj
        return context

    def get_initial(self):
        initial = super().get_initial()
        eligibility = self.request_obj.state['eligibility']
        initial['status'] = eligibility['status']
        initial['justification'] = eligibility['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'vector-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class VectorProjectReviewSetupView(LoginRequiredMixin, UserPassesTestMixin,
                                   VectorProjectRequestMixin, FormView):
    form_class = VectorProjectReviewSetupForm
    template_name = 'project/project_request/vector/project_review_setup.html'
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
        status = form_data['status']
        requested_name = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        final_name = form_data['final_name']
        justification = form_data['justification']
        timestamp = utc_now_offset_aware().isoformat()

        name_change = {
            'requested_name': requested_name,
            'final_name': final_name,
            'justification': justification,
        }
        self.request_obj.state['setup'] = {
            'status': status,
            'name_change': name_change,
            'timestamp': timestamp,
        }

        # Set the Project's name. This is the only modification performed prior
        # to the final submission because the name must be unique.
        self.request_obj.project.name = final_name
        self.request_obj.project.save()

        self.request_obj.status = vector_request_state_status(self.request_obj)

        self.request_obj.save()

        message = (
            f'Setup status for request {self.request_obj.pk} has been set to '
            f'{status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vector_request'] = self.request_obj
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.request_obj.project.pk
        kwargs['requested_name'] = (
            self.request_obj.state['setup']['name_change']['requested_name'])
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        setup = self.request_obj.state['setup']
        initial['status'] = setup['status']
        initial['final_name'] = setup['name_change']['final_name']
        initial['justification'] = setup['name_change']['justification']
        return initial

    def get_success_url(self):
        return reverse(
            'vector-project-request-detail',
            kwargs={'pk': self.kwargs.get('pk')})


class VectorProjectUndenyRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                     VectorProjectRequestMixin, View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to undeny a project request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.set_request_obj(pk)

        disallowed_status_names = list(
            ProjectAllocationRequestStatusChoice.objects.filter(
                ~Q(name='Denied')).values_list('name', flat=True))
        redirect = self.redirect_if_disallowed_status(
            request, disallowed_status_names=disallowed_status_names)
        if redirect is not None:
            return redirect

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        state = self.request_obj.state

        eligibility = state['eligibility']
        if eligibility['status'] == 'Denied':
            eligibility['status'] = 'Pending'

        self.request_obj.status = vector_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Project request {self.request_obj.project.name} has been '
            f'un-denied and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse(
                'vector-project-request-detail',
                kwargs={'pk': kwargs.get('pk')}))
