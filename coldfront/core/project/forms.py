import datetime

from django import forms
from django.shortcuts import get_object_or_404
from django.core.validators import MinLengthValidator

from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectUserRoleChoice,
                                           ProjectStatusChoice,)
from coldfront.core.utils.common import import_from_settings
from coldfront.core.field_of_science.models import FieldOfScience
from django.core.validators import MinLengthValidator
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Fieldset, Reset, Row, Column

EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = import_from_settings(
    'EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL')
EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST', [])
EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings(
    'EMAIL_DIRECTOR_EMAIL_ADDRESS', '')


class ProjectPISearchForm(forms.Form):
    PI_USERNAME = 'PI Username'
    pi_username = forms.CharField(label=PI_USERNAME, max_length=100, required=False)


class ProjectSearchForm(forms.Form):
    """ Search form for the Project list page.
    """
    LAST_NAME = 'Last Name'
    USERNAME = 'Username'
    # FIELD_OF_SCIENCE = 'Field of Science'

    last_name = forms.CharField(
        label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    # field_of_science = forms.CharField(
    #     label=FIELD_OF_SCIENCE, max_length=100, required=False)
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


class ProjectRemoveUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


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

    def __init__(self, pk, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=int(pk))
        self.fields['email_body'].initial = EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL.format(
            first_name=user.first_name, project_name=project_obj.title
        )
        cc_list = [project_obj.pi.email, user.email]
        if project_obj.pi == project_obj.requestor:
            cc_list.remove(project_obj.pi.email)
        self.fields['cc'].initial = ', '.join(cc_list)


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

    def __init__(self, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)

        self.fields['title'].initial = project_obj.title
        self.fields['description'].initial = project_obj.description


class ProjectExportForm(forms.Form):
    file_name = forms.CharField(max_length=64, initial='projects')
    project_statuses = forms.ModelMultipleChoiceField(
        queryset=ProjectStatusChoice.objects.all().order_by('name'),
        help_text='Do not select any if you want all statuses',
        required=False
    )
    project_creation_range_start = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        label='Start',
        help_text='Includes start date',
        required=False
    )
    project_creation_range_stop = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        label='End',
        help_text='Does not include end date',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'file_name',
            Row(
                Column('project_statuses')
            ),
            Fieldset(
                'Project Creation Range',
                Row(
                    Column('project_creation_range_start', css_class='col-md-6'),
                    Column('project_creation_range_stop', css_class='col-md-6'),
                )
            ),
            Submit('submit', 'Export', css_class='btn-success'),
            Reset('reset', 'Reset', css_class='btn-secondary')
        )


class ProjectUserExportForm(forms.Form):
    file_name = forms.CharField(max_length=64, initial='projectusers')
    project_statuses = forms.ModelMultipleChoiceField(
        queryset=ProjectStatusChoice.objects.all().order_by('name'),
        help_text='Do not select any if you want all statuses',
        required=False
    )
    project_user_roles = forms.ModelMultipleChoiceField(
        queryset=ProjectUserRoleChoice.objects.all().order_by('name'),
        help_text='Do not select any if you want all roles',
        required=False
    )
    project_creation_range_start = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        label='Start',
        help_text='Includes start date',
        required=False
    )
    project_creation_range_stop = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        label='Stop',
        help_text='Does not include end date',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'file_name',
            Row(
                Column('project_statuses', css_class='col-md-6'),
                Column('project_user_roles', css_class='col-md-6'),
            ),
            Fieldset(
                'Project Creation Range',
                Row(
                    Column('project_creation_range_start', css_class='col-md-6'),
                    Column('project_creation_range_stop', css_class='col-md-6'),
                )
            ),
            Submit('submit', 'Export', css_class='btn-success'),
            Reset('reset', 'Reset', css_class='btn-secondary')
        )
