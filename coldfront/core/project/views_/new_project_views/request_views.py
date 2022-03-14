from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectAllocationTypeForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectDetailsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectExistingPIForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectICAExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectNewPIForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectPoolAllocationsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectPooledProjectSelectionForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectRechargeExtraFieldsForm
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectSurveyForm
from coldfront.core.project.forms_.new_project_forms.request_forms import VectorProjectDetailsForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.models import savio_project_request_ica_extra_fields_schema
from coldfront.core.project.models import savio_project_request_ica_state_schema
from coldfront.core.project.models import savio_project_request_recharge_extra_fields_schema
from coldfront.core.project.models import savio_project_request_recharge_state_schema
from coldfront.core.project.models import VectorProjectAllocationRequest
from coldfront.core.project.utils_.new_project_utils import send_new_project_request_admin_notification_email
from coldfront.core.project.utils_.new_project_utils import send_new_project_request_pi_notification_email
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from formtools.wizard.views import SessionWizardView

import logging


class ProjectRequestView(LoginRequiredMixin, UserPassesTestMixin,
                         TemplateView):
    template_name = 'project/project_request/project_request.html'

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is not None:
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def get(self, request, *args, **kwargs):
        context = dict()
        context['savio_requests'] = \
            SavioProjectAllocationRequest.objects.filter(
                Q(requester=request.user) | Q(pi=request.user)
            ).exclude(
                status__name__in=['Approved - Complete', 'Denied']
            )
        context['vector_requests'] = \
            VectorProjectAllocationRequest.objects.filter(
                Q(requester=request.user) | Q(pi=request.user)
            ).exclude(
                status__name__in=['Approved - Complete', 'Denied']
            )
        return render(request, self.template_name, context)


# =============================================================================
# BRC: SAVIO
# =============================================================================


