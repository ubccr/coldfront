# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from coldfront.ris.models import Funding, Publication
from coldfront.views.filtersets import ColdFrontModelFilterSet

__all__ = ("FundingFilterSet", "PublicationFilterSet")


class PublicationFilterSet(ColdFrontModelFilterSet):
    # Substring match over the JSON authors list (e.g. [{name, orcid}]).
    author = django_filters.CharFilter(
        field_name="authors",
        lookup_expr="icontains",
        label=_("Author"),
    )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(doi__icontains=value) | Q(title__icontains=value) | Q(journal__icontains=value))

    class Meta:
        model = Publication
        fields = ("doi", "title", "year", "journal", "source")


class FundingFilterSet(ColdFrontModelFilterSet):
    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(award_number__icontains=value) | Q(funding_agency__icontains=value) | Q(title__icontains=value)
        )

    class Meta:
        model = Funding
        fields = ("award_number", "funding_agency", "title", "status")
