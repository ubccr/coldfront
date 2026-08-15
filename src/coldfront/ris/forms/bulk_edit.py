# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import ColdFrontModelBulkEditForm
from coldfront.forms.fields import MoneyField
from coldfront.ras.models import Project
from coldfront.ris.models import Funding, Publication

__all__ = ("FundingBulkEditForm", "PublicationBulkEditForm")


class PublicationBulkEditForm(ColdFrontModelBulkEditForm):
    title = forms.CharField(
        max_length=500,
        required=False,
        label=_("Title"),
    )
    year = forms.IntegerField(
        required=False,
        label=_("Year"),
    )
    journal = forms.CharField(
        max_length=255,
        required=False,
        label=_("Journal"),
    )
    source = forms.CharField(
        max_length=50,
        required=False,
        label=_("Source"),
        help_text=_("Provider registry key the record was imported from (e.g. crossref, orcid, manual)."),
    )
    external_id = forms.CharField(
        max_length=255,
        required=False,
        label=_("External ID"),
        help_text=_("Provider-specific identifier used to re-fetch metadata."),
    )
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Projects"),
        help_text=_("Projects this publication is linked to."),
    )

    model = Publication
    nullable_fields = (
        "year",
        "journal",
        "external_id",
        "projects",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Publication"),
                "title",
                "year",
                "journal",
                "source",
                "external_id",
                "projects",
            ),
        ]


class FundingBulkEditForm(ColdFrontModelBulkEditForm):
    title = forms.CharField(
        max_length=500,
        required=False,
        label=_("Title"),
    )
    amount_awarded = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Amount awarded"),
        help_text=_("Enter an amount and an optional currency."),
    )
    start_date = forms.DateField(
        required=False,
        label=_("Start date"),
    )
    end_date = forms.DateField(
        required=False,
        label=_("End date"),
    )
    status = forms.CharField(
        max_length=50,
        required=False,
        label=_("Status"),
    )
    source = forms.CharField(
        max_length=50,
        required=False,
        label=_("Source"),
        help_text=_("Provider registry key the record was imported from (e.g. nsf, orcid, manual)."),
    )
    external_id = forms.CharField(
        max_length=255,
        required=False,
        label=_("External ID"),
        help_text=_("Provider-specific identifier used to re-fetch metadata."),
    )
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Projects"),
        help_text=_("Projects this funding is linked to."),
    )

    model = Funding
    nullable_fields = (
        "amount_awarded",
        "start_date",
        "end_date",
        "status",
        "external_id",
        "projects",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Funding"),
                "title",
                "amount_awarded",
                "start_date",
                "end_date",
                "status",
                "source",
                "external_id",
                "projects",
            ),
        ]
