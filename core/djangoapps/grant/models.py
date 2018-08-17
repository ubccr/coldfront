from django.core.validators import (MaxLengthValidator, MaxValueValidator,
                                    MinLengthValidator)
from django.db import models
from model_utils.models import TimeStampedModel

from core.djangoapps.project.models import Project


class GrantFundingAgency(TimeStampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class GrantStatusChoice(TimeStampedModel):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Grant(TimeStampedModel):
    """ Grant model """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    project_number = models.CharField(
        'Project Number from funding agency',
        validators=[MinLengthValidator(3), MaxLengthValidator(255)],
        max_length=255,
    )
    title = models.CharField(
        validators=[MinLengthValidator(3), MaxLengthValidator(255)],
        max_length=255,
    )
    ROLE_CHOICES = (
        ('PI', 'Principal Investigator (PI)'),
        ('CoPI', 'Co-Principal Investigator (CoPI)'),
        ('SP', 'Senior Personnel (SP)'),
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
    )
    grant_pi_full_name = models.CharField(max_length=255, blank=True)
    funding_agency = models.ForeignKey(GrantFundingAgency, on_delete=models.CASCADE)
    other_funding_agency = models.CharField(max_length=255, blank=True)
    other_award_number = models.CharField(max_length=255, blank=True)
    project_start = models.DateField('Project Start Date')
    project_end = models.DateField('Project End Date')
    percent_credit = models.FloatField(validators=[MaxValueValidator(100)])
    direct_funding = models.FloatField()
    total_amount_awarded = models.FloatField()
    status = models.ForeignKey(GrantStatusChoice, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Grants"
