# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinLengthValidator, RegexValidator
from django.db import models
from model_utils.models import TimeStampedModel
from simple_history.models import HistoricalRecords

from coldfront.core.project.models import Project


class GrantFundingAgency(TimeStampedModel):
    """A grant funding agency is an agency that funds projects. Examples include Department of Defense (DoD) and National Aeronautics and Space Administration (NASA).

    Attributes:
        name (str): agency name
    """

    class GrantFundingAgencyManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=255, unique=True)
    objects = GrantFundingAgencyManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return [self.name]


class GrantStatusChoice(TimeStampedModel):
    """A grant status choice is an option a user has when setting the status of a grant. Examples include Active, Archived, and Pending.

    Attributes:
        name (str): status name
    """

    class Meta:
        ordering = ("name",)

    class GrantStatusManager(models.Manager):
        def get_by_natural_key(self, name):
            return self.get(name=name)

    name = models.CharField(max_length=64, unique=True)
    objects = GrantStatusManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return [self.name]


class MoneyField(models.CharField):
    validators = [
        RegexValidator(
            r"\$*[\d,.]{1,}$", "Enter only digits, decimals, commas, dollar signs, or spaces.", "Invalid input."
        )
    ]

    def to_python(self, value):
        value = super().to_python(value)
        if value:
            value = value.replace(" ", "")
            value = value.replace(",", "")
            value = value.replace("$", "")
        return value


class PercentField(models.CharField):
    validators = [
        RegexValidator(
            r"^[\d,.]{1,6}\%*$", "Enter only digits, decimals, percent symbols, or spaces.", "Invalid input."
        )
    ]

    def to_python(self, value):
        value = super().to_python(value)
        if value:
            value = value.replace(" ", "")
            value = value.replace("%", "")
            try:
                if float(value) > 100:
                    raise ValidationError("Percent credit should be less than 100")
            except ValueError:
                pass
        return value


class Grant(TimeStampedModel):
    """A grant is funding that a PI receives for their project.

    Attributes:
        project (Project): links the project to the grant
        title (str): grant title
        grant_number (str): grant number from agency used for identification
        role (str): role of the user in charge of the grant
        grant_pi_full_name (str): PI's name
        funding_agency (GrantFundingAgency): represents the agency funding the grant
        other_funding_agency (GrantFundingAgency): optional field indicating any other agency that funded the grant
        other_award_number (str): indicates an alternate grant ID number that a PI might have for an award
        grant_start (Date): represents grant start date
        grant_end (Date): represents the grant end date
        percent_credit (float): indicates how much of the grant is awarded as credit
        direct_funding (float): indicates how much of the grant is directly funded
        total_amount_awarded (float): indicates the total amount awarded
        status (GrantStatusChoice): represents the status of the grant
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(
        validators=[MinLengthValidator(3), MaxLengthValidator(255)],
        max_length=255,
    )
    grant_number = models.CharField(
        "Grant Number from funding agency",
        validators=[MinLengthValidator(3), MaxLengthValidator(255)],
        max_length=255,
    )
    ROLE_CHOICES = (
        ("PI", "Principal Investigator (PI)"),
        ("CoPI", "Co-Principal Investigator (CoPI)"),
        ("SP", "Senior Personnel (SP)"),
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
    )

    grant_pi_full_name = models.CharField("Grant PI Full Name", max_length=255, blank=True)
    funding_agency = models.ForeignKey(GrantFundingAgency, on_delete=models.CASCADE)
    other_funding_agency = models.CharField(max_length=255, blank=True)
    other_award_number = models.CharField(max_length=255, blank=True)
    grant_start = models.DateField("Grant Start Date")
    grant_end = models.DateField("Grant End Date")
    percent_credit = PercentField(max_length=100, validators=[MaxValueValidator(100)])
    direct_funding = MoneyField(max_length=100)
    total_amount_awarded = MoneyField(max_length=100)
    status = models.ForeignKey(GrantStatusChoice, on_delete=models.CASCADE)
    history = HistoricalRecords()

    @property
    def grant_pi(self):
        """
        Returns:
            str: the grant's PI's full name
        """

        if self.role == "PI":
            return "{} {}".format(self.project.pi.first_name, self.project.pi.last_name)
        else:
            return self.grant_pi_full_name

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Grants"

        permissions = (("can_view_all_grants", "Can view all grants"),)
