from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.forms import MemorandumSignedForm
from coldfront.core.project.forms import ReviewDenyForm
from coldfront.core.project.forms import ReviewStatusForm
from coldfront.core.project.forms_.new_project_forms.approval_forms import SavioProjectReviewAllocationDatesForm
from coldfront.core.project.forms_.new_project_forms.approval_forms import SavioProjectReviewSetupForm
from coldfront.core.project.forms_.new_project_forms.approval_forms import VectorProjectReviewSetupForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectICAExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectRechargeExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectSurveyForm
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.utils_.new_project_utils import project_allocation_request_latest_update_timestamp
from coldfront.core.project.utils_.new_project_utils import ProjectDenialRunner
from coldfront.core.project.utils_.new_project_utils import SavioProjectApprovalRunner
from coldfront.core.project.utils_.new_project_utils import savio_request_state_status
from coldfront.core.project.utils_.new_project_utils import send_project_request_pooling_email
from coldfront.core.project.utils_.new_project_utils import VectorProjectApprovalRunner
from coldfront.core.project.utils_.new_project_utils import vector_request_state_status
from coldfront.core.utils.common import utc_now_offset_aware

from datetime import datetime
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
from django.views import View
from django.views.generic import DetailView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

import iso8601
import logging
import pytz


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

        return SavioProjectAllocationRequest.objects.order_by(order_by)

    def get_context_data(self, **kwargs):
        """Include either pending or completed requests. If the user is
        a superuser, show all such requests. Otherwise, show only those
        for which the user is a requester or PI."""
        context = super().get_context_data(**kwargs)
        args, kwargs = [], {}

        request_list = self.get_queryset()
        user = self.request.user
        if not (user.is_superuser or user.has_perm('project.view_savioprojectallocationrequest')):
            args.append(Q(requester=user) | Q(pi=user))
        if self.completed:
            status__name__in = ['Approved - Complete', 'Denied']
        else:
            status__name__in = ['Under Review', 'Approved - Processing']
        kwargs['status__name__in'] = status__name__in
        context['savio_project_request_list'] = request_list.filter(
            *args, **kwargs)
        context['request_filter'] = (
            'completed' if self.completed else 'pending')

        return context


class SavioProjectRequestMixin(object):

    @staticmethod
    def get_extra_fields_form(allocation_type, extra_fields):
        kwargs = {
            'initial': extra_fields,
            'disable_fields': True,
        }
        if allocation_type == SavioProjectAllocationRequest.ICA:
            form = SavioProjectICAExtraFieldsForm
        elif allocation_type == SavioProjectAllocationRequest.RECHARGE:
            form = SavioProjectRechargeExtraFieldsForm
        else:
            form = SavioProjectExtraFieldsForm
        return form(**kwargs)


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
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)

        try:
            context['allocation_amount'] = \
                self.__get_service_units_to_allocate()
        except Exception as e:
            self.logger.exception(e)
            messages.error(self.request, self.error_message)
            context['allocation_amount'] = 'Failed to compute.'

        try:
            latest_update_timestamp = \
                project_allocation_request_latest_update_timestamp(
                    self.request_obj)
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

        context['setup_status'] = self.__get_setup_status()
        context['is_checklist_complete'] = self.__is_checklist_complete()

        context['is_allowed_to_manage_request'] = self.request.user.is_superuser

        return context

    def post(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            message = 'You do not have permission to access this page.'
            messages.error(request, message)
            pk = self.request_obj.pk

            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))

        if not self.__is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        try:
            num_service_units = self.__get_service_units_to_allocate()
            runner = SavioProjectApprovalRunner(
                self.request_obj, num_service_units)
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
        try:
            for message in runner.get_user_messages():
                messages.info(self.request, message)
        except NameError:
            pass

        return HttpResponseRedirect(self.redirect)

    def __get_service_units_to_allocate(self):
        """Return the number of service units to allocate to the project
        if it were to be approved now.

        If the request was created as part of an allocation renewal, it
        may be associated with at most one AllocationRenewalRequest. If
        so, service units will be allocated when the latter request is
        approved."""
        if AllocationRenewalRequest.objects.filter(
                new_project_request=self.request_obj).exists():
            return settings.ALLOCATION_MIN

        allocation_type = self.request_obj.allocation_type
        now = utc_now_offset_aware()
        if allocation_type == SavioProjectAllocationRequest.CO:
            return settings.CO_DEFAULT_ALLOCATION
        elif allocation_type == SavioProjectAllocationRequest.FCA:
            return prorated_allocation_amount(
                settings.FCA_DEFAULT_ALLOCATION, now)
        elif allocation_type == SavioProjectAllocationRequest.ICA:
            return settings.ICA_DEFAULT_ALLOCATION
        elif allocation_type == SavioProjectAllocationRequest.PCA:
            return prorated_allocation_amount(
                settings.PCA_DEFAULT_ALLOCATION, now)
        elif allocation_type == SavioProjectAllocationRequest.RECHARGE:
            num_service_units = \
                self.request_obj.extra_fields['num_service_units']
            return Decimal(f'{num_service_units:.2f}')
        else:
            raise ValueError(f'Invalid allocation_type {allocation_type}.')

    def __get_setup_status(self):
        """Return one of the following statuses for the 'setup' step of
        the request: 'N/A', 'Pending', 'Complete'."""
        allocation_type = self.request_obj.allocation_type
        state = self.request_obj.state
        if (state['eligibility']['status'] == 'Denied' or
                state['readiness']['status'] == 'Denied'):
            return 'N/A'
        else:
            pending = 'Pending'
            ica = SavioProjectAllocationRequest.ICA
            recharge = SavioProjectAllocationRequest.RECHARGE
            if allocation_type in (ica, recharge):
                if allocation_type == ica:
                    if state['allocation_dates']['status'] == pending:
                        return pending
                if state['memorandum_signed']['status'] == pending:
                    return pending
        return state['setup']['status']

    def __is_checklist_complete(self):
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
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
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
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
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
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
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
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
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


