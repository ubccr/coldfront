from coldfront.core.allocation.forms import AllocationPeriodChoiceField
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.forms import DisabledChoicesSelectWidget
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_current_allocation_period
from coldfront.core.utils.common import utc_now_offset_aware

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator
from django.core.validators import MinLengthValidator
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.db.models import Q
from django.forms.widgets import TextInput
from django.utils.safestring import mark_safe

from datetime import datetime
from datetime import timedelta
from flags.state import flag_enabled

import pytz


# =============================================================================
# BRC: SAVIO
# =============================================================================

class SavioProjectAllocationPeriodForm(forms.Form):

    allocation_period = AllocationPeriodChoiceField(
        label='Allocation Period',
        queryset=AllocationPeriod.objects.none(),
        required=True)

    def __init__(self, *args, **kwargs):
        self.allocation_type = kwargs.pop('allocation_type', None)
        super().__init__(*args, **kwargs)
        display_timezone = pytz.timezone(settings.DISPLAY_TIME_ZONE)
        self.fields['allocation_period'].queryset = \
            self.allocation_period_choices(
                self.allocation_type, utc_now_offset_aware(), display_timezone)

    @staticmethod
    def allocation_period_choices(allocation_type, utc_dt, display_timezone):
        """Return a queryset of AllocationPeriods to be available in the
        form if rendered at the given datetime, whose tzinfo must be
        pytz.UTC and which will be converted to the given timezone, for
        an allocation with the given type."""
        if utc_dt.tzinfo != pytz.UTC:
            raise ValueError(f'Datetime {utc_dt}\'s tzinfo is not pytz.UTC.')
        dt = utc_dt.astimezone(display_timezone)
        date = datetime.date(dt)
        f = Q(end_date__gte=date)
        queryset = AllocationPeriod.objects.filter(end_date__gte=date)
        if allocation_type in ('FCA', 'PCA'):
            if flag_enabled('ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE'):
                # If projects for the next period may be requested, include it.
                # TODO: This assumes that an allocation year lasts a year.
                num_days_in_allocation_year = 365
                started_before_date = (
                    date + timedelta(days=num_days_in_allocation_year))
            else:
                # Otherwise, include only the current period.
                started_before_date = date
            f = f & Q(start_date__lte=started_before_date)
            f = f & Q(name__startswith='Allowance Year')
        elif allocation_type == 'ICA':
            # TODO: This is a magic number. Make it a setting.
            num_days = 90
            f = f & Q(start_date__lte=date + timedelta(days=num_days))
            f = f & (
                Q(name__startswith='Fall Semester') |
                Q(name__startswith='Spring Semester') |
                Q(name__startswith='Summer Sessions'))
        else:
            return AllocationPeriod.objects.none()
        return queryset.filter(f).order_by('start_date', 'end_date')


class SavioProjectAllocationTypeForm(forms.Form):

    allocation_type = forms.ChoiceField(
        choices=SavioProjectAllocationRequest.ALLOCATION_TYPE_CHOICES,
        label='Allocation Type',
        widget=forms.Select())


class PIChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return f'{obj.first_name} {obj.last_name} ({obj.email})'


