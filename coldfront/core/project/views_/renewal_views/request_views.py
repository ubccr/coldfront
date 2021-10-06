from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.project.forms import SavioProjectDetailsForm
from coldfront.core.project.forms import SavioProjectSurveyForm
from coldfront.core.project.forms_.renewal_forms import ProjectRenewalPISelectionForm
from coldfront.core.project.forms_.renewal_forms import ProjectRenewalPoolingPreferenceForm
from coldfront.core.project.forms_.renewal_forms import ProjectRenewalProjectSelectionForm
from coldfront.core.project.forms_.renewal_forms import ProjectRenewalReviewAndSubmitForm
from coldfront.core.project.forms_.renewal_forms import SavioProjectRenewalRequestForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_pi_current_active_fca_project
from coldfront.core.project.utils_.renewal_utils import is_pooled
from coldfront.core.resource.models import Resource

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormView

from formtools.wizard.views import SessionWizardView

import logging


logger = logging.getLogger(__name__)


class AllocationRenewalRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                   SessionWizardView):

    # TODO: Add logging, sending messages to users, etc.

    FORMS = [
        ('pi_selection', ProjectRenewalPISelectionForm),
        ('pooling_preference', ProjectRenewalPoolingPreferenceForm),
        ('project_selection', ProjectRenewalProjectSelectionForm),
        ('new_project_details', SavioProjectDetailsForm),
        ('new_project_survey', SavioProjectSurveyForm),
        ('review_and_submit', ProjectRenewalReviewAndSubmitForm),
    ]

    TEMPLATES = {
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
        ProjectRenewalPISelectionForm,
        ProjectRenewalPoolingPreferenceForm,
        ProjectRenewalProjectSelectionForm,
        SavioProjectDetailsForm,
        SavioProjectSurveyForm,
        ProjectRenewalReviewAndSubmitForm,
    ]

    # Non-required lookup table: form name --> step number
    step_numbers_by_form_name = {
        'pi_selection': 0,
        'pooling_preference': 1,
        'project_selection': 2,
        'new_project_details': 3,
        'new_project_survey': 4,
        'review_and_submit': 5,
    }

    def test_func(self):
        """Allow superusers and users who are active Managers or
        Principal Investigators on at least one Project to access the
        view."""
        user = self.request.user
        if self.request.user.is_superuser:
            return True
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

    def get_form_kwargs(self, step):
        kwargs = {}
        step = int(step)
        if step == self.step_numbers_by_form_name['pi_selection']:
            project_pks = []
            user = self.request.user
            role_names = ['Manager', 'Principal Investigator']
            status = ProjectUserStatusChoice.objects.get(name='Active')
            project_users = user.projectuser_set.filter(
                role__name__in=role_names, status=status)
            for project_user in project_users:
                project_pks.append(project_user.project.pk)
            kwargs['project_pks'] = project_pks
        elif step == self.step_numbers_by_form_name['pooling_preference']:
            tmp = {}
            self.__set_data_from_previous_steps(step, tmp)
            kwargs['currently_pooled'] = ('current_project' in tmp and
                                          is_pooled(tmp['current_project']))
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
            kwargs['allocation_type'] = SavioProjectAllocationRequest.FCA
        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def done(self, form_list, form_dict, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = '/'

        # Retrieve form data; include empty dictionaries for skipped steps.
        data = iter([form.cleaned_data for form in form_list])
        form_data = [{} for _ in range(len(self.form_list))]
        for step in sorted(form_dict.keys()):
            form_data[int(step)] = next(data)

        try:
            tmp = {}
            self.__set_data_from_previous_steps(len(self.FORMS), tmp)

            form_class = ProjectRenewalPoolingPreferenceForm
            if tmp['preference'] == form_class.POOLED_TO_UNPOOLED_NEW:
                requested_project = self.__handle_create_new_project(form_data)
                survey_data = self.__get_survey_data(form_data)
                new_project_request = self.__handle_create_new_project_request(
                    tmp['PI'], requested_project, survey_data)
            else:
                requested_project = tmp['requested_project']

            request = self.__handle_create_new_renewal_request(
                tmp['PI'], tmp['current_project'], requested_project)

            # TODO
            # Send a notification email to admins.
            try:
                pass
            except Exception as e:
                logger.error(f'Failed to send notification email. Details:\n')
                logger.exception(e)
            # Send a notification email to the PI if the requester differs.
            if request.requester != request.pi:
                try:
                    pass
                except Exception as e:
                    logger.error(
                        f'Failed to send notification email. Details:\n')
                    logger.exception(e)
            # TODO: May need to send email to new pooling PIs.
        except Exception as e:
            logger.exception(e)
            message = f'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return HttpResponseRedirect(redirect_url)

    @staticmethod
    def condition_dict():
        view = AllocationRenewalRequestView
        return {
            '2': view.show_project_selection_form_condition,
            '3': view.show_new_project_forms_condition,
            '4': view.show_new_project_forms_condition,
        }

    @staticmethod
    def show_new_project_forms_condition(wizard):
        """Only show the forms needed for a new Project if the pooling
        preference is to create one."""
        step_name = 'pooling_preference'
        step = str(
            AllocationRenewalRequestView.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
        form_class = ProjectRenewalPoolingPreferenceForm
        return (cleaned_data.get('preference', None) ==
                form_class.POOLED_TO_UNPOOLED_NEW)

    @staticmethod
    def show_project_selection_form_condition(wizard):
        """Only show the form for selecting a Project if the pooling
        preference is to start pooling, to pool with a different
        Project, or to select a different Project owned by the PI."""
        step_name = 'pooling_preference'
        step = str(
            AllocationRenewalRequestView.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
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

    def __handle_create_new_renewal_request(self, pi, pre_project,
                                            post_project):
        """Create a new AllocationRenewalRequest."""
        # TODO: Fill in the correct name.
        allocation_period = AllocationPeriod.objects.get(name='')
        status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')
        request_kwargs = dict()
        request_kwargs['requester'] = self.request.user,
        request_kwargs['pi'] = pi
        request_kwargs['allocation_period'] = allocation_period
        request_kwargs['status'] = status
        request_kwargs['pre_project'] = pre_project
        request_kwargs['post_project'] = post_project
        return AllocationRenewalRequest.objects.create(**request_kwargs)

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        pi_selection_form_step = self.step_numbers_by_form_name['pi_selection']
        if step > pi_selection_form_step:
            data = self.get_cleaned_data_for_step(str(pi_selection_form_step))
            if data:
                dictionary.update(data)
                pi_user = data['PI'].user
                dictionary['current_project'] = \
                    get_pi_current_active_fca_project(pi_user)

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


# TODO: Rename this (e.g., SpecificProject); remove "Savio"
class SavioAllocationRenewalRequestView(LoginRequiredMixin,
                                        UserPassesTestMixin, FormView):
    form_class = SavioProjectRenewalRequestForm
    template_name = 'project/project_renewal/project_renewal_request.html'
    login_url = '/'

    project_obj = None

    # TODO

    def test_func(self):
        """UserPassesTestMixin tests."""
        if self.request.user.is_superuser:
            return True

        project_obj = get_object_or_404(Project, pk=self.kwargs.get('pk'))

        if project_obj.projectuser_set.filter(
                user=self.request.user,
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exists():
            return True

    def dispatch(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        self.project_obj = get_object_or_404(Project, pk=pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form_data = form.cleaned_data
        pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project_obj
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_pk'] = self.project_obj.pk
        return kwargs
