# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from coldfront.models import ColdFrontModel
from coldfront.models.utils import get_currency_choices, get_default_currency

__all__ = ("Funding", "Publication")


class Publication(ColdFrontModel):
    """
    A global publication entity, identified by its DOI and linkable to any
    number of projects.

    The DOI is the canonical, cross-provider identifier for a publication
    (registered by Crossref/DataCite). ``source`` records which provider the
    record was first imported from (e.g. ``orcid``, ``crossref``, ``manual``).

    No provider-specific identifiers (e.g. an ORCID put_code) are stored: the
    DOI alone is the identity, and refresh happens via the DOI.
    """

    doi = models.CharField(
        verbose_name=_("DOI"),
        max_length=255,
        unique=True,
        help_text=_("Digital Object Identifier (e.g. 10.1000/xyz). Required."),
    )
    title = models.CharField(
        verbose_name=_("title"),
        max_length=500,
    )
    authors = models.JSONField(
        verbose_name=_("authors"),
        default=list,
        blank=True,
        help_text=_('List of {"name", "orcid"} objects.'),
    )
    year = models.IntegerField(
        verbose_name=_("year"),
        blank=True,
        null=True,
    )
    journal = models.CharField(
        verbose_name=_("journal"),
        max_length=255,
        blank=True,
    )
    source = models.CharField(
        verbose_name=_("source"),
        max_length=50,
        help_text=_("Provider registry key the record was imported from."),
    )
    external_id = models.CharField(
        verbose_name=_("external ID"),
        max_length=255,
        blank=True,
        help_text=_(
            "Provider-specific identifier (e.g. an ORCID put code or a Crossref DOI) used to re-fetch metadata."
        ),
    )
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_publications",
        blank=True,
        null=True,
        verbose_name=_("created by"),
    )
    projects = models.ManyToManyField(
        to="ras.Project",
        blank=True,
        related_name="publications",
        verbose_name=_("projects"),
    )

    class Meta:
        ordering = ("doi",)
        verbose_name = _("publication")
        verbose_name_plural = _("publications")
        permissions = (("unlink", _("Can unlink publications from projects")),)

    def __str__(self):
        return self.title or self.doi


class Funding(ColdFrontModel):
    """
    A global funding (grant) entity, identified by its award number within a
    funding agency and linkable to any number of projects.

    ``(award_number, funding_agency)`` is the canonical, cross-provider key.
    ``status`` is auto-set from the provider at import (e.g. NSF's activeAwd)
    but remains editable. ``source`` records first-provenance.
    """

    award_number = models.CharField(
        verbose_name=_("award number"),
        max_length=100,
    )
    funding_agency = models.CharField(
        verbose_name=_("funding agency"),
        max_length=100,
    )
    title = models.CharField(
        verbose_name=_("title"),
        max_length=500,
    )
    amount_awarded = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        currency_choices=get_currency_choices,
        default_currency=get_default_currency,
    )
    start_date = models.DateField(
        verbose_name=_("start date"),
        blank=True,
        null=True,
    )
    end_date = models.DateField(
        verbose_name=_("end date"),
        blank=True,
        null=True,
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=50,
        blank=True,
    )
    source = models.CharField(
        verbose_name=_("source"),
        max_length=50,
        help_text=_("Provider registry key the record was imported from."),
    )
    external_id = models.CharField(
        verbose_name=_("external ID"),
        max_length=255,
        blank=True,
        help_text=_(
            "Provider-specific identifier (e.g. an ORCID put code or an NSF award id) used to re-fetch metadata."
        ),
    )
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_funding",
        blank=True,
        null=True,
        verbose_name=_("created by"),
    )
    projects = models.ManyToManyField(
        to="ras.Project",
        blank=True,
        related_name="funding",
        verbose_name=_("projects"),
    )

    class Meta:
        ordering = ("award_number",)
        verbose_name = _("funding")
        verbose_name_plural = _("funding")
        unique_together = (("award_number", "funding_agency"),)
        permissions = (("unlink", _("Can unlink funding from projects")),)

    def __str__(self):
        return self.title or self.award_number
