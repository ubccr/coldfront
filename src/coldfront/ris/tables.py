# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.ris.models import Funding, Publication
from coldfront.tables import ColdFrontTable, columns

__all__ = (
    "FundingAddTable",
    "FundingTable",
    "PublicationAddTable",
    "PublicationTable",
)


class PublicationTable(ColdFrontTable):
    doi = tables.Column(
        verbose_name=_("DOI"),
        linkify=True,
    )
    title = tables.Column(
        verbose_name=_("Title"),
    )
    year = tables.Column(
        verbose_name=_("Year"),
    )
    journal = tables.Column(
        verbose_name=_("Journal"),
    )
    source = tables.Column(
        verbose_name=_("Source"),
    )
    projects = tables.ManyToManyColumn(
        verbose_name=_("Projects"),
        linkify_item=True,
    )
    tags = columns.TagColumn(
        url_name="ris:publication_list",
    )

    class Meta(ColdFrontTable.Meta):
        model = Publication
        fields = (
            "pk",
            "id",
            "doi",
            "title",
            "year",
            "journal",
            "source",
            "projects",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "doi", "title", "year", "journal", "source", "projects")


class PublicationAddTable(ColdFrontTable):
    """
    Candidate publication rows for the project link view. Rows are dicts
    (``key/is_local/title/doi/year/journal/source``) merged from local records
    and provider results; the ``pk`` checkbox carries the row key so the
    POST handler can link local/external records unchanged.
    """

    pk = columns.ToggleColumn(
        visible=True,
        accessor="key",
    )
    title = tables.Column(verbose_name=_("Title"))
    doi = tables.Column(verbose_name=_("DOI"))
    year = tables.Column(verbose_name=_("Year"))
    journal = tables.Column(verbose_name=_("Journal"))
    source = columns.TemplateColumn(
        template_code="""
            {{ record.source }}
            {% if record.is_local %}<span class="badge bg-secondary">{{ local_label }}</span>{% endif %}
        """,
        extra_context={"local_label": _("local")},
        verbose_name=_("Source"),
    )

    exempt_columns = ("pk",)

    class Meta(ColdFrontTable.Meta):
        model = Publication
        fields = ("pk", "title", "doi", "year", "journal", "source")
        default_columns = ("pk", "title", "doi", "year", "journal", "source")
        empty_text = _("No results found. Please use the filter tab to search for publications")

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._project = project

    @property
    def htmx_url(self):
        return reverse("ras:project_add_publication", kwargs={"pk": self._project.pk})


class FundingAddTable(ColdFrontTable):
    """
    Candidate funding rows for the project link view. Rows are dicts
    (``key/is_local/title/award_number/funding_agency/status/source``) merged
    from local records and provider results.
    """

    pk = columns.ToggleColumn(
        visible=True,
        accessor="key",
    )
    title = tables.Column(verbose_name=_("Title"))
    award_number = tables.Column(verbose_name=_("Award number"))
    funding_agency = tables.Column(verbose_name=_("Funding agency"))
    status = tables.Column(verbose_name=_("Status"))
    source = columns.TemplateColumn(
        template_code="""
            {{ record.source }}
            {% if record.is_local %}<span class="badge bg-secondary">{{ local_label }}</span>{% endif %}
        """,
        extra_context={"local_label": _("local")},
        verbose_name=_("Source"),
    )

    exempt_columns = ("pk",)

    class Meta(ColdFrontTable.Meta):
        model = Funding
        fields = ("pk", "title", "award_number", "funding_agency", "status", "source")
        default_columns = ("pk", "title", "award_number", "funding_agency", "status", "source")
        empty_text = _("No results found. Please use the filter tab to search for funding")

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._project = project

    @property
    def htmx_url(self):
        return reverse("ras:project_add_funding", kwargs={"pk": self._project.pk})


class FundingTable(ColdFrontTable):
    award_number = tables.Column(
        verbose_name=_("Award number"),
    )
    funding_agency = tables.Column(
        verbose_name=_("Funding agency"),
    )
    title = tables.Column(
        verbose_name=_("Title"),
        linkify=True,
    )
    status = tables.Column(
        verbose_name=_("Status"),
    )
    amount_awarded = columns.TemplateColumn(
        template_code="""
            {% load djmoney %}
            {% if record.amount_awarded %}{% money_localize record.amount_awarded %} {% else %}—{% endif %}
        """,
        verbose_name=_("Amount"),
    )
    start_date = columns.DateColumn(
        verbose_name=_("Start Date"),
    )
    end_date = columns.DateColumn(
        verbose_name=_("End Date"),
    )
    source = tables.Column(
        verbose_name=_("Source"),
    )
    projects = tables.ManyToManyColumn(
        verbose_name=_("Projects"),
        linkify_item=True,
    )
    tags = columns.TagColumn(
        url_name="ris:funding_list",
    )

    class Meta(ColdFrontTable.Meta):
        model = Funding
        fields = (
            "pk",
            "id",
            "award_number",
            "funding_agency",
            "title",
            "status",
            "amount_awarded",
            "start_date",
            "end_date",
            "source",
            "projects",
            "tags",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "award_number", "funding_agency", "title", "status", "amount_awarded", "source")
