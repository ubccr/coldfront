from django import forms
from django.core.exceptions import ValidationError
from coldfront.core.utils.common import import_from_settings

EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = import_from_settings(
    'EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL')
EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST', [])
EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings(
    'EMAIL_DIRECTOR_EMAIL_ADDRESS', '')


class JobSearchForm(forms.Form):
    STATUS_CHOICES = [
        ('', '-----'),
        ('COMPLETING', 'Completed'),
        ('NODE_FAIL', 'Node Fail'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed'),
        ('OUT_OF_MEMORY', 'Out of Memory'),
        ('PREEMPTED', 'Preempted'),
        ('REQUEUED', 'Requeued'),
        ('RUNNING', 'Running'),
        ('TIMEOUT', 'Timeout')
    ]

    DATE_MODIFIERS = [
        ('', '-----'),
        ('Before', 'Before'),
        ('On', 'On'),
        ('After', 'After')
    ]

    status = forms.ChoiceField(
        label='Status', choices=STATUS_CHOICES, required=False,
        widget=forms.Select())

    jobslurmid = forms.CharField(label='Slurm ID',
                                   max_length=150, required=False)

    project_name = forms.CharField(label='Project Name',
                                   max_length=100, required=False)
    username = forms.CharField(
        label='Username', max_length=100, required=False)

    partition = forms.CharField(label='Partition', max_length=100, required=False)

    submitdate = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker',
                                      'placeholder': 'MM/DD/YYYY'}),
        required=False,)

    submit_modifier = forms.ChoiceField(
        choices=DATE_MODIFIERS,
        required=False,
        widget=forms.Select()
    )

    startdate = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker',
                                      'placeholder': 'MM/DD/YYYY'}),
        required=False)

    start_modifier = forms.ChoiceField(
        choices=DATE_MODIFIERS,
        required=False,
        widget=forms.Select()
    )

    enddate = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'datepicker',
                                      'placeholder': 'MM/DD/YYYY'}),
        required=False)

    end_modifier = forms.ChoiceField(
        choices=DATE_MODIFIERS,
        required=False,
        widget=forms.Select()
    )

    show_all_jobs = forms.BooleanField(initial=False,
                                       required=False,
                                       label='Show All Jobs')

    def clean(self):
        cleaned_data = super().clean()
        submitdate = cleaned_data.get("submitdate")
        submit_modifier = cleaned_data.get("submit_modifier")

        startdate = cleaned_data.get("startdate")
        start_modifier = cleaned_data.get("start_modifier")

        enddate = cleaned_data.get("enddate")
        end_modifier = cleaned_data.get("end_modifier")

        error_dict = {}

        if submitdate:
            # Only do something if both fields are valid so far.
            if not submit_modifier:
                error_dict['submitdate'] = \
                    ValidationError('Must select a modifier after selecting a date')

        if startdate:
            if not start_modifier:
                error_dict['startdate'] = \
                    ValidationError('Must select a modifier after selecting a date')

        if enddate:
            if not end_modifier:
                error_dict['enddate'] = \
                    ValidationError('Must select a modifier after selecting a date')

        if submit_modifier:
            if not submitdate:
                error_dict['submit_modifier'] = \
                    ValidationError('Must select a date after selecting modifier')

        if start_modifier:
            if not startdate:
                error_dict['start_modifier'] = \
                    ValidationError('Must select a date after selecting modifier')

        if end_modifier:
            if not enddate:
                error_dict['end_modifier'] = \
                    ValidationError('Must select a date after selecting modifier')

        if error_dict:
            raise forms.ValidationError(error_dict)

    def __init__(self, *args, **kwargs):
        ''' remove any labels here if desired
        '''
        super(JobSearchForm, self).__init__(*args, **kwargs)

        self.fields['submitdate'].label = ''
        self.fields['submit_modifier'].label = ''
        self.fields['startdate'].label = ''
        self.fields['start_modifier'].label = ''
        self.fields['enddate'].label = ''
        self.fields['end_modifier'].label = ''
