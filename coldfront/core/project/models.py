import datetime
import textwrap

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
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

    JOINS_AUTO_APPROVAL_DELAY = datetime.timedelta(hours=6)
    joins_auto_approval_delay = models.DurationField(
        default=JOINS_AUTO_APPROVAL_DELAY)

    def clean(self):
        if 'Auto-Import Project'.lower() in self.title.lower():
            raise ValidationError(
                'You must update the project title. You cannot have "Auto-Import Project" in the title.')

        if 'We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!' in self.description:
            raise ValidationError('You must update the project description.')

        if self.joins_auto_approval_delay < datetime.timedelta():
            raise ValidationError('Delay must be non-negative.')

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

    def __str__(self):
        return self.title

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

    project_user = models.ForeignKey(ProjectUser, on_delete=models.CASCADE)

    def __str__(self):
        user = self.project_user.user
        return (
            f'{user.first_name} {user.last_name} ({user.username}) '
            f'({self.created})')

    class Meta:
        verbose_name = 'Project User Join Request'
        verbose_name_plural = 'Project User Join Requests'


class ProjectAllocationRequestStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class SavioProjectAllocationRequest(TimeStampedModel):
    requester = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='savio_requester')

    FCA = 'FCA'
    CO = 'CO'
    ALLOCATION_TYPE_CHOICES = (
        # TODO: Add the rest.
        (FCA, 'Faculty Compute Allowance (FCA)'),
        (CO, 'Condo Allocation'),
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
    history = HistoricalRecords()

    def __str__(self):
        # TODO: Include the word "Pooled" if applicable
        return f''

    class Meta:
        # TODO: unique_together?
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
    history = HistoricalRecords()

    def __str__(self):
        # TODO
        return f''

    class Meta:
        # TODO: unique_together?
        verbose_name = 'Vector Project Allocation Request'
        verbose_name_plural = 'Vector Project Allocation Requests'