class SavioProjectExistingPIForm(forms.Form):

    PI = PIChoiceField(
        label='Principal Investigator',
        queryset=User.objects.none(),
        required=False,
        widget=DisabledChoicesSelectWidget())

    def __init__(self, *args, **kwargs):

        self.allocation_type = kwargs.pop('allocation_type', None)
        self.allocation_period = kwargs.pop('allocation_period', None)

        super().__init__(*args, **kwargs)

        queryset = User.objects.all()
        exclude_user_pks = set()
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')

        ineligible_project_status_names = ['New', 'Active', 'Inactive']
        ineligible_project_request_status_names = [
            'Under Review', 'Approved - Processing', 'Approved - Complete']
        ineligible_renewal_request_status_names = [
            'Under Review', 'Approved', 'Complete']

        if self.allocation_type == 'FCA':

            # PIs may only have one FCA, so disable any PIs who:
            #     (a) have an existing 'New', 'Active', or 'Inactive' FCA,
            #     (b) have non-denied AllocationRenewalRequests during the
            #         specified AllocationPeriod, or
            #     (c) have non-denied SavioProjectAllocationRequests during
            #         the specified AllocationPeriod.

            pis_with_existing_fcas = set(ProjectUser.objects.filter(
                role=pi_role,
                project__name__startswith='fc_',
                project__status__name__in=ineligible_project_status_names
            ).values_list('user__pk', flat=True))
            pis_with_pending_requests = set(
                SavioProjectAllocationRequest.objects.filter(
                    allocation_type=SavioProjectAllocationRequest.FCA,
                    allocation_period=self.allocation_period,
                    status__name__in=ineligible_project_request_status_names
                ).values_list('pi__pk', flat=True))
            pis_with_renewal_requests = set(
                AllocationRenewalRequest.objects.filter(
                    allocation_period=self.allocation_period,
                    status__name__in=ineligible_renewal_request_status_names
                ).values_list('pi__pk', flat=True))
            exclude_user_pks.update(
                set.union(
                    pis_with_existing_fcas,
                    pis_with_pending_requests,
                    pis_with_renewal_requests))
        elif self.allocation_type == 'PCA':

            # PIs may only have one PCA, so disable any PIs who:
            #     (a) have an existing 'New' or 'Active' PCA, or
            #     (b) have non-denied SavioProjectAllocationRequests during
            #         the specified AllocationPeriod.

            pis_with_existing_pcas = set(ProjectUser.objects.filter(
                role=pi_role,
                project__name__startswith='pc_',
                project__status__name__in=ineligible_project_status_names
            ).values_list('user__pk', flat=True))
            pis_with_pending_requests = set(
                SavioProjectAllocationRequest.objects.filter(
                    allocation_type=SavioProjectAllocationRequest.PCA,
                    allocation_period=self.allocation_period,
                    status__name__in=ineligible_project_request_status_names
                ).values_list('pi__pk', flat=True))
            exclude_user_pks.update(
                set.union(pis_with_existing_pcas, pis_with_pending_requests))

        # Exclude any user that does not have an email address.
        queryset = queryset.exclude(Q(email__isnull=True) | Q(email__exact=''))
        self.fields['PI'].queryset = queryset
        self.fields['PI'].widget.disabled_choices = exclude_user_pks

    def clean(self):
        cleaned_data = super().clean()
        pi = self.cleaned_data['PI']
        if pi is not None and pi not in self.fields['PI'].queryset:
            raise forms.ValidationError(f'Invalid selection {pi.username}.')
        return cleaned_data


class SavioProjectNewPIForm(forms.Form):

    first_name = forms.CharField(max_length=30, required=True)
    middle_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(max_length=100, required=True)

    def clean_email(self):
        cleaned_data = super().clean()
        email = cleaned_data['email'].lower()
        if (User.objects.filter(username=email).exists() or
                User.objects.filter(email=email).exists()):
            raise forms.ValidationError(
                'A user with that email address already exists.')
        return email


class SavioProjectExtraFieldsForm(forms.Form):
    """A placeholder for extra fields for non-ICA/Recharge projects."""

    def __init__(self, *args, **kwargs):
        disable_fields = kwargs.pop('disable_fields', False)
        super().__init__(*args, **kwargs)
        if disable_fields:
            for field in self.fields:
                self.fields[field].disabled = True


