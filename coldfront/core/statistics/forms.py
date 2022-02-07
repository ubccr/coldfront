from django import forms
from django.core.exceptions import ValidationError
from coldfront.core.project.models import Project, ProjectUser


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

    AMOUNT_MODIFIER = [
        ('', '-----'),
        ('leq', 'Less than or equal to'),
        ('geq', 'Greater than or equal to')
    ]

    status = forms.ChoiceField(
        label='Status', choices=STATUS_CHOICES, required=False,
        widget=forms.Select())

    jobslurmid = forms.CharField(label='Slurm ID',
                                   max_length=150, required=False)

    project_name = forms.CharField(
        label='Project Name',
        max_length=100,
        required=False,
        widget=forms.Select())

    username = forms.CharField(
        label='Username', max_length=100, required=False)

    partition = forms.CharField(label='Partition', max_length=100, required=False)

    amount = forms.FloatField(label='Service Units', required=False)

    amount_modifier = forms.ChoiceField(
        choices=AMOUNT_MODIFIER,
        required=False,
        widget=forms.Select()
    )

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
        submitdate = cleaned_data.get('submitdate')
        submit_modifier = cleaned_data.get('submit_modifier')

        startdate = cleaned_data.get('startdate')
        start_modifier = cleaned_data.get('start_modifier')

        enddate = cleaned_data.get('enddate')
        end_modifier = cleaned_data.get('end_modifier')
        
        amount = cleaned_data.get('amount')
        amount_modifier = cleaned_data.get('amount_modifier')

        error_dict = {}

        if bool(amount) ^ bool(amount_modifier):
            error_dict['amount'] = \
                ValidationError('When filtering on Service Units, you must '
                                'select both a modifier and an amount.')

        if (bool(submitdate) ^ bool(submit_modifier)) or \
                (bool(startdate) ^ bool(start_modifier)) or \
                (bool(enddate) ^ bool(end_modifier)):
            # doesnt really matter what field the error is raised on
            error_dict['submitdate'] = \
                ValidationError('When filtering on a date, you must '
                                'select both a modifier and a date.')

        if error_dict:
            raise forms.ValidationError(error_dict)

        return cleaned_data

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        is_pi = kwargs.pop('is_pi', None)
        super(JobSearchForm, self).__init__(*args, **kwargs)
        queryset = Project.objects.all()

        if user:
            if not (user.is_superuser or user.has_perm('statistics.view_job')):
                if not is_pi:
                    self.fields.pop('username')

                self.fields.pop('show_all_jobs')

                set = ProjectUser.objects.filter(user=user,
                                                 status__name='Active').\
                    distinct('project').values_list('project__name')
                queryset = \
                    Project.objects.filter(name__in=set)

        self.fields['submitdate'].label = ''
        self.fields['submit_modifier'].label = ''
        self.fields['startdate'].label = ''
        self.fields['start_modifier'].label = ''
        self.fields['enddate'].label = ''
        self.fields['end_modifier'].label = ''
        self.fields['amount'].label = ''
        self.fields['amount_modifier'].label = ''

        self.fields['project_name'].widget.choices = \
            [('', '-----')] + [(project.name, project.name) for project in queryset]
