# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.routers import APIRootView

from coldfront.api.metadata import ContentTypeMetadata
from coldfront.api.viewsets import BaseViewSet, ColdFrontModelViewSet
from coldfront.core import filtersets
from coldfront.core.models import CustomField, CustomFieldChoiceSet, SavedFilter, TableConfig, Tag, TaggedItem

from . import serializers


class CoreRootView(APIRootView):
    """
    Core API root view
    """

    def get_view_name(self):
        return "Core"


#
# Custom fields
#


class SavedFilterViewSet(ColdFrontModelViewSet):
    queryset = SavedFilter.objects.all()
    serializer_class = serializers.SavedFilterSerializer
    filterset_class = filtersets.SavedFilterFilterSet


class CustomFieldViewSet(ColdFrontModelViewSet):
    metadata_class = ContentTypeMetadata
    queryset = CustomField.objects.select_related("choice_set")
    serializer_class = serializers.CustomFieldSerializer
    filterset_class = filtersets.CustomFieldFilterSet


class CustomFieldChoiceSetViewSet(ColdFrontModelViewSet):
    queryset = CustomFieldChoiceSet.objects.all()
    serializer_class = serializers.CustomFieldChoiceSetSerializer
    filterset_class = filtersets.CustomFieldChoiceSetFilterSet

    @action(detail=True)
    def choices(self, request, pk):
        """
        Provides an endpoint to iterate through each choice in a set.
        """
        choiceset = get_object_or_404(self.queryset, pk=pk)
        choices = choiceset.choices

        # Enable filtering
        if q := request.GET.get("q"):
            q = q.lower()
            choices = [c for c in choices if q in c[0].lower() or q in c[1].lower()]

        # Paginate data
        if page := self.paginate_queryset(choices):
            data = [{"id": c[0], "display": c[1]} for c in page]
        else:
            data = []

        return self.get_paginated_response(data)


#
# Tags
#


class TagViewSet(ColdFrontModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer
    filterset_class = filtersets.TagFilterSet


class TableConfigViewSet(ColdFrontModelViewSet):
    queryset = TableConfig.objects.all()
    serializer_class = serializers.TableConfigSerializer
    filterset_class = filtersets.TableConfigFilterSet


class TaggedItemViewSet(RetrieveModelMixin, ListModelMixin, BaseViewSet):
    queryset = TaggedItem.objects.prefetch_related("content_type", "content_object", "tag").order_by(
        "tag__weight", "tag__name"
    )
    serializer_class = serializers.TaggedItemSerializer
    filterset_class = filtersets.TaggedItemFilterSet