class SavioProjectICAExtraFieldsForm(SavioProjectExtraFieldsForm):

    num_students = forms.IntegerField(
        help_text=(
            'Specify the number of students you anticipate having in this '
            'course.'),
        label='Number of Students',
        required=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(3000),
        ],
        widget=TextInput(
            attrs={
                'type': 'number',
                'min': '1',
                'max': '3000',
                'step': '1'}))
    num_gsis = forms.IntegerField(
        help_text=(
            'Specify the number of Graduate Student Instructors (GSIs) you '
            'anticipate having in this course.'),
        label='Number of GSIs',
        required=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(50),
        ],
        widget=TextInput(
            attrs={
                'type': 'number',
                'min': '1',
                'max': '50',
                'step': '1'}))
    manager_experience_description = forms.CharField(
        help_text=(
            'Describe your computational skills and experience. As the main '
            'contact/manager, you should be familiar with using the UNIX '
            'command line, accessing remote computing resources via SSH, '
            'using and troubleshooting the software required for the course, '
            'and running said software in parallel (if applicable). You will '
            'also be expected to become familiar with submitting batch jobs '
            'via the Slurm scheduler, based on Savio\'s documentation and/or '
            'other online tutorials.'),
        label='Your Computational Skills and Experience',
        required=True,
        validators=[
            MinLengthValidator(50),
        ],
        widget=forms.Textarea(attrs={'rows': 3}))
    student_experience_description = forms.CharField(
        help_text=(
            'Describe the computational skills and experience of the students '
            'in the course. In particular, describe their experience with the '
            'UNIX command line and with the primary software to be run on '
            'Savio.'),
        label='Student Computational Skills and Experience',
        required=True,
        validators=[
            MinLengthValidator(50),
        ],
        widget=forms.Textarea(attrs={'rows': 3}))
    max_simultaneous_jobs = forms.IntegerField(
        help_text=(
            'Specify an estimate of the maximum total number of jobs you '
            'expect would be run simultaneously by students in the course.'),
        label='Maximum Number of Simultaneous Jobs',
        required=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(100000),
        ],
        widget=TextInput(
            attrs={
                'type': 'number',
                'min': '1',
                'max': '100000',
                'step': '1'}))
    max_simultaneous_nodes = forms.IntegerField(
        help_text=(
            'Specify an estimate of the maximum total number of nodes you '
            'expect would be used simultaneously by students in the course.'),
        label='Maximum Number of Simultaneous Nodes',
        required=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10000),
        ],
        widget=TextInput(
            attrs={
                'type': 'number',
                'min': '1',
                'max': '10000',
                'step': '1'}))


class SavioProjectRechargeExtraFieldsForm(SavioProjectExtraFieldsForm):

    num_service_units = forms.IntegerField(
        help_text=(
            'Specify the number of service units you would like to purchase, '
            'which must be a positive multiple of 100. $1 = 100 SUs.'),
        label='Number of Service Units',
        required=True,
        validators=[
            MaxValueValidator(settings.ALLOCATION_MAX),
            MinValueValidator(100),
        ],
        widget=TextInput(
            attrs={
                'type': 'number',
                'min': '100',
                'max': str(settings.ALLOCATION_MAX),
                'step': '100'}))
    # The minimum and maximum lengths are loose bounds.
    campus_chartstring = forms.CharField(
        help_text=mark_safe(
            'Provide the campus <a href="https://calanswers.berkeley.edu/'
            'subject-areas/pi-portfolio/training/chartstring" target="_blank">'
            'chartstring</a> to bill.'),
        label='Campus Chartstring',
        max_length=100,
        required=True,
        validators=[MinLengthValidator(15)])
    chartstring_account_type = forms.CharField(
        help_text=(
            'Provide the type of account represented by the chartstring.'),
        label='Chartstring Account Type',
        max_length=150,
        required=True)
    # Allow at most 150 characters for the first and last names, and 1 space.
    chartstring_contact_name = forms.CharField(
        help_text=(
            'Provide the name of the departmental business contact for '
            'correspondence about the chartstring.'),
        label='Chartstring Contact Name',
        max_length=301,
        required=True)
    chartstring_contact_email = forms.EmailField(
        help_text=(
            'Provide the email address of the departmental business contact '
            'for correspondence about the chartstring.'),
        label='Chartstring Contact Email',
        max_length=100,
        required=True)

    def __init__(self, *args, **kwargs):
        disable_fields = kwargs.pop('disable_fields', False)
        super().__init__(*args, **kwargs)
        if disable_fields:
            for field in self.fields:
                self.fields[field].disabled = True

    def clean_num_service_units(self):
        cleaned_data = super().clean()
        num_service_units = cleaned_data['num_service_units']
        if not (100 <= num_service_units <= settings.ALLOCATION_MAX):
            raise forms.ValidationError(
                f'The number of service units {num_service_units} is outside '
                f'of the expected range.')
        if num_service_units % 100:
            raise forms.ValidationError(
                f'The number of service units {num_service_units} is not '
                f'divisible by 100.')
        return num_service_units


