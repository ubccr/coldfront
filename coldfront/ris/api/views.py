# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from rest_framework.routers import APIRootView

from coldfront.api.viewsets import ColdFrontModelViewSet
from coldfront.ris import filtersets
from coldfront.ris.models import Funding, Publication

from . import serializers

__all__ = ("FundingViewSet", "PublicationViewSet", "RISRootView")


class RISRootView(APIRootView):
    """
    RIS API root view
    """

    def get_view_name(self):
        return "RIS"


class PublicationViewSet(ColdFrontModelViewSet):
    queryset = Publication.objects.all()
    serializer_class = serializers.PublicationSerializer
    filterset_class = filtersets.PublicationFilterSet


class FundingViewSet(ColdFrontModelViewSet):
    queryset = Funding.objects.all()
    serializer_class = serializers.FundingSerializer
    filterset_class = filtersets.FundingFilterSet
