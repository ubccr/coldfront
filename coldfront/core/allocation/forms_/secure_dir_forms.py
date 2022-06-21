from django import forms
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db.models import Q

from coldfront.core.allocation.models import SecureDirRequest
from coldfront.core.project.forms_.new_project_forms.request_forms import \
    PIChoiceField
from coldfront.core.project.models import ProjectUserRoleChoice, ProjectUser, \
    Project


class SecureDirManageUsersForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class SecureDirManageUsersSearchForm(forms.Form):
    project_name = forms.CharField(label='Project Name',
                                   max_length=100, required=False,
                                   help_text='Name of associated project.')
    directory_name = forms.CharField(label='Directory Name',
                                     max_length=100, required=False,
                                     help_text='Directory name on cluster.')
    username = forms.CharField(
        label='User Username', max_length=100, required=False)
    email = forms.CharField(label='User Email', max_length=100, required=False)
    show_all_requests = forms.BooleanField(initial=True, required=False)


class SecureDirManageUsersRequestUpdateStatusForm(forms.Form):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
    ]

    status = forms.ChoiceField(
        label='Status', choices=STATUS_CHOICES, required=True,
        widget=forms.Select())


class SecureDirManageUsersRequestCompletionForm(forms.Form):
    STATUS_CHOICES = [
        ('Processing', 'Processing'),
        ('Complete', 'Complete')
    ]

    status = forms.ChoiceField(
        label='Status', choices=STATUS_CHOICES, required=True,
        widget=forms.Select())


class SecureDirDataDescriptionForm(forms.Form):
    data_description = forms.CharField(
        label='Please explain the kind of P2/P3 data you are planning to '
              'work with on Savio. Please include: (1) Dataset description '
              '(2) Source of dataset (3) Security & Compliance requirements '
              'for this dataset(s) (4) Number and sizes of files (5) '
              'Anticipated duration of usage of datasets on Savio.',
        validators=[MinLengthValidator(20)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))

    rdm_consultation = forms.BooleanField(
        initial=False,
        label='Have you already talked with Research IT staff (and/or with '
              'the Information Security and Policy team) about your data?',
        required=False)


class SecureDirRDMConsultationForm(forms.Form):
    rdm_consultants = forms.CharField(
        label='List the name(s) of the Research-IT or Information Security '
              'and Policy (ISP) team member(s) with whom you have discussed '
              'this data/project',
        validators=[MinLengthValidator(3)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))


class SecureDirExistingPIForm(forms.Form):
    PI = PIChoiceField(
        label='Principal Investigator',
        queryset=User.objects.none(),
        required=True)

    def __init__(self, *args, **kwargs):
        kwargs.pop('breadcrumb_rdm_consultation', None)
        super().__init__(*args, **kwargs)

        queryset = User.objects.all()
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')

        # Only include active PIs that are apart of active projects.
        pi_set = \
            set(ProjectUser.objects.filter(role=pi_role,
                                           project__status__name='Active',
                                           status__name='Active'
                                           ).values_list('user__pk', flat=True))
        queryset = queryset.filter(pk__in=pi_set)
        self.fields['PI'].queryset = queryset

    def clean(self):
        cleaned_data = super().clean()
        pi = self.cleaned_data['PI']
        if pi is not None and pi not in self.fields['PI'].queryset:
            raise forms.ValidationError(f'Invalid selection {pi.username}.')
        return cleaned_data


class SecureDirExistingProjectForm(forms.Form):
    project = forms.ModelChoiceField(
        label='Project',
        queryset=Project.objects.none(),
        required=True)

    def __init__(self, *args, **kwargs):
        kwargs.pop('breadcrumb_rdm_consultation', None)
        kwargs.pop('breadcrumb_pi', None)
        super().__init__(*args, **kwargs)

        fc_co_projects_cond = Q(name__startswith='fc_') | Q(name__startswith='co_')
        self.fields['project'].queryset = Project.objects.filter(fc_co_projects_cond, status__name='Active')


class SecureDirReviewStatusForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Completed', 'Completed'),
            ('Denied', 'Denied'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. This field is only required '
            'for denials, since it will be included in the notification '
            'email.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status', 'Pending')
        # Require justification for denials.
        if status == 'Denied':
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for your decision.')
        return cleaned_data


class SecureDirRequestReviewDenyForm(forms.Form):

    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. It will be included in the '
            'notification email.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))


class SecureDirRequestDirectoryNamesForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Completed', 'Completed'),
            ('Denied', 'Denied'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)

    # TODO: change help text when scratch2 is migrated to scratch
    # TODO: change to required when scratch2 is migrated to scratch
    scratch_name = forms.CharField(
        help_text=(
            'Provide the name of the secure scratch directory.'),
        label='Scratch Subdirectory Name',
        required=True,
        widget=forms.Textarea(attrs={'rows': 1}))
    groups_name = forms.CharField(
        help_text=(
            'Provide the name of the secure groups directory.'),
        label='Groups Subdirectory Name',
        required=True,
        widget=forms.Textarea(attrs={'rows': 1}))