import datetime

from django import forms
from django.shortcuts import get_object_or_404

from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectUserRoleChoice)
from coldfront.core.utils.common import import_from_settings

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
    FIELD_OF_SCIENCE = 'Field of Science'

    last_name = forms.CharField(
        label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    field_of_science = forms.CharField(
        label=FIELD_OF_SCIENCE, max_length=100, required=False)
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
    allocation = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'checked': 'checked'}), required=False)

    def __init__(self, request_user, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)

        allocation_query_set = project_obj.allocation_set.filter(
            status__name__in=['Active', 'New', 'Renewal Requested', ], resources__is_allocatable=True, is_locked=False)
        allocation_choices = [(allocation.id, "%s (%s) %s" % (allocation.get_parent_resource.name, allocation.get_parent_resource.resource_type.name,
                                                              allocation.description if allocation.description else '')) for allocation in allocation_query_set]
        allocation_choices.insert(0, ('__select_all__', 'Select All'))
        if allocation_query_set:
            self.fields['allocation'].choices = allocation_choices
            self.fields['allocation'].help_text = '<br/>Select allocations to add selected users to.'
        else:
            self.fields['allocation'].widget = forms.HiddenInput()


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


class ProjectReviewForm(forms.Form):
    reason = forms.CharField(label='Reason for not updating project information', widget=forms.Textarea(attrs={
                             'placeholder': 'If you have no new information to provide, you are required to provide a statement explaining this in this box. Thank you!'}), required=False)
    acknowledgement = forms.BooleanField(
        label='By checking this box I acknowledge that I have updated my project to the best of my knowledge', initial=False, required=True)

    def __init__(self, project_pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_obj = get_object_or_404(Project, pk=project_pk)
        now = datetime.datetime.now(datetime.timezone.utc)

        """
        if project_obj.grant_set.exists():
            latest_grant = project_obj.grant_set.order_by('-modified')[0]
            grant_updated_in_last_year = (
                now - latest_grant.created).days < 365
        else:
            grant_updated_in_last_year = None
        """

        """
        if project_obj.publication_set.exists():
            latest_publication = project_obj.publication_set.order_by(
                '-created')[0]
            publication_updated_in_last_year = (
                now - latest_publication.created).days < 365
        else:
            publication_updated_in_last_year = None
        """

        """
        if grant_updated_in_last_year or publication_updated_in_last_year:
            self.fields['reason'].widget = forms.HiddenInput()
        else:
            self.fields['reason'].required = True
        """


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
        self.fields['email_body'].initial = 'Dear {} managers \n{}'.format(
            project_review_obj.project.name,
            EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL)
        self.fields['cc'].initial = ', '.join(
            [EMAIL_DIRECTOR_EMAIL_ADDRESS] + EMAIL_ADMIN_LIST)


class ProjectReviewUserJoinForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    role = forms.CharField(max_length=30, disabled=True)
    selected = forms.BooleanField(initial=False, required=False)





from coldfront.core.project.models import ProjectUser
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator


class SavioProjectAllocationTypeForm(forms.Form):

    FCA = "FCA"
    CONDO = "CO"
    CHOICES = (
        (FCA, "Faculty Computing Allowance (FCA)"),
        (CONDO, "Condo Allocation"),
    )

    allocation_type = forms.ChoiceField(                                # TODO: Make these allocation attribute types / similar.
        choices=CHOICES,
        label='Allocation Type',
        widget=forms.Select())


class SavioProjectExistingPIForm(forms.Form):

    PI = forms.ModelChoiceField(
        label='Principal Investigator',
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select())

    def __init__(self, *args, **kwargs):

        self.allocation_type = kwargs.pop('allocation_type', None)

        super().__init__(*args, **kwargs)

        # PIs may only have one FCA, so only allow those without an active FCA
        # to be selected.
        queryset = User.objects.filter(userprofile__is_pi=True)
        if self.allocation_type == 'FCA':
            # TODO: What about pending PIs created via this form by others?
            pi_role = ProjectUserRoleChoice.objects.get(
                name='Principal Investigator')
            pis_with_existing_fcas = set(ProjectUser.objects.filter(
                role=pi_role,
                project__name__startswith='fc_',
                project__status__name__in=['New', 'Active']
            ).values_list('user__username', flat=True))
            self.fields['PI'].queryset = queryset.exclude(
                username__in=pis_with_existing_fcas)
        else:
            self.fields['PI'].queryset = queryset

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


class SavioProjectPoolAllocationsForm(forms.Form):

    pool = forms.BooleanField(
        initial=False,
        label='Yes, pool the PI\'s allocation with an existing project\'s.',
        required=False)


class SavioProjectPooledProjectSelectionForm(forms.Form):

    project = forms.ModelChoiceField(
        label='Project',
        queryset=Project.objects.none(),
        required=True,
        widget=forms.Select())

    def __init__(self, *args, **kwargs):
        self.allocation_type = kwargs.pop('allocation_type', None)
        super().__init__(*args, **kwargs)
        projects = Project.objects.filter(
            status__name__in=['Pending - Add', 'New', 'Active'])
        if self.allocation_type == 'FCA':
            projects = projects.filter(name__startswith='fc_')
        elif self.allocation_type == 'CO':
            projects = projects.filter(name__startswith='co_')
        # TODO: Add handling for other types.
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
            'The unique name of the project on the cluster, which must '
            'contain only lowercase letters and numbers.'),
        label='Name',
        max_length=8,
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

    # TODO: Add field_of_science.


class SavioProjectSurveyForm(forms.Form):

    # TODO: This will not apply to Condo, probably.

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
            'Existing computing resources (outside of SAVIO) currently being '
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
            'BRC has 4 512GB large memory nodes. What is your expected use of '
            'these nodes?'),
        required=False)
    data_storage_space = forms.CharField(
        help_text=(
            'BRC provides each user with 10GB of backed up home directory '
            'space; and free access to a not-backed-up shared Global Scratch '
            'high performance parallel filesystem. Research projects that '
            'need to share datasets among their team members can also be '
            'allocated up to 30 GB of not-backed-up shared filesystem space '
            'on request. Users needing more storage can be allocated space on '
            'IST\'s utility storage tier (currently $50/TB/mo as of '
            '7/1/2014). Please indicate if you need additional space and how '
            'much.'),
        label='Data Storage Space',
        required=False)
    io = forms.CharField(
        help_text=(
            'SAVIO provides a shared Lustre parallel filesystem for jobs '
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
        label='Interconnect performance')
    network_to_internet = forms.CharField(
        help_text=(
            'Do you need to transfer large amounts of data to and/or from the '
            'cluster? If yes, what is the max you you might transfer in a '
            'day? What would be typical for a month? Do you have need for '
            'file sharing of large datasets?'),
        label='Network connection from SAVIO to the Internet',
        required=False)
    new_hardware_interest = forms.MultipleChoiceField(
        choices=(
            ('Intel Phi', 'Intel Phi'),
            ('Nvidia GPU', 'Nvidia GPU'),
        ),
        help_text=(
            'Please indicate which of the following hardware would be of '
            'interest to you. BRC currently have some nodes equipped with '
            'Nvidia GPUs and no Intel Phi, but it is under consideration. '),
        label='Many-core, Intel Phi or Nvidia GPU',
        required=False,
        widget=forms.CheckboxSelectMultiple())
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
