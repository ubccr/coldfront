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
        label='Submit Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)

    submit_modifier = forms.ChoiceField(
        label='Submit Modifier', choices=DATE_MODIFIERS, required=False,
        widget=forms.Select()
    )

    startdate = forms.DateField(
        label='Start Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)

    start_modifier = forms.ChoiceField(
        label='Start Modifier', choices=DATE_MODIFIERS, required=False,
        widget=forms.Select()
    )

    enddate = forms.DateField(
        label='End Date',
        widget=forms.DateInput(attrs={'class': 'datepicker'}),
        required=False)

    end_modifier = forms.ChoiceField(
        label='End Modifier', choices=DATE_MODIFIERS, required=False,
        widget=forms.Select()
    )

    show_all_jobs = forms.BooleanField(initial=False, required=False)

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
                    ValidationError('Must select a modifier for Submit Date')

        if startdate:
            if not start_modifier:
                error_dict['startdate'] = \
                    ValidationError('Must select a modifier for Start Date')

        if enddate:
            if not end_modifier:
                error_dict['enddate'] = \
                    ValidationError('Must select a modifier for End Date')

        if submit_modifier:
            if not submitdate:
                error_dict['submit_modifier'] = \
                    ValidationError('Must select a Submit Date when selecting modifier')

        if start_modifier:
            if not startdate:
                error_dict['start_modifier'] = \
                    ValidationError('Must select a Start Date when selecting modifier')

        if end_modifier:
            if not enddate:
                error_dict['end_modifier'] = \
                    ValidationError('Must select an End Date when selecting modifier')

        if error_dict:
            raise forms.ValidationError(error_dict)
