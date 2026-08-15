# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import ColdFrontModelForm
from coldfront.forms.fields import MoneyField
from coldfront.ras.models import Project
from coldfront.ris.models import Funding, Publication

__all__ = ("FundingForm", "PublicationForm")


class PublicationForm(ColdFrontModelForm):
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=True,
        label=_("Projects"),
        help_text=_("Select at least one project to link this publication to."),
    )

    class Meta:
        model = Publication
        fields = ["doi", "title", "authors", "year", "journal", "projects"]

    fieldsets = (Fieldset(_("Publication"), "doi", "title", "authors", "year", "journal", "projects"),)


class FundingForm(ColdFrontModelForm):
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
        Fieldset(
            _("Funding"),
            "award_number",
            "funding_agency",
            "title",
            "amount_awarded",
            "start_date",
            "end_date",
            "status",
            "projects",
        ),
    )
