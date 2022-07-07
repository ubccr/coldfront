from django import forms
from django.core.validators import MinLengthValidator

from coldfront.core.allocation.utils_.secure_dir_utils import \
    get_all_secure_dir_paths


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

    def __init__(self, *args, **kwargs):
        kwargs.pop('breadcrumb_project', None)
        super().__init__(*args, **kwargs)


class SecureDirRDMConsultationForm(forms.Form):
    rdm_consultants = forms.CharField(
        label='List the name(s) of the Research-IT or Information Security '
              'and Policy (ISP) team member(s) with whom you have discussed '
              'this data/project',
        validators=[MinLengthValidator(3)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        kwargs.pop('breadcrumb_project', None)
        super().__init__(*args, **kwargs)


class SecureDirDirectoryNamesForm(forms.Form):

    directory_name = forms.CharField(
        help_text=(
            'Provide the name of the requested secure directory on the cluster.'),
        label='Subdirectory Name',
        required=True,
        widget=forms.Textarea(attrs={'rows': 1}))

    def __init__(self, *args, **kwargs):
        kwargs.pop('breadcrumb_rdm_consultation', None)
        kwargs.pop('breadcrumb_project', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        directory_name = cleaned_data.get('directory_name', None)

        # Fetch all existing directory names.
        paths = get_all_secure_dir_paths()
        cleaned_dir_names = set([path.strip().split('_')[-1] for path in paths])

        # Provided directory name must be unique.
        if directory_name in cleaned_dir_names:
            raise forms.ValidationError(
                'This directory name is already taken. Please choose another.')
        return cleaned_data


class SecureDirSetupForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Denied', 'Denied'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)

    directory_name = forms.CharField(
        help_text=(
            'Edit the provided directory name if necessary.'),
        label='Subdirectory Name',
        required=False,
        widget=forms.Textarea(attrs={'rows': 1}))

    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. This field is only required '
            'for denials, since it will be included in the notification '
            'email.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        dir_name = kwargs.pop('dir_name', None)
        super().__init__(*args, **kwargs)

        self.fields['directory_name'].initial = dir_name

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status', 'Pending')
        directory_name = cleaned_data.get('directory_name', None)

        # Require justification for denials.
        if status == 'Denied':
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for your decision.')

            return cleaned_data

        # Fetch all existing directory names.
        paths = get_all_secure_dir_paths()
        cleaned_dir_names = set([path.strip().split('_')[-1] for path in paths])

        # Provided directory name must be unique.
        if directory_name in cleaned_dir_names:
            raise forms.ValidationError(
                'This directory name is already taken. Please choose another.')

        return cleaned_data
