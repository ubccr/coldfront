import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.core.validators import MinLengthValidator

from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectUserRoleChoice)
from coldfront.core.utils.common import import_from_settings
from coldfront.core.field_of_science.models import FieldOfScience
from django.core.validators import MinLengthValidator
from coldfront.core.utils.validators import IsAlpha

EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = import_from_settings(
    'EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL')
EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST', [])
EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings(
    'EMAIL_DIRECTOR_EMAIL_ADDRESS', '')


class ProjectFormSetWithSelectDisabled(forms.BaseFormSet):
    def get_form_kwargs(self, index):
        """
        Override so specific selections can be disabled.
        """
        kwargs = super().get_form_kwargs(index)
        disable_selected = kwargs['disable_selected'][index]
        return {'disable_selected': disable_selected}


class ProjectPISearchForm(forms.Form):
    PI_USERNAME = 'PI Username'
    pi_username = forms.CharField(label=PI_USERNAME, max_length=100, required=False)


class ProjectSearchForm(forms.Form):
    """ Search form for the Project list page.
    """
    LAST_NAME = 'Last Name'
    USERNAME = 'Username'
    FIELD_OF_SCIENCE = 'Field of Science'

    last_name = forms.CharField(
        label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    field_of_science = forms.CharField(
        label=FIELD_OF_SCIENCE, max_length=100, required=False)
    show_all_projects = forms.BooleanField(initial=False, required=False)


class ProjectAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    source = forms.CharField(max_length=16, disabled=True)
    role = forms.ModelChoiceField(
        queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectAddUsersToAllocationForm(forms.Form):
    pk = forms.IntegerField(disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
    resource = forms.CharField(max_length=50, disabled=True)
    resource_type = forms.CharField(max_length=50, disabled=True)
    status = forms.CharField(max_length=50, disabled=True)

    def __init__(self, *args, disable_selected, **kwargs):
        super().__init__(*args, **kwargs)

        if disable_selected:
            self.fields['selected'].disabled = True


class ProjectRemoveUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, disable_selected, **kwargs):
        super().__init__(*args, **kwargs)
        if disable_selected:
            self.fields['selected'].disabled = True


class ProjectRemoveUserFormset(forms.BaseFormSet):
    def get_form_kwargs(self, index):
        """
        Override so specific users can be prevented from being removed.
        """
        kwargs = super().get_form_kwargs(index)
        disable_selected = kwargs['disable_selected'][index]
        return {'disable_selected': disable_selected}


class ProjectUserUpdateForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    enable_notifications = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        disable_role = kwargs.pop('disable_role', False)
        disable_enable_notifications = kwargs.pop('disable_enable_notifications', False)
        super().__init__(*args, **kwargs)
        if disable_role:
            self.fields['role'].disabled = True
        if disable_enable_notifications:
            self.fields['enable_notifications'].disabled = True


class ProjectReviewForm(forms.Form):
    no_project_updates = forms.BooleanField(label='No new project updates', required=False)
    project_updates = forms.CharField(
        label='Project updates',
        widget=forms.Textarea(),
        required=False
    )
    acknowledgement = forms.BooleanField(
        label='By checking this box I acknowledge that I have updated my project to the best of my knowledge', initial=False, required=True)

    def clean(self):
        cleaned_data = super().clean()
        project_updates = cleaned_data.get('project_updates')
        no_project_updates = cleaned_data.get('no_project_updates')
        if not no_project_updates and project_updates == '':
            raise forms.ValidationError('Please fill out the project updates field.')


class ProjectReviewEmailForm(forms.Form):
    cc = forms.CharField(
        required=False
    )
    email_body = forms.CharField(
        required=True,
        widget=forms.Textarea
    )

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_review_obj = get_object_or_404(ProjectReview, pk=int(pk))
        self.fields['email_body'].initial = 'Dear {} {} \n{}'.format(
            project_review_obj.project.pi.first_name, project_review_obj.project.pi.last_name, EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL)
        self.fields['cc'].initial = ', '.join(
            [EMAIL_DIRECTOR_EMAIL_ADDRESS] + EMAIL_ADMIN_LIST)


class ProjectRequestEmailForm(forms.Form):
    cc = forms.CharField(
        required=False
    )
    email_body = forms.CharField(
        required=True,
        widget=forms.Textarea
    )

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cc'].initial = ', '.join(
            [EMAIL_DIRECTOR_EMAIL_ADDRESS] + EMAIL_ADMIN_LIST)


class ProjectReviewAllocationForm(forms.Form):
    pk = forms.IntegerField(disabled=True)
    resource = forms.CharField(max_length=100, disabled=True)
    users = forms.CharField(max_length=1000, disabled=True, required=False)
    status = forms.CharField(max_length=50, disabled=True)
    expires_on = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        disabled=True
    )
    renew = forms.BooleanField(initial=False, required=False)


class ProjectUpdateForm(forms.Form):
    title = forms.CharField(max_length=255,)
    description = forms.CharField(
        validators=[
            MinLengthValidator(
                10,
                'The project description must be > 10 characters',
            )
        ],
        widget=forms.Textarea
    )
    field_of_science = forms.ModelChoiceField(queryset=FieldOfScience.objects.all())

    def __init__(self, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)

        self.fields['title'].initial = project_obj.title
        self.fields['description'].initial = project_obj.description
        self.fields['field_of_science'].initial = project_obj.field_of_science
