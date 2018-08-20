import textwrap

from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
import datetime
from model_utils.models import TimeStampedModel

from common.djangoapps.field_of_science.models import FieldOfScience


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
    force_project_review = models.BooleanField(default=False)


    @property
    def lastest_grant(self):
        if self.grant_set.exists():
            return self.grant_set.order_by('-created')[0]
        else:
            return None

    @property
    def lastest_publication(self):
        if self.publication_set.exists():
            return self.publication_set.order_by('-created')[0]
        else:
            return None


    @property
    def project_needs_review(self):
        now = datetime.datetime.now(datetime.timezone.utc)

        if self.grant_set.exists():
            latest_grant = self.grant_set.order_by('-created')[0]
            grant_over_365_days = (now - latest_grant.created).days > 365
        else:
            grant_over_365_days = None

        if self.publication_set.exists():
            latest_publication = self.publication_set.order_by('-created')[0]
            publication_over_365_days = (now - latest_publication.created).days > 365
        else:
            publication_over_365_days = None

        if self.projectreview_set.exists():
            latest_review = self.projectreview_set.order_by('-created')[0]
            latest_review_over_365_days = (now - latest_review.created).days > 365
        else:
            latest_review_over_365_days = None
            latest_review = None

        print(latest_review, latest_review_over_365_days)
        if latest_review and not latest_review_over_365_days:
            return False
        elif latest_review_over_365_days:
            return True
        elif grant_over_365_days and publication_over_365_days:
            return True
        else:
            return False

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']

        permissions = (
            ("can_view_all_projects", "Can see all projects"),
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

    def __str__(self):
        return '%s %s (%s)' % (self.user.first_name, self.user.last_name, self.user.username)

    class Meta:
        unique_together = ('user', 'project')
        verbose_name_plural = "Project User Status"
