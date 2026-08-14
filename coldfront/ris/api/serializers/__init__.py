# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework import serializers

from coldfront.api.serializers import PrimaryModelSerializer
from coldfront.api.serializers.fields import MoneyField
from coldfront.ras.api.serializers import ProjectSerializer
from coldfront.ris.models import Funding, Publication

__all__ = ("FundingSerializer", "PublicationSerializer")


class PublicationSerializer(PrimaryModelSerializer):
    # Projects are linked via the per-project link views, not the CRUD API.
    projects = ProjectSerializer(nested=True, many=True, required=False, read_only=True)

    class Meta:
        model = Publication
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "doi",
            "title",
            "authors",
            "year",
            "journal",
            "source",
            "external_id",
            "projects",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "doi", "title", "year")


class FundingSerializer(PrimaryModelSerializer):
    # Projects are linked via the per-project link views, not the CRUD API.
    projects = ProjectSerializer(nested=True, many=True, required=False, read_only=True)

    amount_awarded = MoneyField(required=False)
    amount_awarded_currency = serializers.CharField(read_only=True)

    class Meta:
        model = Funding
        fields = [
            "id",
            "url",
            "display_url",
            "display",
            "award_number",
            "funding_agency",
            "title",
            "amount_awarded",
            "amount_awarded_currency",
            "start_date",
            "end_date",
            "status",
            "source",
            "external_id",
            "projects",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
        ]
        brief_fields = ("id", "url", "display", "award_number", "funding_agency", "title")
