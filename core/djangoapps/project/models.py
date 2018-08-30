import textwrap

from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError
from django.db import models
import datetime
from model_utils.models import TimeStampedModel

from common.djangoapps.field_of_science.models import FieldOfScience

from simple_history.models import HistoricalRecords


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

    title = models.CharField(max_length=255,)
    pi = models.ForeignKey(User, on_delete=models.CASCADE,)
    description = models.TextField(
        default=DEFAULT_DESCRIPTION,
        validators=[
            MinLengthValidator(
                10,
                'The project description must be > 10 characters.',
            )
        ],
    )

    field_of_science = models.ForeignKey(FieldOfScience, on_delete=models.CASCADE, default=FieldOfScience.DEFAULT_PK)
    status = models.ForeignKey(ProjectStatusChoice, on_delete=models.CASCADE)
    project_needs_review = models.BooleanField(default=False)
    project_requires_review = models.BooleanField(default=True)
    history = HistoricalRecords()

    def clean(self):
        if 'Auto-Import Project'.lower() in self.title.lower():
            raise ValidationError('You must update the project title. You cannot have "Auto-Import Project" in the title.')

    @property
    def last_project_review(self):
        if self.projectreview_set.exists():
            return self.projectreview_set.order_by('-created')[0]
        else:
            return None

    @property
    def latest_grant(self):
        if self.grant_set.exists():
            return self.grant_set.order_by('-created')[0]
        else:
            return None

    @property
    def latest_publication(self):
        if self.publication_set.exists():
            return self.publication_set.order_by('-created')[0]
        else:
            return None

    @property
    def get_project_needs_review(self):
        now = datetime.datetime.now(datetime.timezone.utc)

        if self.project_needs_review is True:
            return True

        if self.project_requires_review is False:
            return False

        if self.projectreview_set.exists():
            last_review = self.projectreview_set.order_by('-created')[0]
            last_review_over_365_days = (now - last_review.created).days > 365
        else:
            last_review = None

        days_since_project_creation = (now - self.created).days

        if days_since_project_creation > 365 and last_review is None:
            return True

        if last_review and last_review_over_365_days:
            return True

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']

        permissions = (
            ("can_view_all_projects", "Can see all projects"),
            ("can_review_pending_project_reviews", "Can review pending project reviews"),
        )


class ProjectReviewStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class ProjectReview(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    status = models.ForeignKey(ProjectReviewStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
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
    status = models.ForeignKey(ProjectUserStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    enable_notifications = models.BooleanField(default=True)
    history = HistoricalRecords()

    def __str__(self):
        return '%s %s (%s)' % (self.user.first_name, self.user.last_name, self.user.username)

    class Meta:
        unique_together = ('user', 'project')
        verbose_name_plural = "Project User Status"