class SavioProjectPoolAllocationsForm(forms.Form):

    pool = forms.BooleanField(
        initial=False,
        label='Yes, pool the PI\'s allocation with an existing project\'s.',
        required=False)


class PooledProjectChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        names = []
        project_users = obj.projectuser_set.filter(
            role__name='Principal Investigator')
        for project_user in project_users:
            user = project_user.user
            names.append(f'{user.first_name} {user.last_name}')
        names.sort()
        return f'{obj.name} ({", ".join(names)})'


class SavioProjectPooledProjectSelectionForm(forms.Form):

    project = PooledProjectChoiceField(
        label='Project',
        queryset=Project.objects.none(),
        required=True,
        widget=forms.Select())

    def __init__(self, *args, **kwargs):
        self.allocation_type = kwargs.pop('allocation_type', None)
        kwargs.pop('allocation_period', None)
        kwargs.pop('breadcrumb_pi', None)
        kwargs.pop('breadcrumb_pooling', None)
        super().__init__(*args, **kwargs)
        projects = Project.objects.prefetch_related(
            'projectuser_set__user'
        ).filter(
            status__name__in=['Pending - Add', 'New', 'Active']
        )
        if self.allocation_type == 'FCA':
            projects = projects.filter(name__startswith='fc_')
        elif self.allocation_type == 'CO':
            projects = projects.filter(name__startswith='co_')
        elif self.allocation_type == 'PCA':
            projects = projects.filter(name__startswith='pc_')
        self.fields['project'].queryset = projects

    def clean(self):
        cleaned_data = super().clean()
        project = self.cleaned_data['project']
        if project not in self.fields['project'].queryset:
            raise forms.ValidationError(f'Invalid selection {project.name}.')
        return cleaned_data


class SavioProjectDetailsForm(forms.Form):

    name = forms.CharField(
        help_text=(
            'A unique name for the project, which must contain only lowercase '
            'letters and numbers. This will be used to set up the project\'s '
            'SLURM scheduler account.'),
        label='Name',
        max_length=12,
        required=True,
        validators=[
            MinLengthValidator(4),
            RegexValidator(
                r'^[0-9a-z]+$',
                message=(
                    'Name must contain only lowercase letters and numbers.'))
        ])
    title = forms.CharField(
        help_text='A unique, human-readable title for the project.',
        label='Title',
        max_length=255,
        required=True,
        validators=[
            MinLengthValidator(4),
        ])
    description = forms.CharField(
        help_text='A few sentences describing your project.',
        label='Description',
        validators=[MinLengthValidator(10)],
        widget=forms.Textarea(attrs={'rows': 3}))
    # field_of_science = forms.ModelChoiceField(
    #     empty_label=None,
    #     queryset=FieldOfScience.objects.all())

    def __init__(self, *args, **kwargs):
        self.allocation_type = kwargs.pop('allocation_type', None)
        kwargs.pop('allocation_period', None)
        kwargs.pop('breadcrumb_pi', None)
        kwargs.pop('breadcrumb_pooling', None)
        super().__init__(*args, **kwargs)
        if self.allocation_type == SavioProjectAllocationRequest.ICA:
            self.fields['name'].help_text = (
                'A unique name for the course, which must contain only '
                'lowercase letters and numbers. This will be used to set up '
                'the project\'s SLURM scheduler account. It may be the course '
                'number (e.g., pmb220b, pht32, etc.).')

    def clean_name(self):
        cleaned_data = super().clean()
        name = cleaned_data['name'].lower()
        if self.allocation_type == SavioProjectAllocationRequest.CO:
            name = f'co_{name}'
        elif self.allocation_type == SavioProjectAllocationRequest.FCA:
            name = f'fc_{name}'
        elif self.allocation_type == SavioProjectAllocationRequest.ICA:
            name = f'ic_{name}'
        elif self.allocation_type == SavioProjectAllocationRequest.RECHARGE:
            name = f'ac_{name}'
        elif self.allocation_type == SavioProjectAllocationRequest.PCA:
            name = f'pc_{name}'
        if Project.objects.filter(name=name):
            raise forms.ValidationError(
                f'A project with name {name} already exists.')
        return name


