from django.core.validators import RegexValidator
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords


class BillingProject(TimeStampedModel):
    """The prefix of a complete billing ID (i.e., the '123456' of
    '123456-789')."""

    identifier = models.CharField(
        max_length=6,
        unique=True,
        validators=[
            RegexValidator(
                r'^[0-9]{6}$', message='Identifier must contain 6 numbers.')
        ])
    description = models.CharField(max_length=255)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Billing Project'
        verbose_name_plural = 'Billing Projects'


class BillingActivity(TimeStampedModel):
    """The suffix of a complete billing ID (i.e., the '789' of
    '123456-789')."""

    billing_project = models.ForeignKey(
        BillingProject, on_delete=models.CASCADE)
    identifier = models.CharField(
        max_length=3,
        validators=[
            RegexValidator(
                r'^[0-9]{3}$', message='Identifier must contain 3 numbers.')
        ])
    description = models.CharField(max_length=255)
    is_valid = models.BooleanField(default=False)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('billing_project', 'identifier')
        verbose_name = 'Billing Activity'
        verbose_name_plural = 'Billing Activities'

    def full_id(self):
        """Return a string representing the fully-formed billing ID
        represented by the instance."""
        return f'{self.billing_project.identifier}-{self.identifier}'
