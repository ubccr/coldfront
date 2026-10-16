# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import ColdFrontModelFilterSetForm
from coldfront.forms.layout import FieldSet
from coldfront.ris.models import Funding, Publication
from coldfront.ris.providers.local import LocalProvider
from coldfront.ris.registry import get_providers_for_model

__all__ = (
    "FundingAddFilterForm",
    "FundingFilterSetForm",
    "ProviderSelectionMixin",
    "PublicationAddFilterForm",
    "PublicationFilterSetForm",
)


class PublicationFilterSetForm(ColdFrontModelFilterSetForm):
    model = Publication
    doi = forms.CharField(required=False, label=_("DOI"))
    title = forms.CharField(required=False, label=_("Title"))
    year = forms.IntegerField(required=False, label=_("Year"))
    journal = forms.CharField(required=False, label=_("Journal"))
    source = forms.CharField(required=False, label=_("Source"))

    fieldsets = (
        FieldSet(
            "q",
        ),
        FieldSet(
            "doi",
            "title",
            "year",
            "journal",
            "source",
            name=_("Publication"),
        ),
    )


class FundingFilterSetForm(ColdFrontModelFilterSetForm):
    model = Funding
    award_number = forms.CharField(required=False, label=_("Award number"))
    funding_agency = forms.CharField(required=False, label=_("Funding agency"))
    title = forms.CharField(required=False, label=_("Title"))
    status = forms.CharField(required=False, label=_("Status"))

    fieldsets = (
        FieldSet(
            "q",
        ),
        FieldSet(
            "award_number",
            "funding_agency",
            "title",
            "status",
            name=_("Funding"),
        ),
    )


class ProviderSelectionMixin(forms.Form):
    """
    Adds a multi-select ``providers`` field to an add/link filter form, letting
    the user restrict which research-work providers (including the local cache)
    are searched. Choices are built from the model's registered providers plus
    the local cache; no selection means every provider is searched.
    """

    providers = forms.MultipleChoiceField(
        required=False,
        label=_("Providers"),
        help_text=_("Search only the selected providers; all are searched by default."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        providers = [LocalProvider] + list(get_providers_for_model(self.model))
        self.fields["providers"].choices = [(cls.key, cls.display_name()) for cls in providers]

    def provider_fieldset(self):
        """Return the layout fieldset holding the provider selection field."""
        return FieldSet("providers", name=_("Providers"))


class PublicationAddFilterForm(ProviderSelectionMixin, ColdFrontModelFilterSetForm):
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

    def fieldsets(self):
        return [
            FieldSet(
                "q",
            ),
            FieldSet(
                "title",
                "doi",
                "author",
                "year",
                "journal",
                "source",
                name=_("Publication"),
            ),
            self.provider_fieldset(),
        ]


class FundingAddFilterForm(ProviderSelectionMixin, ColdFrontModelFilterSetForm):
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

    def fieldsets(self):
        return [
            FieldSet(
                "q",
            ),
            FieldSet(
                "title",
                "award_number",
                "funding_agency",
                "status",
                name=_("Funding"),
            ),
            self.provider_fieldset(),
        ]
