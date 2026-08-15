# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset, Layout
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import ColdFrontModelFilterSetForm
from coldfront.ris.models import Funding, Publication

__all__ = ("FundingFilterSetForm", "PublicationFilterSetForm")


class PublicationFilterSetForm(ColdFrontModelFilterSetForm):
    model = Publication
    doi = forms.CharField(required=False, label=_("DOI"))
    title = forms.CharField(required=False, label=_("Title"))
    year = forms.IntegerField(required=False, label=_("Year"))
    journal = forms.CharField(required=False, label=_("Journal"))
    source = forms.CharField(required=False, label=_("Source"))

    fieldsets = (Fieldset(_("Publication"), "doi", "title", "year", "journal", "source"),)


class FundingFilterSetForm(ColdFrontModelFilterSetForm):
    model = Funding
    award_number = forms.CharField(required=False, label=_("Award number"))
    funding_agency = forms.CharField(required=False, label=_("Funding agency"))
    title = forms.CharField(required=False, label=_("Title"))
    status = forms.CharField(required=False, label=_("Status"))

    fieldsets = (Fieldset(_("Funding"), "award_number", "funding_agency", "title", "status"),)


class PublicationAddFilterForm(ColdFrontModelFilterSetForm):
    """
    Filter/search form for the publication link view. Fields mirror the fields
    the Crossref/ORCID APIs can search (title, DOI, author, journal, year).
    The saved-filter dropdown (``filter_id``) is intentionally omitted from the
    layout for now.
    """

    model = Publication
    doi = forms.CharField(required=False, label=_("DOI"))
    title = forms.CharField(required=False, label=_("Title"))
    author = forms.CharField(required=False, label=_("Author"))
    year = forms.IntegerField(required=False, label=_("Year"))
    journal = forms.CharField(required=False, label=_("Journal"))
    source = forms.CharField(required=False, label=_("Source"))

    def get_layout(self):
        return Layout(
            Fieldset(_("Search"), "q"),
            Fieldset(_("Publication"), "title", "doi", "author", "year", "journal", "source"),
        )


class FundingAddFilterForm(ColdFrontModelFilterSetForm):
    """
    Filter/search form for the funding link view. Fields mirror the fields the
    NSF/ORCID APIs can search (title, award number, agency, status). The
    saved-filter dropdown (``filter_id``) is intentionally omitted from the
    layout for now.
    """

    model = Funding
    title = forms.CharField(required=False, label=_("Title"))
    award_number = forms.CharField(required=False, label=_("Award number"))
    funding_agency = forms.CharField(required=False, label=_("Funding agency"))
    status = forms.CharField(required=False, label=_("Status"))

    def get_layout(self):
        return Layout(
            Fieldset(_("Search"), "q"),
            Fieldset(_("Funding"), "title", "award_number", "funding_agency", "status"),
        )
