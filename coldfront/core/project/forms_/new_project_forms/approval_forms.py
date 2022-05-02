from coldfront.core.project.models import Project

from django import forms
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator


# =============================================================================
# BRC: SAVIO
# =============================================================================


class SavioProjectReviewAllocationDatesForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Complete', 'Complete'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    start_date = forms.DateField(
        help_text=(
            'Specify the date on which the allocation should start, in local '
            'time.'),
        label='Start Date',
        required=False,
        widget=forms.widgets.DateInput())
    end_date = forms.DateField(
        help_text=(
            'Specify the date on which the allocation should end, in local '
            'time.'),
        label='End Date',
        required=False,
        widget=forms.widgets.DateInput())

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError(
                    'End date cannot be less than start date.')
        else:
            if status == 'Complete':
                raise forms.ValidationError(
                    'One or more dates have not been set.')


class SavioProjectReviewSetupForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Complete', 'Complete'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    final_name = forms.CharField(
        help_text=(
            'Update the name of the project, in case it needed to be '
            'changed. It must begin with the correct prefix.'),
        label='Final Name',
        max_length=len('fc_') + 12,
        required=True,
        validators=[
            MinLengthValidator(len('fc_') + 4),
            RegexValidator(
                r'^[0-9a-z_]+$',
                message=(
                    'Name must contain only lowercase letters, numbers, and '
                    'underscores.'))
        ])
    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. This field is only required '
            'when the name changes.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        self.project_pk = kwargs.pop('project_pk')
        self.requested_name = kwargs.pop('requested_name')
        super().__init__(*args, **kwargs)
        self.fields['final_name'].initial = self.requested_name

    def clean(self):
        cleaned_data = super().clean()
        final_name = cleaned_data.get('final_name', '').lower()
        # Require justification for name changes.
        if final_name != self.requested_name:
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for the name change.')
        return cleaned_data

    def clean_final_name(self):
        cleaned_data = super().clean()
        final_name = cleaned_data.get('final_name', '').lower()
        expected_prefix = None
        for prefix in ('ac_', 'co_', 'fc_', 'ic_', 'pc_'):
            if self.requested_name.startswith(prefix):
                expected_prefix = prefix
                break
        if not expected_prefix:
            raise forms.ValidationError(
                f'Requested project name {self.requested_name} has invalid '
                f'prefix.')
        if not final_name.startswith(expected_prefix):
            raise forms.ValidationError(
                f'Final project name must begin with "{expected_prefix}".')
        matching_projects = Project.objects.exclude(
            pk=self.project_pk).filter(name=final_name)
        if matching_projects.exists():
            raise forms.ValidationError(
                f'A project with name {final_name} already exists.')
        return final_name


# =============================================================================
# BRC: VECTOR
# =============================================================================

class VectorProjectReviewSetupForm(forms.Form):

    status = forms.ChoiceField(
        choices=(
            ('', 'Select one.'),
            ('Pending', 'Pending'),
            ('Complete', 'Complete'),
        ),
        help_text='If you are unsure, leave the status as "Pending".',
        label='Status',
        required=True)
    final_name = forms.CharField(
        help_text=(
            'Update the name of the project, in case it needed to be '
            'changed. It must begin with the correct prefix.'),
        label='Final Name',
        max_length=len('vector_') + 12,
        required=True,
        validators=[
            MinLengthValidator(len('vector_') + 4),
            RegexValidator(
                r'^[0-9a-z_]+$',
                message=(
                    'Name must contain only lowercase letters, numbers, and '
                    'underscores.'))
        ])
    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. This field is only required '
            'when the name changes.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        self.project_pk = kwargs.pop('project_pk')
        self.requested_name = kwargs.pop('requested_name')
        super().__init__(*args, **kwargs)
        self.fields['final_name'].initial = self.requested_name

    def clean(self):
        cleaned_data = super().clean()
        final_name = cleaned_data.get('final_name', '').lower()
        # Require justification for name changes.
        if final_name != self.requested_name:
            justification = cleaned_data.get('justification', '')
            if not justification.strip():
                raise forms.ValidationError(
                    'Please provide a justification for the name change.')
        return cleaned_data

    def clean_final_name(self):
        cleaned_data = super().clean()
        final_name = cleaned_data.get('final_name', '').lower()
        expected_prefix = 'vector_'
        if not final_name.startswith(expected_prefix):
            raise forms.ValidationError(
                f'Final project name must begin with "{expected_prefix}".')
        matching_projects = Project.objects.exclude(
            pk=self.project_pk).filter(name=final_name)
        if matching_projects.exists():
            raise forms.ValidationError(
                f'A project with name {final_name} already exists.')
        return final_name
