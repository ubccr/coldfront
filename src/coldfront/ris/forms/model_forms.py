# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import PrimaryModelForm
from coldfront.forms.fields import MoneyField
from coldfront.forms.layout import FieldSet
from coldfront.ras.models import Project
from coldfront.ris.models import Funding, Publication

__all__ = ("FundingForm", "PublicationForm")


class PublicationForm(PrimaryModelForm):
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=True,
        label=_("Projects"),
        help_text=_("Select at least one project to link this publication to."),
    )

    class Meta:
        model = Publication
        fields = ["doi", "title", "authors", "year", "journal", "projects"]

    fieldsets = (
        FieldSet(
            "doi",
            "title",
            "authors",
            "year",
            "journal",
            "projects",
            name=_("Publication"),
        ),
    )


class FundingForm(PrimaryModelForm):
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=True,
        label=_("Projects"),
        help_text=_("Select at least one project to link this funding to."),
    )
    amount_awarded = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Amount awarded"),
    )

    class Meta:
        model = Funding
        fields = [
            "award_number",
            "funding_agency",
            "title",
            "amount_awarded",
            "start_date",
            "end_date",
            "status",
            "projects",
        ]

    fieldsets = (
        FieldSet(
            "award_number",
            "funding_agency",
            "title",
            "amount_awarded",
            "start_date",
            "end_date",
            "status",
            "projects",
            name=_("Funding"),
        ),
    )
