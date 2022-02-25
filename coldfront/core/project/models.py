import datetime
import textwrap

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.utils.common import import_from_settings

PROJECT_ENABLE_PROJECT_REVIEW = import_from_settings(
    'PROJECT_ENABLE_PROJECT_REVIEW', False)


class ProjectStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Project(TimeStampedModel):

    DEFAULT_DESCRIPTION = '''
We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!
        '''

    name = models.CharField(max_length=255, unique=True, blank=True, null=True)
    title = models.CharField(max_length=255,)
    description = models.TextField(
        default=DEFAULT_DESCRIPTION,
        validators=[
            MinLengthValidator(
                10,
                'The project description must be > 10 characters.',
            )
        ],
    )

    field_of_science = models.ForeignKey(
        FieldOfScience, on_delete=models.CASCADE, default=FieldOfScience.DEFAULT_PK)
    status = models.ForeignKey(ProjectStatusChoice, on_delete=models.CASCADE)
    force_review = models.BooleanField(default=False)
    requires_review = models.BooleanField(default=True)
    history = HistoricalRecords()

    def clean(self):
        if 'Auto-Import Project'.lower() in self.title.lower():
            raise ValidationError(
                'You must update the project title. You cannot have "Auto-Import Project" in the title.')

        if 'We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!' in self.description:
            raise ValidationError('You must update the project description.')

    def save(self, *args, **kwargs):
        """If the Project previously existed and its status has changed,
        update any pending ProjectUserJoinRequests."""
        if self.pk:
            old_obj = Project.objects.get(pk=self.pk)
            if old_obj.status.name != self.status.name:
                pending_status = ProjectUserStatusChoice.objects.get(
                    name='Pending - Add')
                if self.status.name == 'Active':
                    # If the status changed to 'Active', create another join
                    # request, since only the latest created request is
                    # considered. This ensures that the auto-approval delay
                    # begins after the project becomes active.
                    project_users = self.projectuser_set.filter(
                        status=pending_status)

                    for project_user in project_users:
                        try:
                            reason = project_user.projectuserjoinrequest_set.latest('created').reason
                            ProjectUserJoinRequest.objects.create(
                                project_user=project_user,
                                reason=reason)
                        except ProjectUserJoinRequest.DoesNotExist:
                            # use default reason if no prior request exists
                            ProjectUserJoinRequest.objects.create(
                                    project_user=project_user)

                elif self.status.name == 'Denied':
                    # If the status changed to 'Denied', deny all pending
                    # join requests.
                    denied_status = ProjectUserStatusChoice.objects.get(
                        name='Denied')
                    self.projectuser_set.filter(
                        status=pending_status).update(status=denied_status)

        super().save(*args, **kwargs)

    @property
    def last_project_review(self):
        if self.projectreview_set.exists():
            return self.projectreview_set.order_by('-created')[0]
        else:
            return None

    @property
    def latest_grant(self):
        """
        if self.grant_set.exists():
            return self.grant_set.order_by('-modified')[0]
        else:
            return None
        """
        return None

    @property
    def latest_publication(self):
        """
        if self.publication_set.exists():
            return self.publication_set.order_by('-created')[0]
        else:
            return None
        """
        return None

    @property
    def needs_review(self):

        if self.status.name == 'Archived':
            return False

        now = datetime.datetime.now(datetime.timezone.utc)

        if self.force_review is True:
            return True

        if not PROJECT_ENABLE_PROJECT_REVIEW:
            return False

        if self.requires_review is False:
            return False

        if self.projectreview_set.exists():
            last_review = self.projectreview_set.order_by('-created')[0]
            last_review_over_365_days = (now - last_review.created).days > 365
        else:
            last_review = None

        days_since_creation = (now - self.created).days

        if days_since_creation > 365 and last_review is None:
            return True

        if last_review and last_review_over_365_days:
            return True

        return False

    def pis(self):
        """Return a queryset of User objects that are PIs on this
        project, ordered by username."""
        pi_user_pks = self.projectuser_set.filter(
            role__name='Principal Investigator').values_list('user', flat=True)
        return User.objects.filter(pk__in=pi_user_pks).order_by('username')

    def managers(self):
        """Return a queryset of User objects that are Managers on this
        project, ordered by username."""
        manager_user_pks = self.projectuser_set.filter(
            role__name='Manager').values_list('user', flat=True)
        return User.objects.filter(
            pk__in=manager_user_pks).order_by('username')

    def is_pooled(self):
        """Return whether this project is a pooled project. In
        particular, it is pooled if it has more than one PI."""
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        return self.projectuser_set.filter(role=pi_role).count() > 1

    def managers_and_pis_emails(self):
        """Return a list of emails belonging to active managers and PIs that
        have enable_notifications=True."""
        pi_condition = Q(
            role__name='Principal Investigator', status__name='Active',
            enable_notifications=True)
        manager_condition = Q(role__name='Manager', status__name='Active')

        return list(
            self.projectuser_set.filter(
                pi_condition | manager_condition
            ).distinct().values_list('user__email', flat=True))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['title']

        permissions = (
            ("can_view_all_projects", "Can view all projects"),
            ("can_review_pending_project_reviews",
             "Can review pending project reviews"),
        )


