from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectAllocationPeriodForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectDetailsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectSurveyForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalPISelectionForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalPoolingPreferenceForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalProjectSelectionForm
from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalReviewAndSubmitForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.permissions_utils import is_user_manager_or_pi_of_project
from coldfront.core.project.utils_.renewal_utils import get_pi_current_active_fca_project
from coldfront.core.project.utils_.renewal_utils import has_non_denied_renewal_request
from coldfront.core.project.utils_.renewal_utils import send_new_allocation_renewal_request_admin_notification_email
from coldfront.core.project.utils_.renewal_utils import send_new_allocation_renewal_request_pi_notification_email
from coldfront.core.project.utils_.renewal_utils import send_new_allocation_renewal_request_pooling_notification_email
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import session_wizard_all_form_data
from coldfront.core.utils.common import utc_now_offset_aware

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from formtools.wizard.views import SessionWizardView

import logging


logger = logging.getLogger(__name__)


class AllocationRenewalMixin(object):

    success_message = (
        'Thank you for your submission. It will be reviewed and processed by '
        'administrators.')
    error_message = 'Unexpected failure. Please contact an administrator.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def create_allocation_renewal_request(requester, pi, allocation_period,
                                          pre_project, post_project,
                                          new_project_request=None):
        """Create a new AllocationRenewalRequest."""
        request_kwargs = dict()
        request_kwargs['requester'] = requester
        request_kwargs['pi'] = pi
        request_kwargs['allocation_period'] = allocation_period
        request_kwargs['status'] = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        request_kwargs['pre_project'] = pre_project
        request_kwargs['post_project'] = post_project
        request_kwargs['new_project_request'] = new_project_request
        request_kwargs['request_time'] = utc_now_offset_aware()
        return AllocationRenewalRequest.objects.create(**request_kwargs)

    @staticmethod
    def send_emails(request_obj):
        """Send emails to various recipients based on the given, newly-
        created AllocationRenewalRequest."""
        # Send a notification email to admins.
        try:
            send_new_allocation_renewal_request_admin_notification_email(
                request_obj)
        except Exception as e:
            logger.error(f'Failed to send notification email. Details:\n')
            logger.exception(e)
        # Send a notification email to the PI if the requester differs.
        if request_obj.requester != request_obj.pi:
            try:
                send_new_allocation_renewal_request_pi_notification_email(
                    request_obj)
            except Exception as e:
                logger.error(
                    f'Failed to send notification email. Details:\n')
                logger.exception(e)
        # If applicable, send a notification email to the managers and PIs of
        # the project being requested to pool with.
        if (request_obj.pi not in request_obj.post_project.pis() and
                not request_obj.new_project_request):
            try:
                send_new_allocation_renewal_request_pooling_notification_email(
                    request_obj)
            except Exception as e:
                logger.error(
                    f'Failed to send notification email. Details:\n')
                logger.exception(e)


class AllocationRenewalRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                   AllocationRenewalMixin, SessionWizardView):

    FORMS = [
        ('allocation_period', SavioProjectAllocationPeriodForm),
        ('pi_selection', ProjectRenewalPISelectionForm),
        ('pooling_preference', ProjectRenewalPoolingPreferenceForm),
        ('project_selection', ProjectRenewalProjectSelectionForm),
        ('new_project_details', SavioProjectDetailsForm),
        ('new_project_survey', SavioProjectSurveyForm),
        ('review_and_submit', ProjectRenewalReviewAndSubmitForm),
    ]

    TEMPLATES = {
        'allocation_period': 'project/project_renewal/allocation_period.html',
        'pi_selection': 'project/project_renewal/pi_selection.html',
        'pooling_preference':
            'project/project_renewal/pooling_preference.html',
        'project_selection': 'project/project_renewal/project_selection.html',
        'new_project_details':
            'project/project_renewal/new_project_details.html',
        'new_project_survey':
            'project/project_renewal/new_project_survey.html',
        'review_and_submit': 'project/project_renewal/review_and_submit.html',
    }

    form_list = [
        SavioProjectAllocationPeriodForm,
        ProjectRenewalPISelectionForm,
        ProjectRenewalPoolingPreferenceForm,
        ProjectRenewalProjectSelectionForm,
        SavioProjectDetailsForm,
        SavioProjectSurveyForm,
        ProjectRenewalReviewAndSubmitForm,
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define a lookup table from form name to step number.
        self.step_numbers_by_form_name = {
            name: i for i, (name, _) in enumerate(self.FORMS)}

    def test_func(self):
        """Allow superusers and users who are active Managers or
        Principal Investigators on at least one Project to access the
        view."""
        user = self.request.user
        if self.request.user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is None:
            message = (
                'You must sign the User Access Agreement before you can '
                'request to renew a PI\'s allocation.')
            messages.error(self.request, message)
            return False
        role_names = ['Manager', 'Principal Investigator']
        status = ProjectUserStatusChoice.objects.get(name='Active')
        has_access = ProjectUser.objects.filter(
            user=user, role__name__in=role_names, status=status)
        if has_access:
            return True
        message = (
            'You must be an active Manager or Principal Investigator of a '
            'Project.')
        messages.error(self.request, message)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self.__set_data_from_previous_steps(current_step, context)
        return context

    def get_form_kwargs(self, step=None):
        # TODO: Set this dynamically when supporting other types.
        allocation_type = SavioProjectAllocationRequest.FCA
        kwargs = {}
        step = int(step)
        if step == self.step_numbers_by_form_name['allocation_period']:
            kwargs['allocation_type'] = allocation_type
        elif step == self.step_numbers_by_form_name['pi_selection']:
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['allocation_period_pk'] = getattr(
                tmp.get('allocation_period', None), 'pk', None)
            project_pks = []
            user = self.request.user
            role_names = ['Manager', 'Principal Investigator']
            status = ProjectUserStatusChoice.objects.get(name='Active')
            project_users = user.projectuser_set.filter(
                project__name__startswith='fc_',
                role__name__in=role_names,
                status=status)
            for project_user in project_users:
                project_pks.append(project_user.project.pk)
            kwargs['project_pks'] = project_pks
        elif step == self.step_numbers_by_form_name['pooling_preference']:
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['currently_pooled'] = ('current_project' in tmp and
                                          tmp['current_project'].is_pooled())
        elif step == self.step_numbers_by_form_name['project_selection']:
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['pi_pk'] = tmp['PI'].user.pk
            form_class = ProjectRenewalPoolingPreferenceForm
            choices = (
                form_class.UNPOOLED_TO_POOLED,
                form_class.POOLED_TO_POOLED_DIFFERENT,
            )
            kwargs['non_owned_projects'] = tmp['preference'] in choices
            if 'current_project' in tmp:
                kwargs['exclude_project_pk'] = tmp['current_project'].pk
        elif step == self.step_numbers_by_form_name['new_project_details']:
            kwargs['allocation_type'] = allocation_type
        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def done(self, form_list, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = '/'
        try:
            form_data = session_wizard_all_form_data(
                form_list, kwargs['form_dict'], len(self.form_list))
            tmp = {}
            self.__set_data_from_previous_steps(len(self.FORMS), tmp)
            pi = tmp['PI'].user
            allocation_period = tmp['allocation_period']

            # If the PI already has a non-denied request for the period, raise
            # an exception. Such PIs are not selectable in the 'pi_selection'
            # step, but a request could have been created between selection and
            # final submission.
            if has_non_denied_renewal_request(pi, allocation_period):
                raise Exception(
                    f'PI {pi.username} already has a non-denied '
                    f'AllocationRenewalRequest for AllocationPeriod '
                    f'{allocation_period.name}.')

            # If a new Project was requested, create it along with a
            # SavioProjectAllocationRequest.
            new_project_request = None
            form_class = ProjectRenewalPoolingPreferenceForm
            if tmp['preference'] == form_class.POOLED_TO_UNPOOLED_NEW:
                requested_project = self.__handle_create_new_project(form_data)
                survey_data = self.__get_survey_data(form_data)
                new_project_request = self.__handle_create_new_project_request(
                    pi, requested_project, survey_data)
            else:
                requested_project = tmp['requested_project']

            request = self.create_allocation_renewal_request(
                self.request.user, pi, allocation_period,
                tmp['current_project'], requested_project,
                new_project_request=new_project_request)

            self.send_emails(request)
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            messages.success(self.request, self.success_message)

        return HttpResponseRedirect(redirect_url)

    @staticmethod
    def condition_dict():
        view = AllocationRenewalRequestView
        return {
            '2': view.show_project_selection_form_condition,
            '3': view.show_new_project_forms_condition,
            '4': view.show_new_project_forms_condition,
        }

    def show_new_project_forms_condition(self):
        """Only show the forms needed for a new Project if the pooling
        preference is to create one."""
        step_name = 'pooling_preference'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        form_class = ProjectRenewalPoolingPreferenceForm
        return (cleaned_data.get('preference', None) ==
                form_class.POOLED_TO_UNPOOLED_NEW)

    def show_project_selection_form_condition(self):
        """Only show the form for selecting a Project if the pooling
        preference is to start pooling, to pool with a different
        Project, or to select a different Project owned by the PI."""
        step_name = 'pooling_preference'
        step = str(self.step_numbers_by_form_name[step_name])
        cleaned_data = self.get_cleaned_data_for_step(step) or {}
        form_class = ProjectRenewalPoolingPreferenceForm
        preferences = (
            form_class.UNPOOLED_TO_POOLED,
            form_class.POOLED_TO_POOLED_DIFFERENT,
            form_class.POOLED_TO_UNPOOLED_OLD,
        )
        return cleaned_data.get('preference', None) in preferences

    def __get_survey_data(self, form_data):
        """Return provided survey data."""
        step_number = self.step_numbers_by_form_name['new_project_survey']
        return form_data[step_number]

    def __handle_create_new_project(self, form_data):
        """Create a new project and an allocation to the Savio Compute
        resource. This method should only be invoked if a new Project"""
        step_number = self.step_numbers_by_form_name['new_project_details']
        data = form_data[step_number]

        # Create the new Project.
        status = ProjectStatusChoice.objects.get(name='New')
        try:
            project = Project.objects.create(
                name=data['name'],
                status=status,
                title=data['title'],
                description=data['description'])
        except IntegrityError as e:
            logger.error(
                f'Project {data["name"]} unexpectedly already exists.')
            raise e

        # Create an allocation to the "Savio Compute" resource.
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(project=project, status=status)
        resource = Resource.objects.get(name='Savio Compute')
        allocation.resources.add(resource)
        allocation.save()

        return project

    def __handle_create_new_project_request(self, pi, project, survey_data):
        """Create a new SavioProjectAllocationRequest. This method
        should only be invoked if a new Project is requested."""
        request_kwargs = dict()
        request_kwargs['requester'] = self.request.user
        request_kwargs['allocation_type'] = SavioProjectAllocationRequest.FCA
        request_kwargs['pi'] = pi
        request_kwargs['project'] = project
        request_kwargs['pool'] = False
        request_kwargs['survey_answers'] = survey_data
        request_kwargs['status'] = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        return SavioProjectAllocationRequest.objects.create(**request_kwargs)

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        allocation_period_form_step = self.step_numbers_by_form_name[
            'allocation_period']
        if step > allocation_period_form_step:
            data = self.get_cleaned_data_for_step(
                str(allocation_period_form_step))
            if data:
                dictionary.update(data)
                # TODO: Set this dynamically when supporting other types.
                dictionary['allocation_amount'] = prorated_allocation_amount(
                    settings.FCA_DEFAULT_ALLOCATION, utc_now_offset_aware(),
                    data['allocation_period'])

        pi_selection_form_step = self.step_numbers_by_form_name['pi_selection']
        if step > pi_selection_form_step:
            data = self.get_cleaned_data_for_step(str(pi_selection_form_step))
            if data:
                dictionary.update(data)
                pi_user = data['PI'].user
                try:
                    current_project = get_pi_current_active_fca_project(
                        pi_user)
                except Project.DoesNotExist:
                    # If the PI has no active FCA Project, fall back on one
                    # shared by the requester and the PI.
                    requester_projects = set(list(
                        ProjectUser.objects.filter(
                            project__name__startswith='fc_',
                            user=self.request.user,
                            role__name__in=[
                                'Manager', 'Principal Investigator']
                        ).values_list('project', flat=True)))
                    pi_projects = set(list(
                        ProjectUser.objects.filter(
                            project__name__startswith='fc_',
                            user=pi_user,
                            role__name='Principal Investigator'
                        ).values_list('project', flat=True)))
                    intersection = set.intersection(
                        requester_projects, pi_projects)
                    project_pk = sorted(list(intersection))[0]
                    current_project = Project.objects.get(pk=project_pk)
                dictionary['current_project'] = current_project

        pooling_preference_form_step = self.step_numbers_by_form_name[
            'pooling_preference']
        if step > pooling_preference_form_step:
            data = self.get_cleaned_data_for_step(
                str(pooling_preference_form_step))
            if data:
                dictionary.update(data)

                preference = data['preference']
                form_class = ProjectRenewalPoolingPreferenceForm
                dictionary['breadcrumb_pooling_preference'] = \
                    form_class.SHORT_DESCRIPTIONS.get(preference, 'Unknown')

                if (preference == form_class.UNPOOLED_TO_UNPOOLED or
                        preference == form_class.POOLED_TO_POOLED_SAME):
                    dictionary['requested_project'] = \
                        dictionary['current_project']

        project_selection_form_step = self.step_numbers_by_form_name[
            'project_selection']
        if step > project_selection_form_step:
            data = self.get_cleaned_data_for_step(
                str(project_selection_form_step))
            if data:
                dictionary.update(data)
                dictionary['requested_project'] = data['project'].name

        new_project_details_form_step = self.step_numbers_by_form_name[
            'new_project_details']
        if step > new_project_details_form_step:
            data = self.get_cleaned_data_for_step(
                str(new_project_details_form_step))
            if data:
                dictionary.update(data)
                dictionary['requested_project'] = data['name']


class AllocationRenewalRequestUnderProjectView(LoginRequiredMixin,
                                               UserPassesTestMixin,
                                               AllocationRenewalMixin,
                                               SessionWizardView):

    FORMS = [
        ('allocation_period', SavioProjectAllocationPeriodForm),
        ('pi_selection', ProjectRenewalPISelectionForm),
        ('review_and_submit', ProjectRenewalReviewAndSubmitForm),
    ]

    TEMPLATES = {
        'allocation_period': 'project/project_renewal/allocation_period.html',
        'pi_selection': 'project/project_renewal/pi_selection.html',
        'review_and_submit': 'project/project_renewal/review_and_submit.html',
    }

    form_list = [
        SavioProjectAllocationPeriodForm,
        ProjectRenewalPISelectionForm,
        ProjectRenewalReviewAndSubmitForm,
    ]

    project_obj = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define a lookup table from form name to step number.
        self.step_numbers_by_form_name = {
            name: i for i, (name, _) in enumerate(self.FORMS)}

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.project_obj = get_object_or_404(Project, pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = reverse(
            'project-detail', kwargs={'pk': self.project_obj.pk})
        try:
            tmp = {}
            self.__set_data_from_previous_steps(len(self.FORMS), tmp)
            pi = tmp['PI'].user
            allocation_period = tmp['allocation_period']

            # If the PI already has a non-denied request for the period, raise
            # an exception. Such PIs are not selectable in the 'pi_selection'
            # step, but a request could have been created between selection and
            # final submission.
            if has_non_denied_renewal_request(pi, allocation_period):
                raise Exception(
                    f'PI {pi.username} already has a non-denied '
                    f'AllocationRenewalRequest for AllocationPeriod '
                    f'{allocation_period.name}.')

            request = self.create_allocation_renewal_request(
                self.request.user, pi, allocation_period, self.project_obj,
                self.project_obj)

            self.send_emails(request)
        except Exception as e:
            logger.exception(e)
            messages.error(self.request, self.error_message)
        else:
            messages.success(self.request, self.success_message)

        return HttpResponseRedirect(redirect_url)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self.__set_data_from_previous_steps(current_step, context)
        return context

    def get_form_kwargs(self, step=None):
        # TODO: Set this dynamically when supporting other types.
        allocation_type = SavioProjectAllocationRequest.FCA
        kwargs = {}
        step = int(step)
        if step == self.step_numbers_by_form_name['allocation_period']:
            kwargs['allocation_type'] = allocation_type
        elif step == self.step_numbers_by_form_name['pi_selection']:
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['allocation_period_pk'] = getattr(
                tmp.get('allocation_period', None), 'pk', None)
            kwargs['project_pks'] = [self.project_obj.pk]
        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def test_func(self):
        """Allow superusers and users who are active Managers or
        Principal Investigators on the Project and who have signed the
        access agreement to access the view."""
        user = self.request.user
        if user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is None:
            message = (
                'You must sign the User Access Agreement before you can '
                'request to renew a PI\'s allocation.')
            messages.error(self.request, message)
            return False
        if is_user_manager_or_pi_of_project(user, self.project_obj):
            return True
        message = (
            'You must be an active Manager or Principal Investigator of the '
            'Project.')
        messages.error(self.request, message)

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        allocation_period_form_step = self.step_numbers_by_form_name[
            'allocation_period']
        if step > allocation_period_form_step:
            data = self.get_cleaned_data_for_step(
                str(allocation_period_form_step))
            if data:
                dictionary.update(data)
                # TODO: Set this dynamically when supporting other types.
                dictionary['allocation_amount'] = prorated_allocation_amount(
                    settings.FCA_DEFAULT_ALLOCATION, utc_now_offset_aware(),
                    data['allocation_period'])

        pi_selection_form_step = self.step_numbers_by_form_name['pi_selection']
        if step > pi_selection_form_step:
            data = self.get_cleaned_data_for_step(str(pi_selection_form_step))
            if data:
                dictionary.update(data)
                dictionary['current_project'] = self.project_obj
                dictionary['requested_project'] = self.project_obj
                form_class = ProjectRenewalPoolingPreferenceForm
                if not self.project_obj.is_pooled():
                    pooling_preference = form_class.UNPOOLED_TO_UNPOOLED
                else:
                    pooling_preference = form_class.POOLED_TO_POOLED_SAME
                dictionary['breadcrumb_pooling_preference'] = \
                    pooling_preference