class SavioProjectReviewAllocationDatesView(LoginRequiredMixin,
                                            UserPassesTestMixin,
                                            SavioProjectRequestMixin,
                                            FormView):
    form_class = SavioProjectReviewAllocationDatesForm
    template_name = (
        'project/project_request/savio/project_review_allocation_dates.html')
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
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        allocation_type = self.request_obj.allocation_type
        if allocation_type != SavioProjectAllocationRequest.ICA:
            message = (
                f'This view is not applicable for projects with allocation '
                f'type {allocation_type}.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        status = form_data['status']
        timestamp = utc_now_offset_aware().isoformat()

        # The allocation starts at the beginning of the start date and ends at
        # the end of the end date.
        local_tz = pytz.timezone('America/Los_Angeles')
        tz = pytz.timezone(settings.TIME_ZONE)
        if form_data['start_date']:
            naive_dt = datetime.datetime.combine(
                form_data['start_date'], datetime.datetime.min.time())
            start = local_tz.localize(naive_dt).astimezone(tz).isoformat()
        else:
            start = ''
        if form_data['end_date']:
            naive_dt = datetime.datetime.combine(
                form_data['end_date'], datetime.datetime.max.time())
            end = local_tz.localize(naive_dt).astimezone(tz).isoformat()
        else:
            end = ''

        self.request_obj.state['allocation_dates'] = {
            'status': status,
            'dates': {
                'start': start,
                'end': end,
            },
            'timestamp': timestamp,
        }

        self.request_obj.status = savio_request_state_status(self.request_obj)
        self.request_obj.save()

        message = (
            f'Allocation Dates status for request {self.request_obj.pk} has '
            f'been set to {status}.')
        messages.success(self.request, message)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['savio_request'] = self.request_obj
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
        context['survey_form'] = SavioProjectSurveyForm(
            initial=self.request_obj.survey_answers, disable_fields=True)
        return context

    def get_initial(self):
        initial = super().get_initial()
        allocation_dates = self.request_obj.state['allocation_dates']
        initial['status'] = allocation_dates['status']
        local_tz = pytz.timezone('America/Los_Angeles')
        for key in ('start', 'end'):
            value = allocation_dates['dates'][key]
            if value:
                initial[f'{key}_date'] = iso8601.parse_date(value).astimezone(
                    pytz.utc).astimezone(local_tz).date()
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
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        allocation_type = self.request_obj.allocation_type
        memorandum_types = (
            SavioProjectAllocationRequest.ICA,
            SavioProjectAllocationRequest.RECHARGE,
        )
        if allocation_type not in memorandum_types:
            message = (
                f'This view is not applicable for projects with allocation '
                f'type {allocation_type}.')
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
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
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
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
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
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
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
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
        self.request_obj = get_object_or_404(
            SavioProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('savio-project-request-detail', kwargs={'pk': pk}))
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
        context['extra_fields_form'] = self.get_extra_fields_form(
            self.request_obj.allocation_type, self.request_obj.extra_fields)
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
                                    View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to undeny a project request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        project_request = get_object_or_404(
            SavioProjectAllocationRequest, pk=self.kwargs.get('pk'))

        state_status = savio_request_state_status(project_request)
        denied_status = ProjectAllocationRequestStatusChoice.objects.get(
            name='Denied')

        if state_status != denied_status:
            message = 'Savio project request has an unexpected status.'
            messages.error(request, message)

            return HttpResponseRedirect(
                reverse('savio-project-request-detail',
                        kwargs={'pk': self.kwargs.get('pk')}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        project_request = get_object_or_404(
            SavioProjectAllocationRequest, pk=kwargs.get('pk'))

        if project_request.state['eligibility']['status'] == 'Denied':
            project_request.state['eligibility']['status'] = 'Pending'

        if project_request.state['readiness']['status'] == 'Denied':
            project_request.state['readiness']['status'] = 'Pending'

        if project_request.state['other']['timestamp']:
            project_request.state['other']['justification'] = ''
            project_request.state['other']['timestamp'] = ''

        project_request.status = savio_request_state_status(project_request)
        project_request.save()

        message = (
            f'Project request {project_request.project.name} '
            f'has been UNDENIED and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse('savio-project-request-detail',
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


class VectorProjectRequestDetailView(LoginRequiredMixin, UserPassesTestMixin,
                                     DetailView):
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
        self.request_obj = get_object_or_404(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            latest_update_timestamp = \
                project_allocation_request_latest_update_timestamp(
                    self.request_obj)
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

        context['is_checklist_complete'] = self.__is_checklist_complete()

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

        if not self.__is_checklist_complete():
            message = 'Please complete the checklist before final activation.'
            messages.error(request, message)
            pk = self.request_obj.pk
            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))
        try:
            runner = VectorProjectApprovalRunner(self.request_obj)
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
        try:
            for message in runner.get_user_messages():
                messages.info(self.request, message)
        except NameError:
            pass

        return HttpResponseRedirect(self.redirect)

    def __is_checklist_complete(self):
        status_choice = vector_request_state_status(self.request_obj)
        return (status_choice.name == 'Approved - Processing' and
                self.request_obj.state['setup']['status'] == 'Complete')


class VectorProjectReviewEligibilityView(LoginRequiredMixin,
                                         UserPassesTestMixin, FormView):
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
        self.request_obj = get_object_or_404(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))
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
                                   FormView):
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
        self.request_obj = get_object_or_404(
            VectorProjectAllocationRequest.objects.prefetch_related(
                'pi', 'project', 'requester'), pk=pk)
        status_name = self.request_obj.status.name
        if status_name in ['Approved - Complete', 'Denied']:
            message = f'You cannot review a request with status {status_name}.'
            messages.error(request, message)
            return HttpResponseRedirect(
                reverse('vector-project-request-detail', kwargs={'pk': pk}))
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
                                     View):
    login_url = '/'

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        message = (
            'You do not have permission to undeny a project request.')
        messages.error(self.request, message)

    def dispatch(self, request, *args, **kwargs):
        project_request = get_object_or_404(
            VectorProjectAllocationRequest, pk=self.kwargs.get('pk'))

        state_status = vector_request_state_status(project_request)
        denied_status = ProjectAllocationRequestStatusChoice.objects.get(name='Denied')

        if state_status != denied_status:
            message = 'Vector project request has an unexpected status.'
            messages.error(request, message)

            return HttpResponseRedirect(
                reverse('vector-project-request-detail',
                        kwargs={'pk': self.kwargs.get('pk')}))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        project_request = get_object_or_404(
            VectorProjectAllocationRequest, pk=kwargs.get('pk'))

        if project_request.state['eligibility']['status'] == 'Denied':
            project_request.state['eligibility']['status'] = 'Pending'

        project_request.status = vector_request_state_status(project_request)
        project_request.save()

        message = (
            f'Project request {project_request.project.name} '
            f'has been UNDENIED and will need to be reviewed again.')
        messages.success(request, message)

        return HttpResponseRedirect(
            reverse('vector-project-request-detail',
                    kwargs={'pk': kwargs.get('pk')}))
