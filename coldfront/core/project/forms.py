import datetime

from django import forms
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from ast import Constant
from django.db.models.functions import Lower
from cProfile import label

from coldfront.core.project.models import (Project, ProjectAttribute, ProjectAttributeType, ProjectReview,
                                           ProjectUserRoleChoice)
from coldfront.core.utils.common import import_from_settings

from django.core.validators import MinLengthValidator

EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = import_from_settings(
    'EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL')
EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST', [])
EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings(
    'EMAIL_DIRECTOR_EMAIL_ADDRESS', '')


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
    first_name = forms.CharField(max_length=150, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    source = forms.CharField(max_length=16, disabled=True)
    role = forms.ModelChoiceField(
        queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectAddUsersToAllocationFormSet(forms.BaseFormSet):
    def get_form_kwargs(self, index):
        """
        Override so allocations can have role selection
        """
        kwargs = super().get_form_kwargs(index)
        roles = kwargs['roles'][index]
        return {'roles': roles}


class ProjectAddUsersToAllocationForm(forms.Form):
    pk = forms.IntegerField(disabled=True)
    selected = forms.BooleanField(initial=False, required=False)
    resource = forms.CharField(max_length=50, disabled=True)
    details = forms.CharField(max_length=300, disabled=True, required=False)
    resource_type = forms.CharField(max_length=50, disabled=True)
    status = forms.CharField(max_length=50, disabled=True)
    role = forms.ChoiceField(choices=(('', '----'),), disabled=True, required=False)

    def __init__(self, *args, **kwargs):
        roles = kwargs.pop('roles')
        super().__init__(*args, **kwargs)
        if roles:
            self.fields['role'].disabled = False
            self.fields['role'].choices = tuple([(role, role) for role in roles])


class ProjectRemoveUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=150, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectUserUpdateForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=ProjectUserRoleChoice.objects.all(), empty_label=None)
    enable_notifications = forms.BooleanField(initial=False, required=False)


class ProjectReviewForm(forms.Form):
    no_project_updates = forms.BooleanField(label='No new project updates', required=False)
    project_updates = forms.CharField(
        label='Project updates', widget=forms.Textarea(), required=False)
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

    def __init__(self, pk, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_review_obj = get_object_or_404(ProjectReview, pk=int(pk))
        self.fields['email_body'].initial = EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL.format(
            first_name=user.first_name, project_name=project_review_obj.project.title
        )
        cc_list = [project_review_obj.project.pi.email, user.email]
        if project_review_obj.project.pi == project_review_obj.project.requestor:
            cc_list.remove(project_review_obj.project.pi.email)
        self.fields['cc'].initial = ', '.join(cc_list)


class ProjectAttributeAddForm(forms.ModelForm):    
    class Meta:
        fields = '__all__'
        model = ProjectAttribute
        labels = {
            'proj_attr_type' : "Project Attribute Type",
        }

    def __init__(self, *args, **kwargs):
        super(ProjectAttributeAddForm, self).__init__(*args, **kwargs) 
        user =(kwargs.get('initial')).get('user')
        self.fields['proj_attr_type'].queryset = self.fields['proj_attr_type'].queryset.order_by(Lower('name'))
        if not user.is_superuser and not user.has_perm('project.delete_projectattribute'):
            self.fields['proj_attr_type'].queryset = self.fields['proj_attr_type'].queryset.filter(is_private=False)

class ProjectAttributeDeleteForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    name = forms.CharField(max_length=150, required=False, disabled=True)
    attr_type = forms.CharField(max_length=150, required=False, disabled=True)
    value = forms.CharField(max_length=150, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()

# class ProjectAttributeChangeForm(forms.Form):
#     pk = forms.IntegerField(required=False, disabled=True)
#     name = forms.CharField(max_length=150, required=False, disabled=True)
#     value = forms.CharField(max_length=150, required=False, disabled=True)
#     new_value = forms.CharField(max_length=150, required=False, disabled=False)

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['pk'].widget = forms.HiddenInput()

#     def clean(self):
#         cleaned_data = super().clean()

#         if cleaned_data.get('new_value') != "":
#             proj_attr = ProjectAttribute.objects.get(pk=cleaned_data.get('pk'))
#             proj_attr.value = cleaned_data.get('new_value')
#             proj_attr.clean()


class ProjectAttributeUpdateForm(forms.Form):
    pk = forms.IntegerField(required=False, disabled=True)
    new_value = forms.CharField(max_length=150, required=True, disabled=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pk'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('new_value') != "":
            proj_attr = ProjectAttribute.objects.get(pk=cleaned_data.get('pk'))
            proj_attr.value = cleaned_data.get('new_value')
            proj_attr.clean()

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
    users = forms.CharField(max_length=2000, disabled=True, required=False)
    status = forms.CharField(max_length=50, disabled=True)
    expires_on = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        disabled=True
    )
    renew = forms.BooleanField(initial=True, required=False)


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
