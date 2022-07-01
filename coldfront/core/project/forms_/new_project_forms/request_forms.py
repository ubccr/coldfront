from coldfront.core.allocation.forms import AllocationPeriodChoiceField
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.forms import DisabledChoicesSelectWidget
from coldfront.core.project.models import Project
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.new_project_utils import non_denied_new_project_request_statuses
from coldfront.core.project.utils_.new_project_utils import pis_with_new_project_requests_pks
from coldfront.core.project.utils_.new_project_utils import project_pi_pks
from coldfront.core.project.utils_.renewal_utils import non_denied_renewal_request_statuses
from coldfront.core.project.utils_.renewal_utils import pis_with_renewal_requests_pks
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.constants import LRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.user.utils import is_lbl_employee
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

    NUM_DAYS_IN_ALLOCATION_YEAR = 365
    NUM_DAYS_BEFORE_ICA = 90

    allocation_period = forms.ModelChoiceField(
        label='Allocation Period',
        queryset=AllocationPeriod.objects.none(),
        required=True)

    def __init__(self, *args, **kwargs):
        computing_allowance = kwargs.pop('computing_allowance', None)
        super().__init__(*args, **kwargs)
        display_timezone = pytz.timezone(settings.DISPLAY_TIME_ZONE)
        queryset = self.allocation_period_choices(
            computing_allowance, utc_now_offset_aware(), display_timezone)
        self.fields['allocation_period'] = AllocationPeriodChoiceField(
            computing_allowance=computing_allowance,
            label='Allocation Period',
            queryset=queryset,
            required=True)

    def allocation_period_choices(self, computing_allowance, utc_dt,
                                  display_timezone):
        """Return a queryset of AllocationPeriods to be available in the
        form if rendered at the given datetime, whose tzinfo must be
        pytz.utc and which will be converted to the given timezone, for
        the given computing allowance."""
        none = AllocationPeriod.objects.none()
        if not computing_allowance:
            return none

        if utc_dt.tzinfo != pytz.utc:
            raise ValueError(f'Datetime {utc_dt}\'s tzinfo is not pytz.utc.')
        dt = utc_dt.astimezone(display_timezone)
        date = datetime.date(dt)
        f = Q(end_date__gte=date)
        order_by = ('start_date', 'end_date')

        if flag_enabled('BRC_ONLY'):
            return self._allocation_period_choices_brc(
                computing_allowance, date, f, order_by)
        elif flag_enabled('LRC_ONLY'):
            return self._allocation_period_choices_lrc(
                computing_allowance, date, f, order_by)
        return none

    def _allocation_period_choices_brc(self, computing_allowance, date, f,
                                       order_by):
        """TODO"""
        allowance_name = computing_allowance.name
        if allowance_name in (BRCAllowances.FCA, BRCAllowances.PCA):
            return self._allocation_period_choices_allowance_year(
                date, f, order_by)
        elif allowance_name == BRCAllowances.ICA:
            num_days = self.NUM_DAYS_BEFORE_ICA
            f = f & Q(start_date__lte=date + timedelta(days=num_days))
            f = f & (
                Q(name__startswith='Fall Semester') |
                Q(name__startswith='Spring Semester') |
                Q(name__startswith='Summer Sessions'))
            return AllocationPeriod.objects.filter(f).order_by(*order_by)
        return AllocationPeriod.objects.none()

    def _allocation_period_choices_lrc(self, computing_allowance, date, f,
                                       order_by):
        """TODO"""
        allowance_name = computing_allowance.name
        if allowance_name == LRCAllowances.PCA:
            return self._allocation_period_choices_allowance_year(
                date, f, order_by)
        return AllocationPeriod.objects.none()

    def _allocation_period_choices_allowance_year(self, date, f, order_by):
        """TODO"""
        if flag_enabled('ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE'):
            # If projects for the next period may be requested, include it.
            started_before_date = (
                    date + timedelta(days=self.NUM_DAYS_IN_ALLOCATION_YEAR))
            # Special handling: During the time in which renewals for the
            # next period can be requested, the first option should be the
            # period that is most relevant to most users (i.e., the
            # upcoming one).
            order_by = ('-start_date', '-end_date')
        else:
            # Otherwise, include only the current period.
            started_before_date = date
        f = f & Q(start_date__lte=started_before_date)
        f = f & Q(name__startswith='Allowance Year')
        return AllocationPeriod.objects.filter(f).order_by(*order_by)