class SavioProjectSurveyForm(forms.Form):

    # Question 3
    scope_and_intent = forms.CharField(
        label='Scope and intent of research needing computation',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))
    computational_aspects = forms.CharField(
        label='Computational aspects of the research',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))
    existing_resources = forms.CharField(
        label=(
            'Existing computing resources (outside of Savio) currently being '
            'used by this project. If you use cloud computing resources, we '
            'would be interested in hearing about it.'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}))
    system_needs = forms.MultipleChoiceField(
        choices=(
            ('intermittent_need', 'Meets intermittent or small need for compute cycles'),
            ('cannot_purchase', 'Provides a resource since my group/area cannot purchase its own'),
            ('additional_compute_beyond_cluster', 'Provides additional compute cycles beyond what is provided on my own cluster'),
            ('larger_jobs', 'Provides ability to run larger-scale jobs than those I can\'t run on my own cluster'),
            ('onramp', 'Provides an onramp to prepare for running on large systems or applying for grants and supercomputing center allocations'),
            ('additional_compute', 'Provides additional compute cycles'),
        ),
        label=(
            'Which of the following best describes your need for this '
            'system:'),
        required=False,
        widget=forms.CheckboxSelectMultiple())

    # Question 4
    num_processor_cores = forms.CharField(
        label=(
            'How many processor cores does your application use? (min, max, '
            'typical runs)'),
        required=False)
    memory_per_core = forms.CharField(
        label='How much memory per core does your typical job require?',
        required=False)
    run_time = forms.CharField(
        label='What is the run time of your typical job?', required=False)
    processor_core_hours_year = forms.CharField(
        label=(
            'Estimate how many processor-core-hrs your research will need '
            'over the year.'),
        required=False)
    large_memory_nodes = forms.CharField(
        label=(
            'BRC has a number of large memory nodes, each with 512GB or '
            '384GB. Do you have a need to use these nodes? If so, what is '
            'your expected use of these nodes?'),
        required=False)
    data_storage_space = forms.CharField(
        help_text=mark_safe(
            'BRC provides each user with 10GB of backed up home directory '
            'space; and free access to a not-backed-up shared Global Scratch '
            'high performance parallel filesystem. Research projects that '
            'need to share datasets among their team members can also be '
            'allocated up to 30 GB of not-backed-up shared filesystem space '
            'on request. Users needing more storage can choose to join the '
            'Condo Storage service by purchasing 42TB at the cost of $6539. '
            'More details about this program are available <a href="https://docs-research-it.berkeley.edu/services/high-performance-computing/condos/condo-storage-service/"><span class="accessibility-link-text">Data Storage program details</span>here</a>. '
            'Please indicate if you need additional space and how much.'),
        label='Data Storage Space',
        required=False)
    io = forms.CharField(
        help_text=(
            'Savio provides a shared Lustre parallel filesystem for jobs '
            'needing access to high performance storage.'),
        label='Describe your applications I/O requirements',
        required=False)
    interconnect = forms.ChoiceField(
        choices=(
            ('', 'Select one...'),
            ('1', '1 - Unimportant'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5 - Important'),
        ),
        help_text=(
            'Does your application require low latency communication between '
            'nodes?'),
        label='Interconnect performance',
        required=False)
    network_to_internet = forms.CharField(
        help_text=(
            'Do you need to transfer large amounts of data to and/or from the '
            'cluster? If yes, what is the max you you might transfer in a '
            'day? What would be typical for a month? Do you have need for '
            'file sharing of large datasets?'),
        label='Network connection from Savio to the Internet',
        required=False)
    cloud_computing = forms.ChoiceField(
        choices=(
            ('', 'Select one...'),
            ('1', '1 - Unimportant'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5 - Important'),
        ),
        help_text=(
            'BRC is developing a cloud computing offering. What is your '
            'interest in using the cloud for your computation?'),
        label='Cloud computing',
        required=False)

    # Question 5
    software_source = forms.CharField(
        help_text=(
            'Specify your software applications. If you have need for '
            'commercial software, please indicate that here.'),
        label='What is the source of the software you use (or would use)?',
        required=False)
    outside_server_db_access = forms.CharField(
        label=(
            'Does your application require access to an outside web server or '
            'database? If yes, please explain.'),
        required=False)

    def __init__(self, *args, **kwargs):
        allocation_type = kwargs.pop('allocation_type', None)
        kwargs.pop('allocation_period', None)
        kwargs.pop('breadcrumb_pi', None)
        kwargs.pop('breadcrumb_pooling', None)
        kwargs.pop('breadcrumb_project', None)
        disable_fields = kwargs.pop('disable_fields', False)
        super().__init__(*args, **kwargs)
        if allocation_type == SavioProjectAllocationRequest.ICA:
            self.fields['scope_and_intent'].label = (
                'Scope and intent of coursework needing computation')
            self.fields['computational_aspects'].help_text = (
                'Describe the nature of the coursework for which students '
                'will use Savio (e.g., homework, problem sets, projects, '
                'etc.).')
            self.fields['computational_aspects'].label = (
                'Computational aspects of the coursework')
            self.fields['existing_resources'].label = (
                'Existing computing resources (outside of Savio) currently '
                'being used by this course. If you use cloud computing '
                'resources, we would be interested in hearing about it.')
            self.fields['num_processor_cores'].label = (
                'How many processor cores does a single execution (i.e., by '
                'one student) of your application use? (min, max, typical '
                'runs)')
            self.fields['processor_core_hours_year'].label = (
                'Estimate how many processor-core-hrs your students will need '
                'over the duration of the course.')
        if disable_fields:
            for field in self.fields:
                self.fields[field].disabled = True


# =============================================================================
# BRC: VECTOR
# =============================================================================

class VectorProjectDetailsForm(forms.Form):

    name = forms.CharField(
        help_text=(
            'The unique name of the project, which must contain only '
            'lowercase letters and numbers. This will be used to set up the '
            'project\'s SLURM scheduler account.'),
        label='Name',
        max_length=12,
        required=True,
        validators=[
            MinLengthValidator(4),
            RegexValidator(
                r'^[0-9a-z]+$',
                message=(
                    'Name must contain only lowercase letters and numbers.'))
        ])

    title = forms.CharField(
        help_text='A unique, human-readable title for the project.',
        label='Title',
        max_length=255,
        required=True,
        validators=[
            MinLengthValidator(4),
        ])
    description = forms.CharField(
        help_text='A few sentences describing your project.',
        label='Description',
        validators=[MinLengthValidator(10)],
        widget=forms.Textarea(attrs={'rows': 3}))
    # field_of_science = forms.ModelChoiceField(
    #     empty_label=None,
    #     queryset=FieldOfScience.objects.all())

    def clean_name(self):
        cleaned_data = super().clean()
        name = cleaned_data['name'].lower()
        name = f'vector_{name}'
        if Project.objects.filter(name=name):
            raise forms.ValidationError(
                f'A project with name {name} already exists.')
        return name
