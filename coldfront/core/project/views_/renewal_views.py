from coldfront.core.project.forms import SavioProjectDetailsForm
from coldfront.core.project.forms import SavioProjectSurveyForm
from coldfront.core.project.forms_.renewal_forms import ProjectRenewalPISelectionForm
from coldfront.core.project.forms_.renewal_forms import ProjectRenewalPoolingPreferenceForm
from coldfront.core.project.forms_.renewal_forms import ProjectRenewalProjectSelectionForm
from coldfront.core.project.forms_.renewal_forms import ProjectRenewalReviewAndSubmitForm
from coldfront.core.project.forms_.renewal_forms import SavioProjectRenewalRequestForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_pi_current_active_fca_project
from coldfront.core.project.utils_.renewal_utils import is_pooled

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormView

from formtools.wizard.views import SessionWizardView

import logging


logger = logging.getLogger(__name__)


class SavioProjectRenewalRequestView(LoginRequiredMixin, UserPassesTestMixin,
                                     FormView):
    form_class = SavioProjectRenewalRequestForm
    template_name = 'project/project_renewal/project_renewal_request.html'
    login_url = '/'

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


# TODO: Rename this.
class PoolingMockUpTmpView(LoginRequiredMixin, UserPassesTestMixin,
                           SessionWizardView):

    # TODO: May need to give allocation type as input: fc_, ic_, pc_.

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
        # TODO: Refine this.
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
            # TODO: Handle others.
            kwargs['allocation_type'] = SavioProjectAllocationRequest.FCA

        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def done(self, form_list, form_dict, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = '/'
        return HttpResponseRedirect(redirect_url)

    @staticmethod
    def condition_dict():
        return {
            '2': PoolingMockUpTmpView.show_project_selection_form_condition,
            '3': PoolingMockUpTmpView.show_new_project_forms_condition,
            '4': PoolingMockUpTmpView.show_new_project_forms_condition,
        }

    @staticmethod
    def show_new_project_forms_condition(wizard):
        """Only show the forms needed for a new Project if the pooling
        preference is to create one."""
        step_name = 'pooling_preference'
        step = str(PoolingMockUpTmpView.step_numbers_by_form_name[step_name])
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
        step = str(PoolingMockUpTmpView.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
        form_class = ProjectRenewalPoolingPreferenceForm
        preferences = (
            form_class.UNPOOLED_TO_POOLED,
            form_class.POOLED_TO_POOLED_DIFFERENT,
            form_class.POOLED_TO_UNPOOLED_OLD,
        )
        return cleaned_data.get('preference', None) in preferences

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
                dictionary['requested_project'] = data["project"].name

        new_project_details_form_step = self.step_numbers_by_form_name[
            'new_project_details']
        if step > new_project_details_form_step:
            data = self.get_cleaned_data_for_step(
                str(new_project_details_form_step))
            if data:
                dictionary.update(data)
                dictionary['requested_project'] = data["name"]