class ComputingAllowanceForm(forms.Form):

    computing_allowance = forms.ModelChoiceField(
        label='Computing Allowance',
        queryset=Resource.objects.filter(
            resource_type__name='Computing Allowance').order_by('pk'))


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
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        self.allocation_period = kwargs.pop('allocation_period', None)
        super().__init__(*args, **kwargs)
        if self.computing_allowance is not None:
            self.computing_allowance = ComputingAllowance(
                self.computing_allowance)
            self.disable_pi_choices()
        self.exclude_pi_choices()

    def clean(self):
        cleaned_data = super().clean()
        pi = self.cleaned_data['PI']
        if pi is not None and pi not in self.fields['PI'].queryset:
            raise forms.ValidationError(f'Invalid selection {pi.username}.')
        return cleaned_data

    def disable_pi_choices(self):
        """Prevent certain Users, who should be displayed, from being
        selected as PIs."""
        disable_user_pks = set()

        if self.computing_allowance.is_one_per_pi() and self.allocation_period:
            # Disable any PI who has:
            #     (a) an existing Project with the allowance*,
            #     (b) a new project request for a Project with the allowance
            #         during the AllocationPeriod*, or
            #     (c) an allowance renewal request for a Project with the
            #         allowance during the AllocationPeriod*.
            # * Projects/requests must have ineligible statuses.
            resource = self.computing_allowance.get_resource()
            project_status_names = ['New', 'Active', 'Inactive']
            disable_user_pks.update(
                project_pi_pks(
                    computing_allowance=resource,
                    project_status_names=project_status_names))
            new_project_request_status_names = list(
                non_denied_new_project_request_statuses().values_list(
                    'name', flat=True))
            disable_user_pks.update(
                pis_with_new_project_requests_pks(
                    self.allocation_period,
                    computing_allowance=resource,
                    request_status_names=new_project_request_status_names))
            renewal_request_status_names = list(
                non_denied_renewal_request_statuses().values_list(
                    'name', flat=True))
            disable_user_pks.update(
                pis_with_renewal_requests_pks(
                    self.allocation_period,
                    computing_allowance=resource,
                    request_status_names=renewal_request_status_names))

        if flag_enabled('LRC_ONLY'):
            # On LRC, PIs must be LBL employees.
            non_lbl_employees = set(
                [user.pk for user in User.objects.all()
                 if not is_lbl_employee(user)])
            disable_user_pks.update(non_lbl_employees)

        self.fields['PI'].widget.disabled_choices = disable_user_pks

    def exclude_pi_choices(self):
        """Exclude certain Users from being displayed as PI options."""
        # Exclude any user that does not have an email address.
        self.fields['PI'].queryset = User.objects.exclude(
            Q(email__isnull=True) | Q(email__exact=''))


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

        if flag_enabled('LRC_ONLY'):
            if not email.endswith('@lbl.gov'):
                raise forms.ValidationError(
                    'New PI must be an LBL employee with an LBL email.')

        return email


class SavioProjectExtraFieldsForm(forms.Form):
    """A base form for retrieving additional information for the
    requested allowance."""

    def __init__(self, *args, **kwargs):
        disable_fields = kwargs.pop('disable_fields', False)
        super().__init__(*args, **kwargs)
        if disable_fields:
            for field in self.fields:
                self.fields[field].disabled = True


class NewProjectExtraFieldsFormFactory(object):
    """A factory for returning a form to acquire additional information
    about a particular allowance."""

    def get_form(self, computing_allowance, *args, **kwargs):
        """Return an instantiated form for the given allowance with the
        given arguments and keyword arguments."""
        assert isinstance(computing_allowance, ComputingAllowance)
        return self._get_form_class(computing_allowance)(*args, **kwargs)

    @staticmethod
    def _get_form_class(computing_allowance):
        """Return the appropriate form class for the given allowance. If
        none are applicable, raise a ValueError."""
        allowance_name = computing_allowance.get_name()
        if flag_enabled('BRC_ONLY'):
            if allowance_name == BRCAllowances.ICA:
                return SavioProjectICAExtraFieldsForm
            elif allowance_name == BRCAllowances.RECHARGE:
                return SavioProjectRechargeExtraFieldsForm
        raise ValueError(
            f'Computing Allowance {allowance_name} does not require extra '
            f'fields.')


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
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        self.interface = ComputingAllowanceInterface()
        super().__init__(*args, **kwargs)

        f = Q(status__name__in=['Pending - Add', 'New', 'Active'])

        if self.computing_allowance is not None:
            self.computing_allowance = ComputingAllowance(
                self.computing_allowance)
            prefix = self.interface.code_from_name(
                self.computing_allowance.get_name())
            f = f & Q(name__startswith=prefix)

        self.fields['project'].queryset = Project.objects.prefetch_related(
            'projectuser_set__user').filter(f)

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
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        self.interface = ComputingAllowanceInterface()
        super().__init__(*args, **kwargs)
        if self.computing_allowance is not None:
            self.computing_allowance = ComputingAllowance(
                self.computing_allowance)
            self._update_field_attributes()

    def clean_name(self):
        cleaned_data = super().clean()
        prefix = self.interface.code_from_name(
            self.computing_allowance.get_name())
        suffix = cleaned_data['name'].lower()
        name = f'{prefix}{suffix}'
        if Project.objects.filter(name=name):
            raise forms.ValidationError(
                f'A project with name {name} already exists.')
        return name

    def _update_field_attributes(self):
        """Update fields for select allowances."""
        field = self.fields['name']
        if self.computing_allowance.is_instructional():
            field.help_text = (
                'A unique name for the course, which must contain only '
                'lowercase letters and numbers. This will be used to set up '
                'the project\'s SLURM scheduler account. It may be the course '
                'number (e.g., pmb220b, pht32, etc.).')


class SavioProjectSurveyForm(forms.Form):
    # TODO: Customize based on feature flags.

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
        self.computing_allowance = kwargs.pop('computing_allowance', None)
        disable_fields = kwargs.pop('disable_fields', False)
        super().__init__(*args, **kwargs)
        if self.computing_allowance is not None:
            self.computing_allowance = ComputingAllowance(
                self.computing_allowance)
            self._update_field_attributes()
        if disable_fields:
            for field in self.fields:
                self.fields[field].disabled = True

    def _update_field_attributes(self):
        """Update fields for select allowances."""
        if self.computing_allowance.is_instructional():
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
