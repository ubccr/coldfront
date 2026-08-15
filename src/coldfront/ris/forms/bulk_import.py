# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.forms import ColdFrontModelImportForm
from coldfront.forms.fields import CSVModelChoiceField, CSVModelMultipleChoiceField, CSVMoneyField
from coldfront.ras.models import Project
from coldfront.ris.models import Funding, Publication
from coldfront.users.models import User

__all__ = ("FundingImportForm", "PublicationImportForm")


class PublicationImportForm(ColdFrontModelImportForm):
    created_by = CSVModelChoiceField(
        label=_("Created by"),
        queryset=User.objects.all(),
        required=False,
        to_field_name="username",
        help_text=_("Username of the user who created the record."),
    )

    projects = CSVModelMultipleChoiceField(
        label=_("Projects"),
        queryset=Project.objects.all(),
        required=False,
        to_field_name="name",
        help_text=_("Project names separated by commas."),
    )

    class Meta:
        model = Publication
        fields = [
            "doi",
            "title",
            "authors",
            "year",
            "journal",
            "source",
            "external_id",
            "created_by",
            "projects",
        ]


class FundingImportForm(ColdFrontModelImportForm):
    amount_awarded = CSVMoneyField(
        label=_("Amount awarded"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "10000.00" or "10000.00 USD").'),
    )

    created_by = CSVModelChoiceField(
        label=_("Created by"),
        queryset=User.objects.all(),
        required=False,
        to_field_name="username",
        help_text=_("Username of the user who created the record."),
    )

    projects = CSVModelMultipleChoiceField(
        label=_("Projects"),
        queryset=Project.objects.all(),
        required=False,
        to_field_name="name",
        help_text=_("Project names separated by commas."),
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
            "source",
            "external_id",
            "created_by",
            "projects",
        ]