class SavioProjectRequestWizard(UserPassesTestMixin, SessionWizardView):

    FORMS = [
        ('allocation_type', SavioProjectAllocationTypeForm),
        ('existing_pi', SavioProjectExistingPIForm),
        ('new_pi', SavioProjectNewPIForm),
        ('ica_extra_fields', SavioProjectICAExtraFieldsForm),
        ('recharge_extra_fields', SavioProjectRechargeExtraFieldsForm),
        ('pool_allocations', SavioProjectPoolAllocationsForm),
        ('pooled_project_selection', SavioProjectPooledProjectSelectionForm),
        ('details', SavioProjectDetailsForm),
        ('survey', SavioProjectSurveyForm),
    ]

    TEMPLATES = {
        'allocation_type': 'project/project_request/savio/project_allocation_type.html',
        'existing_pi': 'project/project_request/savio/project_existing_pi.html',
        'new_pi': 'project/project_request/savio/project_new_pi.html',
        'ica_extra_fields': 'project/project_request/savio/project_ica_extra_fields.html',
        'recharge_extra_fields': 'project/project_request/savio/project_recharge_extra_fields.html',
        'pool_allocations': 'project/project_request/savio/project_pool_allocations.html',
        'pooled_project_selection': 'project/project_request/savio/project_pooled_project_selection.html',
        'details': 'project/project_request/savio/project_details.html',
        'survey': 'project/project_request/savio/project_survey.html',
    }

    form_list = [
        SavioProjectAllocationTypeForm,
        SavioProjectExistingPIForm,
        SavioProjectNewPIForm,
        SavioProjectICAExtraFieldsForm,
        SavioProjectRechargeExtraFieldsForm,
        SavioProjectPoolAllocationsForm,
        SavioProjectPooledProjectSelectionForm,
        SavioProjectDetailsForm,
        SavioProjectSurveyForm,
    ]

    # Non-required lookup table: form name --> step number
    step_numbers_by_form_name = {
        'allocation_type': 0,
        'existing_pi': 1,
        'new_pi': 2,
        'ica_extra_fields': 3,
        'recharge_extra_fields': 4,
        'pool_allocations': 5,
        'pooled_project_selection': 6,
        'details': 7,
        'survey': 8,
    }

    logger = logging.getLogger(__name__)

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is not None:
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current)
        self.__set_data_from_previous_steps(current_step, context)
        return context

    def get_form_kwargs(self, step=None):
        kwargs = {}
        step = int(step)
        # The names of steps that require the past data.
        step_names = [
            'existing_pi',
            'pooled_project_selection',
            'details',
            'survey',
        ]
        step_numbers = [
            self.step_numbers_by_form_name[name] for name in step_names]
        if step in step_numbers:
            self.__set_data_from_previous_steps(step, kwargs)
        return kwargs

    def get_template_names(self):
        return [self.TEMPLATES[self.FORMS[int(self.steps.current)][0]]]

    def done(self, form_list, **kwargs):
        """Perform processing and store information in a request
        object."""
        redirect_url = '/'
        try:
            # Retrieve form data; include empty dictionaries for skipped steps.
            data = iter([form.cleaned_data for form in form_list])
            form_data = [{} for _ in range(len(self.form_list))]
            for step in sorted(kwargs['form_dict'].keys()):
                form_data[int(step)] = next(data)

            request_kwargs = {
                'requester': self.request.user,
            }
            allocation_type = self.__get_allocation_type(form_data)
            pi = self.__handle_pi_data(form_data)
            if allocation_type == SavioProjectAllocationRequest.ICA:
                self.__handle_ica_allocation_type(form_data, request_kwargs)
            if allocation_type == SavioProjectAllocationRequest.RECHARGE:
                self.__handle_recharge_allocation_type(
                    form_data, request_kwargs)
            pooling_requested = self.__get_pooling_requested(form_data)
            if pooling_requested:
                project = self.__handle_pool_with_existing_project(form_data)
            else:
                project = self.__handle_create_new_project(form_data)
            survey_data = self.__get_survey_data(form_data)

            # Store transformed form data in a request.
            request_kwargs['allocation_type'] = allocation_type
            request_kwargs['pi'] = pi
            request_kwargs['project'] = project
            request_kwargs['pool'] = pooling_requested
            request_kwargs['survey_answers'] = survey_data
            request_kwargs['status'] = \
                ProjectAllocationRequestStatusChoice.objects.get(
                    name='Under Review')
            request = SavioProjectAllocationRequest.objects.create(
                **request_kwargs)

            # Send a notification email to admins.
            try:
                send_new_project_request_admin_notification_email(request)
            except Exception as e:
                self.logger.error(
                    'Failed to send notification email. Details:\n')
                self.logger.exception(e)
            # Send a notification email to the PI if the requester differs.
            if request.requester != request.pi:
                try:
                    send_new_project_request_pi_notification_email(request)
                except Exception as e:
                    self.logger.error(
                        'Failed to send notification email. Details:\n')
                    self.logger.exception(e)
        except Exception as e:
            self.logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return HttpResponseRedirect(redirect_url)

    @staticmethod
    def condition_dict():
        view = SavioProjectRequestWizard
        return {
            '2': view.show_new_pi_form_condition,
            '3': view.show_ica_extra_fields_form_condition,
            '4': view.show_recharge_extra_fields_form_condition,
            '5': view.show_pool_allocations_form_condition,
            '6': view.show_pooled_project_selection_form_condition,
            '7': view.show_details_form_condition,
        }

    @staticmethod
    def show_details_form_condition(wizard):
        step_name = 'pool_allocations'
        step = str(
            SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
        return not cleaned_data.get('pool', False)

    @staticmethod
    def show_new_pi_form_condition(wizard):
        step_name = 'existing_pi'
        step = str(
            SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
        return cleaned_data.get('PI', None) is None

    @staticmethod
    def show_ica_extra_fields_form_condition(wizard):
        step_name = 'allocation_type'
        step = str(
            SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
        ica_allocation_type = SavioProjectAllocationRequest.ICA
        return cleaned_data.get('allocation_type', None) == ica_allocation_type

    @staticmethod
    def show_recharge_extra_fields_form_condition(wizard):
        step_name = 'allocation_type'
        step = str(
            SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
        recharge_allocation_type = SavioProjectAllocationRequest.RECHARGE
        return (
            cleaned_data.get('allocation_type', None) ==
            recharge_allocation_type)

    @staticmethod
    def show_pool_allocations_form_condition(wizard):
        step_name = 'allocation_type'
        step = str(
            SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
        non_poolable_allocation_types = (
            SavioProjectAllocationRequest.ICA,
            SavioProjectAllocationRequest.RECHARGE,
        )
        allocation_type = cleaned_data.get('allocation_type', None)
        return allocation_type not in non_poolable_allocation_types

    @staticmethod
    def show_pooled_project_selection_form_condition(wizard):
        step_name = 'pool_allocations'
        step = str(
            SavioProjectRequestWizard.step_numbers_by_form_name[step_name])
        cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
        return cleaned_data.get('pool', False)

    def __get_allocation_type(self, form_data):
        """Return the allocation type matching the provided input."""
        step_number = self.step_numbers_by_form_name['allocation_type']
        data = form_data[step_number]
        allocation_type = data['allocation_type']
        for choice, _ in SavioProjectAllocationRequest.ALLOCATION_TYPE_CHOICES:
            if allocation_type == choice:
                return allocation_type
        self.logger.error(
            f'Form received unexpected allocation type {allocation_type}.')
        raise ValueError(f'Invalid allocation type {allocation_type}.')

    def __get_pooling_requested(self, form_data):
        """Return whether or not pooling was requested."""
        step_number = self.step_numbers_by_form_name['pool_allocations']
        data = form_data[step_number]
        return data.get('pool', False)

    def __get_survey_data(self, form_data):
        """Return provided survey data."""
        step_number = self.step_numbers_by_form_name['survey']
        return form_data[step_number]

    def __handle_ica_allocation_type(self, form_data, request_kwargs):
        """Perform ICA-specific handling.

        In particular, set fields in the given dictionary to be used
        during request creation. Set the extra_fields field from the
        given form data and set the state field to include an additional
        step."""
        step_number = self.step_numbers_by_form_name['ica_extra_fields']
        data = form_data[step_number]
        extra_fields = savio_project_request_ica_extra_fields_schema()
        for field in extra_fields:
            extra_fields[field] = data[field]
        request_kwargs['extra_fields'] = extra_fields
        request_kwargs['state'] = savio_project_request_ica_state_schema()

    def __handle_pi_data(self, form_data):
        """Return the requested PI. If the PI did not exist, create a
        new User and UserProfile."""
        # If an existing PI was selected, return the existing User object.
        step_number = self.step_numbers_by_form_name['existing_pi']
        data = form_data[step_number]
        if data['PI']:
            return data['PI']

        # Create a new User object intended to be a new PI.
        step_number = self.step_numbers_by_form_name['new_pi']
        data = form_data[step_number]
        try:
            email = data['email']
            pi = User.objects.create(
                username=email,
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=email,
                is_active=False)
        except IntegrityError as e:
            self.logger.error(f'User {email} unexpectedly exists.')
            raise e

        # Set the user's middle name in the UserProfile; generate a PI request.
        try:
            pi_profile = pi.userprofile
        except UserProfile.DoesNotExist as e:
            self.logger.error(
                f'User {email} unexpectedly has no UserProfile.')
            raise e
        pi_profile.middle_name = data['middle_name']
        pi_profile.upgrade_request = utc_now_offset_aware()
        pi_profile.save()

        return pi

    def __handle_recharge_allocation_type(self, form_data, request_kwargs):
        """Perform Recharge-specific handling.

        In particular, set fields in the given dictionary to be used
        during request creation. Set the extra_fields field from the
        given form data and set the state field to include an additional
        step."""
        step_number = self.step_numbers_by_form_name['recharge_extra_fields']
        data = form_data[step_number]
        extra_fields = savio_project_request_recharge_extra_fields_schema()
        for field in extra_fields:
            extra_fields[field] = data[field]
        request_kwargs['extra_fields'] = extra_fields
        request_kwargs['state'] = savio_project_request_recharge_state_schema()

    def __handle_create_new_project(self, form_data):
        """Create a new project and an allocation to the Savio Compute
        resource."""
        step_number = self.step_numbers_by_form_name['details']
        data = form_data[step_number]

        # Create the new Project.
        status = ProjectStatusChoice.objects.get(name='New')
        try:
            project = Project.objects.create(
                name=data['name'],
                status=status,
                title=data['title'],
                description=data['description'])
                #field_of_science=data['field_of_science'])
        except IntegrityError as e:
            self.logger.error(
                f'Project {data["name"]} unexpectedly already exists.')
            raise e

        # Create an allocation to the "Savio Compute" resource.
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(project=project, status=status)
        resource = Resource.objects.get(name='Savio Compute')
        allocation.resources.add(resource)
        allocation.save()

        return project

    def __handle_pool_with_existing_project(self, form_data):
        """Return the requested project to pool with."""
        step_number = \
            self.step_numbers_by_form_name['pooled_project_selection']
        data = form_data[step_number]
        project = data['project']

        # Validate that the project has exactly one allocation to the "Savio
        # Compute" resource.
        resource = Resource.objects.get(name='Savio Compute')
        allocations = Allocation.objects.filter(
            project=project, resources__pk__exact=resource.pk)
        try:
            assert allocations.count() == 1
        except AssertionError as e:
            number = 'no' if allocations.count() == 0 else 'more than one'
            self.logger.error(
                f'Project {project.name} unexpectedly has {number} Allocation '
                f'to Resource {resource.name}')
            raise e

        return project

    def __set_data_from_previous_steps(self, step, dictionary):
        """Update the given dictionary with data from previous steps."""
        allocation_type_form_step = \
            self.step_numbers_by_form_name['allocation_type']
        if step > allocation_type_form_step:
            allocation_type_form_data = self.get_cleaned_data_for_step(
                str(allocation_type_form_step))
            if allocation_type_form_data:
                dictionary.update(allocation_type_form_data)

        existing_pi_step = self.step_numbers_by_form_name['existing_pi']
        new_pi_step = self.step_numbers_by_form_name['new_pi']
        if step > new_pi_step:
            existing_pi_form_data = self.get_cleaned_data_for_step(
                str(existing_pi_step))
            new_pi_form_data = self.get_cleaned_data_for_step(str(new_pi_step))
            if existing_pi_form_data['PI'] is not None:
                pi = existing_pi_form_data['PI']
                dictionary.update({
                    'breadcrumb_pi': (
                        f'Existing PI: {pi.first_name} {pi.last_name} '
                        f'({pi.email})')
                })
            else:
                first_name = new_pi_form_data['first_name']
                last_name = new_pi_form_data['last_name']
                email = new_pi_form_data['email']
                dictionary.update({
                    'breadcrumb_pi': (
                        f'New PI: {first_name} {last_name} ({email})')
                })

        pool_allocations_step = \
            self.step_numbers_by_form_name['pool_allocations']
        if step > pool_allocations_step:
            allocation_type = dictionary['allocation_type']
            non_poolable_allocation_types = (
                SavioProjectAllocationRequest.ICA,
                SavioProjectAllocationRequest.RECHARGE,
            )
            if allocation_type not in non_poolable_allocation_types:
                pool_allocations_form_data = self.get_cleaned_data_for_step(
                    str(pool_allocations_step))
                pooling_requested = pool_allocations_form_data['pool']
            else:
                pooling_requested = False
            dictionary.update({'breadcrumb_pooling': pooling_requested})

        pooled_project_selection_step = \
            self.step_numbers_by_form_name['pooled_project_selection']
        details_step = self.step_numbers_by_form_name['details']
        if step > details_step:
            if pooling_requested:
                pooled_project_selection_form_data = \
                    self.get_cleaned_data_for_step(
                        str(pooled_project_selection_step))
                project = pooled_project_selection_form_data['project']
                dictionary.update({
                    'breadcrumb_project': f'Project: {project.name}'
                })
            else:
                details_form_data = self.get_cleaned_data_for_step(
                    str(details_step))
                name = details_form_data['name']
                dictionary.update({'breadcrumb_project': f'Project: {name}'})


# =============================================================================
# BRC: VECTOR
# =============================================================================


class VectorProjectRequestView(LoginRequiredMixin, UserPassesTestMixin,
                               FormView):
    form_class = VectorProjectDetailsForm
    template_name = 'project/project_request/vector/project_details.html'
    login_url = '/'

    logger = logging.getLogger(__name__)

    def test_func(self):
        if self.request.user.is_superuser:
            return True

        if self.request.user.has_perms('project.view_vectorprojectallocationrequest'):
            return True

        signed_date = (
            self.request.user.userprofile.access_agreement_signed_date)
        if signed_date is not None:
            return True
        message = (
            'You must sign the User Access Agreement before you can create a '
            'new project.')
        messages.error(self.request, message)

    def form_valid(self, form):
        try:
            project = self.__handle_create_new_project(form.cleaned_data)
            # Store form data in a request.

            pi = User.objects.get(username=settings.VECTOR_PI_USERNAME)
            status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
            request = VectorProjectAllocationRequest.objects.create(
                requester=self.request.user,
                pi=pi,
                project=project,
                status=status)

            # Send a notification email to admins.
            try:
                send_new_project_request_admin_notification_email(request)
            except Exception as e:
                self.logger.error(
                    'Failed to send notification email. Details:\n')
                self.logger.exception(e)
        except Exception as e:
            self.logger.exception(e)
            message = 'Unexpected failure. Please contact an administrator.'
            messages.error(self.request, message)
        else:
            message = (
                'Thank you for your submission. It will be reviewed and '
                'processed by administrators.')
            messages.success(self.request, message)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('home')

    def __handle_create_new_project(self, data):
        """Create a new project and an allocation to the Vector Compute
        resource."""
        status = ProjectStatusChoice.objects.get(name='New')
        try:
            project = Project.objects.create(
                name=data['name'],
                status=status,
                title=data['title'],
                description=data['description'])
        except IntegrityError as e:
            self.logger.error(
                f'Project {data["name"]} unexpectedly already exists.')
            raise e

        # Create an allocation to the "Vector Compute" resource.
        status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(project=project, status=status)
        resource = Resource.objects.get(name='Vector Compute')
        allocation.resources.add(resource)
        allocation.save()

        return project