class ProjectAdminComment(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()

    def __str__(self):
        return self.comment


class ProjectUserMessage(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return self.message


class ProjectReviewStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class ProjectReview(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    status = models.ForeignKey(
        ProjectReviewStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    reason_for_not_updating_project = models.TextField(blank=True, null=True)
    history = HistoricalRecords()


class ProjectUserRoleChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class ProjectUserStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class ProjectUser(TimeStampedModel):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    role = models.ForeignKey(ProjectUserRoleChoice, on_delete=models.CASCADE)
    status = models.ForeignKey(
        ProjectUserStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    enable_notifications = models.BooleanField(default=True)
    history = HistoricalRecords()

    def __str__(self):
        return '%s %s (%s)' % (self.user.first_name, self.user.last_name, self.user.username)

    class Meta:
        unique_together = ('user', 'project')
        verbose_name_plural = "Project User Status"


class ProjectUserJoinRequest(TimeStampedModel):
    """A model to track when a user requested to join a project."""
    DEFAULT_REASON = 'This is the default join reason.'

    project_user = models.ForeignKey(ProjectUser, on_delete=models.CASCADE)
    reason = models.TextField(
            default=DEFAULT_REASON,
            validators=[
                MinLengthValidator(20, 'The project join reason must be > 20 characters.',)
            ])

    def __str__(self):
        user = self.project_user.user
        return (
            f'{user.first_name} {user.last_name} ({user.username}) '
            f'({self.created}) ({self.reason})')

    class Meta:
        verbose_name = 'Project User Join Request'
        verbose_name_plural = 'Project User Join Requests'


class ProjectAllocationRequestStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


def savio_project_request_state_schema():
    """Return the schema for the SavioProjectAllocationRequest.state
    field."""
    return {
        'eligibility': {
            'status': 'Pending',
            'justification': '',
            'timestamp': ''
        },
        'readiness': {
            'status': 'Pending',
            'justification': '',
            'timestamp': ''
        },
        'setup': {
            'status': 'Pending',
            'name_change': {
                'requested_name': '',
                'final_name': '',
                'justification': ''
            },
            'timestamp': ''
        },
        'other': {
            'justification': '',
            'timestamp': ''
        }
    }


def savio_project_request_ica_extra_fields_schema():
    """Return the schema for the
    SavioProjectAllocationRequest.extra_fields for Instructional Compute
    Allowance (ICA) projects."""
    return {
        'semester': '',
        'year': '',
        'num_students': 0,
        'num_gsis': 0,
        'manager_experience_description': '',
        'student_experience_description': '',
        'max_simultaneous_jobs': 0,
        'max_simultaneous_nodes': 0,
    }


def savio_project_request_ica_state_schema():
    """Return the schema for the SavioProjectAllocationRequest.state
    field for Instructional Compute Allowance (ICA) projects."""
    schema = savio_project_request_state_schema()
    schema['allocation_dates'] = {
        'status': 'Pending',
        'dates': {
            'start': '',
            'end': '',
        },
        'timestamp': '',
    }
    schema['memorandum_signed'] = {
        'status': 'Pending',
        'timestamp': '',
    }
    return schema


def savio_project_request_recharge_state_schema():
    """Return the schema for the SavioProjectAllocationRequest.state
    field for Recharge projects."""
    schema = savio_project_request_state_schema()
    schema['memorandum_signed'] = {
        'status': 'Pending',
        'timestamp': '',
    }
    return schema


def savio_project_request_recharge_extra_fields_schema():
    """Return the schema for the
    SavioProjectAllocationRequest.extra_fields field for Recharge
    projects."""
    return {
        'num_service_units': '',
        'campus_chartstring': '',
        'chartstring_account_type': '',
        'chartstring_contact_name': '',
        'chartstring_contact_email': '',
    }


def vector_project_request_state_schema():
    """Return the schema for the VectorProjectAllocationRequest.state
    field."""
    return {
        'eligibility': {
            'status': 'Pending',
            'justification': '',
            'timestamp': ''
        },
        'setup': {
            'status': 'Pending',
            'name_change': {
                'requested_name': '',
                'final_name': '',
                'justification': ''
            },
            'timestamp': ''
        }
    }


class SavioProjectAllocationRequest(TimeStampedModel):
    requester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='savio_requester')

    FCA = 'FCA'
    CO = 'CO'
    ICA = 'ICA'
    PCA = 'PCA'
    RECHARGE = 'RECHARGE'
    ALLOCATION_TYPE_CHOICES = (
        (FCA, 'Faculty Compute Allowance (FCA)'),
        (CO, 'Condo Allocation'),
        (ICA, 'Instructional Compute Allowance (ICA)'),
        (PCA, 'Partner Compute Allowance (PCA)'),
        (RECHARGE, 'Recharge Allocation'),
    )
    allocation_type = models.CharField(
        max_length=16, choices=ALLOCATION_TYPE_CHOICES)

    pi = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='savio_pi')
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    pool = models.BooleanField(default=False)
    survey_answers = models.JSONField()
    status = models.ForeignKey(
        ProjectAllocationRequestStatusChoice, on_delete=models.CASCADE,
        verbose_name='Status')
    state = models.JSONField(default=savio_project_request_state_schema)
    extra_fields = models.JSONField(default=dict)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        # On creation, set the requested_name.
        if not self.pk:
            self.state['setup']['name_change']['requested_name'] = \
                self.project.name
        super().save(*args, **kwargs)

    def __str__(self):
        name = (
            f'{self.project.name} - {self.pi.first_name} {self.pi.last_name}')
        if self.pool:
            name = f'{name} (Pooled)'
        return name

    class Meta:
        verbose_name = 'Savio Project Allocation Request'
        verbose_name_plural = 'Savio Project Allocation Requests'


class VectorProjectAllocationRequest(TimeStampedModel):
    requester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='vector_requester')

    pi = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='vector_pi')
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    status = models.ForeignKey(
        ProjectAllocationRequestStatusChoice, on_delete=models.CASCADE,
        verbose_name='Status')
    state = models.JSONField(default=vector_project_request_state_schema)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        # On creation, set the requested_name.
        if not self.pk:
            self.state['setup']['name_change']['requested_name'] = \
                self.project.name
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f'{self.project.name} - {self.pi.first_name} {self.pi.last_name}')

    class Meta:
        verbose_name = 'Vector Project Allocation Request'
        verbose_name_plural = 'Vector Project Allocation Requests'


class ProjectUserRemovalRequestStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)
    # one of "Pending", "Processing", "Complete"


class ProjectUserRemovalRequest(TimeStampedModel):
    project_user = models.ForeignKey(ProjectUser, on_delete=models.CASCADE)
    requester = models.ForeignKey(User, on_delete=models.CASCADE)
    request_time = models.DateTimeField(auto_now_add=True)
    completion_time = models.DateTimeField(null=True)
    status = models.ForeignKey(ProjectUserRemovalRequestStatusChoice, on_delete=models.CASCADE, null=True)


