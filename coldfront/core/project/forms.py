import datetime

from django import forms
from django.shortcuts import get_object_or_404
from django.db.models import Q

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.project.models import (Project, ProjectReview,
                                           ProjectUserRoleChoice,
                                           ProjectAllocationRequestStatusChoice)
from coldfront.core.utils.common import import_from_settings

from durationwidget.widgets import TimeDurationWidget

EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL = import_from_settings(
    'EMAIL_DIRECTOR_PENDING_PROJECT_REVIEW_EMAIL')
EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST', [])
EMAIL_DIRECTOR_EMAIL_ADDRESS = import_from_settings(
    'EMAIL_DIRECTOR_EMAIL_ADDRESS', '')


class ProjectSearchForm(forms.Form):
    """ Search form for the Project list page.
    """
    LAST_NAME = 'Last Name (PI)'
    USERNAME = 'Username (PI)'
    FIELD_OF_SCIENCE = 'Field of Science'
    PROJECT_TITLE = 'Project Title'
    PROJECT_NAME = 'Project Name'
    CLUSTER_NAME = 'Cluster Name'

    CLUSTER_NAME_CHOICES = [
        ('', '-----'),
        ('ABC', 'ABC'),
        ('Savio', 'Savio'),
        ('Vector', 'Vector'),
    ]

    last_name = forms.CharField(label=LAST_NAME, max_length=100, required=False)
    username = forms.CharField(label=USERNAME, max_length=100, required=False)
    field_of_science = forms.CharField(label=FIELD_OF_SCIENCE, max_length=100, required=False)
    project_title = forms.CharField(label=PROJECT_TITLE, max_length=100, required=False)
    project_name = forms.CharField(label=PROJECT_NAME, max_length=100, required=False)
    cluster_name = forms.ChoiceField(
        label=CLUSTER_NAME, choices=CLUSTER_NAME_CHOICES, required=False,
        widget=forms.Select())
    show_all_projects = forms.BooleanField(initial=False, required=False)


class ProjectAddUserForm(forms.Form):
    username = forms.CharField(max_length=150, disabled=True)
    first_name = forms.CharField(max_length=30, required=False, disabled=True)
    last_name = forms.CharField(max_length=150, required=False, disabled=True)
    email = forms.EmailField(max_length=100, required=False, disabled=True)
    source = forms.CharField(max_length=16, disabled=True)
    role = forms.ModelChoiceField(
        queryset=ProjectUserRoleChoice.objects.all().filter(~Q(name='Principal Investigator')),
        empty_label=None)
    selected = forms.BooleanField(initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._username = kwargs.get('initial', {}).get('username', None)


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
        queryset=ProjectUserRoleChoice.objects.all().filter(~Q(name='Principal Investigator')),
        empty_label=None)
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
    auto_approval_time = forms.DateTimeField(disabled=True)
    selected = forms.BooleanField(initial=False, required=False)


class ProjectUpdateForm(forms.ModelForm):

    joins_auto_approval_delay = forms.DurationField(
        label='Auto-Approval Delay for Join Requests',
        widget=TimeDurationWidget(
            show_days=True, show_hours=True, show_minutes=False,
            show_seconds=False),
        required=False,
        help_text=(
            'Requests to join the project will automatically be approved '
            'after a delay period, allowing managers to review them. The '
            'default is 6 hours. An empty input is interpreted as 0.'))

    class Meta:
        model = Project
        fields = (
            'title', 'description', 'field_of_science',
            'joins_auto_approval_delay',)


# TODO: Once finalized, move these imports above.
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import SavioProjectAllocationRequest
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.core.validators import RegexValidator


class DisabledChoicesSelectWidget(forms.Select):

    def __init__(self, *args, **kwargs):
        self.disabled_choices = kwargs.pop('disabled_choices', set())
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None,
                      attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex,
            attrs=attrs)
        try:
            if int(str(value)) in self.disabled_choices:
                option['attrs']['disabled'] = True
        except Exception:
            pass
        return option


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

        super().__init__(*args, **kwargs)

        # PIs may only have one FCA, so only allow those without an active FCA
        # to be selected. The same applies for PCA.
        queryset = User.objects.all()
        exclude_user_pks = set()
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        if self.allocation_type == 'FCA':
            pis_with_existing_fcas = set(ProjectUser.objects.filter(
                role=pi_role,
                project__name__startswith='fc_',
                project__status__name__in=['New', 'Active']
            ).values_list('user__pk', flat=True))
            status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
            pis_with_pending_requests = set(
                SavioProjectAllocationRequest.objects.filter(
                    allocation_type=SavioProjectAllocationRequest.FCA,
                    status=status
                ).values_list('pi__pk', flat=True))
            exclude_user_pks.update(
                set.union(pis_with_existing_fcas, pis_with_pending_requests))
        elif self.allocation_type == 'PCA':
            pis_with_existing_pcas = set(ProjectUser.objects.filter(
                role=pi_role,
                project__name__startswith='pc_',
                project__status__name__in=['New', 'Active']
            ).values_list('user__pk', flat=True))
            status = ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
            pis_with_pending_requests = set(
                SavioProjectAllocationRequest.objects.filter(
                    allocation_type=SavioProjectAllocationRequest.PCA,
                    status=status
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
        kwargs.pop('breadcrumb_pi', None)
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
    field_of_science = forms.ModelChoiceField(
        empty_label=None,
        queryset=FieldOfScience.objects.all())

    def __init__(self, *args, **kwargs):
        self.allocation_type = kwargs.pop('allocation_type', None)
        kwargs.pop('breadcrumb_pi', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        cleaned_data = super().clean()
        name = cleaned_data['name'].lower()
        if self.allocation_type == SavioProjectAllocationRequest.FCA:
            name = f'fc_{name}'
        elif self.allocation_type == SavioProjectAllocationRequest.CO:
            name = f'co_{name}'
        elif self.allocation_type == SavioProjectAllocationRequest.PCA:
            name = f'pc_{name}'
        if Project.objects.filter(name=name):
            raise forms.ValidationError(
                f'A project with name {name} already exists.')
        return name


class SavioProjectSurveyForm(forms.Form):

    # TODO: Modify survey questions for Condo.

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
        label='Interconnect performance',
        required=False)
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

    def __init__(self, *args, **kwargs):
        disable_fields = kwargs.pop('disable_fields', False)
        super().__init__(*args, **kwargs)
        if disable_fields:
            for field in self.fields:
                self.fields[field].disabled = True


class ProjectAllocationReviewForm(forms.Form):

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
        for prefix in ('co_', 'fc_', 'pc_'):
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


class SavioProjectReviewDenyForm(forms.Form):

    justification = forms.CharField(
        help_text=(
            'Provide reasoning for your decision. It will be included in the '
            'notification email.'),
        label='Justification',
        validators=[MinLengthValidator(10)],
        required=True,
        widget=forms.Textarea(attrs={'rows': 3}))


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
    field_of_science = forms.ModelChoiceField(
        empty_label=None,
        queryset=FieldOfScience.objects.all())

    def clean_name(self):
        cleaned_data = super().clean()
        name = cleaned_data['name'].lower()
        name = f'vector_{name}'
        if Project.objects.filter(name=name):
            raise forms.ValidationError(
                f'A project with name {name} already exists.')
        return name


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
