from ast import literal_eval
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

PROJECT_ENABLE_PROJECT_REVIEW = import_from_settings('PROJECT_ENABLE_PROJECT_REVIEW', False)

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
    force_review = models.BooleanField(default=False)
    requires_review = models.BooleanField(default=True)
    history = HistoricalRecords()

    def clean(self):
        if 'Auto-Import Project'.lower() in self.title.lower():
            raise ValidationError('You must update the project title. You cannot have "Auto-Import Project" in the title.')

        if 'We do not have information about your research. Please provide a detailed description of your work and update your field of science. Thank you!' in self.description:
            raise ValidationError('You must update the project description.')

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

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']

        permissions = (
            ("can_view_all_projects", "Can view all projects"),
            ("can_review_pending_project_reviews", "Can review pending project reviews"),
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


class AttributeType(TimeStampedModel):
    """ AttributeType. """
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name', ]


class ProjectAttributeType(TimeStampedModel):
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    has_usage = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    is_private = models.BooleanField(default=True)
    is_changeable = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return '%s (%s)' % (self.name, self.attribute_type.name)

    def __repr__(self) -> str:
        return str(self)

    class Meta:
        ordering = ['name', ]


class ProjectAttribute(TimeStampedModel):
    proj_attr_type = models.ForeignKey(ProjectAttributeType, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    
    value = models.CharField(max_length=128)
    history = HistoricalRecords()

    def clean(self):
        if self.proj_attr_type.is_unique and self.allocation.allocationattribute_set.filter(proj_attr_type=self.proj_attr_type).exists():
            raise ValidationError("'{}' attribute already exists for this allocation.".format(
                self.proj_attr_type))

        expected_value_type = self.proj_attr_type.attribute_type.name.strip()

        if expected_value_type == "Int":
            # Changed from the literal casting to try catch because certain invalid inputs could lead to SyntaxErrors and
            # other errors.
            try:
                _ = int(self.value)
            except ValueError:
                raise ValidationError(
                'Invalid Value "%s" for "%s". Value must be an integer.' % (self.value, self.proj_attr_type.name))
        elif expected_value_type == "Float":
            try:
                _ = float(self.value)
            except ValueError:
                raise ValidationError(
                    'Invalid Value "%s" for "%s". Value must be a float.' % (self.value, self.proj_attr_type.name))
        elif expected_value_type == "Yes/No" and self.value not in ["Yes", "No"]:
            raise ValidationError(
                'Invalid Value "%s" for "%s". Allowed inputs are "Yes" or "No".' % (self.value, self.proj_attr_type.name))
        elif expected_value_type == "Date":
            try:
                datetime.datetime.strptime(self.value.strip(), "%Y-%m-%d")
            except ValueError:
                raise ValidationError(
                    'Invalid Value "%s" for "%s". Date must be in format YYYY-MM-DD' % (self.value, self.proj_attr_type.name))

    def __str__(self):
        return '%s' % (self.proj_attr_type.name)
    
class ProjectAttributeUsage(TimeStampedModel):
    """ ProjectAttributeUsage. """
    project_attribute = models.OneToOneField(
        ProjectAttribute, on_delete=models.CASCADE, primary_key=True)
    value = models.FloatField(default=0)
    history = HistoricalRecords()

    def __str__(self):
        return '{}: {}'.format(self.project_attribute.proj_attr_type.name, self.value)
    