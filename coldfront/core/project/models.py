import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.field_of_science.models import FieldOfScience
from coldfront.core.utils.common import import_from_settings

PROJECT_ENABLE_PROJECT_REVIEW = import_from_settings('PROJECT_ENABLE_PROJECT_REVIEW', False)
PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING = import_from_settings(
    'PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING',
    60
)
PROJECT_DAYS_TO_REVIEW_BEFORE_EXPIRING = import_from_settings(
    'PROJECT_DAYS_TO_REVIEW_BEFORE_EXPIRING',
    30
)


class ProjectStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class ProjectTypeChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Project(TimeStampedModel):

    DEFAULT_DESCRIPTION = ''
    DESCRIPTION_HELP_TEXT = """
Please provide a brief description or abstract about your project including any applications or
workflows you intend to use, and how you primarily intend to use the system, including if PHI will
be stored. Please include your area of research and your department. If this is for a class please
put the approximate class size.
"""

    title = models.CharField(max_length=255,)
    pi = models.ForeignKey(User, on_delete=models.CASCADE,)
    pi_username = models.CharField(
        verbose_name="PI Username",
        max_length=20,
        blank=True,
        help_text='Required if you will not be the PI of this project. Only faculty and staff can be the PI'
    )
    requestor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requestor_user')
    description = models.TextField(
        default=DEFAULT_DESCRIPTION,
        help_text=DESCRIPTION_HELP_TEXT,
        validators=[
            MinLengthValidator(
                10,
                'The project description must be > 10 characters.',
            )
        ],
    )

    slurm_account_name = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        unique=True
    )
    field_of_science = models.ForeignKey(FieldOfScience, on_delete=models.CASCADE, default=FieldOfScience.DEFAULT_PK)
    type = models.ForeignKey(
        ProjectTypeChoice,
        on_delete=models.CASCADE,
        help_text="This cannot be changed once your project is submitted. Class projects expire at the end of every semester. Research projects expire once a year."
    )
    private = models.BooleanField(
        default=False,
        help_text="A private project will not show up in the PI search results if someone searchs for you/your PI."
    )
    status = models.ForeignKey(ProjectStatusChoice, on_delete=models.CASCADE)
    force_review = models.BooleanField(default=False)
    requires_review = models.BooleanField(default=True)
    end_date = models.DateField()
    max_managers = models.IntegerField()
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
            return self.grant_set.order_by('-modified')[0]
        else:
            return None

    @property
    def latest_publication(self):
        if self.publication_set.exists():
            return self.publication_set.order_by('-created')[0]
        else:
            return None

    @property
    def needs_review(self):

        if self.status.name in ['Archived', 'Expired', 'Review Pending']:
            return False

        if self.force_review is True:
            return True

        return False

    @property
    def can_be_reviewed(self):
        if self.status.name in ['Archived', 'Denied', 'Review Pending']:
            return False

        if self.force_review is True:
            return False

        if not PROJECT_ENABLE_PROJECT_REVIEW:
            return False

        if self.requires_review is False:
            return False

        if self.status.name == 'Active' and self.expires_in <= PROJECT_DAYS_TO_REVIEW_BEFORE_EXPIRING:
            return True

        if self.status.name == 'Expired' and self.expires_in >= -PROJECT_DAYS_TO_REVIEW_AFTER_EXPIRING:
            return True

        return False

    @property
    def expires_in(self):
        return (self.end_date - datetime.date.today()).days

    @property
    def list_of_manager_usernames(self):
        project_managers = self.projectuser_set.filter(
            role=ProjectUserRoleChoice.objects.get(name='Manager')
        )
        return [manager.user.username for manager in project_managers]

    def get_current_num_managers(self):
        return self.projectuser_set.filter(
            role=ProjectUserRoleChoice.objects.get(name='Manager'),
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            ).count()

    def check_exceeds_max_managers(self, num_added_managers=0):
        """
        Checks if the number of added managers exceeds the max allowed managers.
        """
        return (self.get_current_num_managers() + num_added_managers) > self.max_managers

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']

        permissions = (
            ("can_view_all_projects", "Can view all projects"),
            ("can_review_pending_projects", "Can review pending project requests/reviews"),
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
    is_private = models.BooleanField(default=True)
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
    status = models.ForeignKey(ProjectReviewStatusChoice, on_delete=models.CASCADE, verbose_name='Status')
    project_updates = models.TextField(blank=True, null=True)
    allocation_renewals = models.TextField(blank=True, null=True)
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
