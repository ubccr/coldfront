# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.db.models import Count

from coldfront.ras import filtersets, forms, tables
from coldfront.ras.models import Resource, ResourceType
from coldfront.registry import register_model_view
from coldfront.utils.query import count_related
from coldfront.views import generic
from coldfront.views.mixins import GetRelatedModelsMixin

#
# Resource types
#


@register_model_view(ResourceType, "list", path="", detail=False)
class ResourceTypeListView(generic.ObjectListView):
    queryset = ResourceType.objects.annotate(
        resource_count=count_related(Resource, "resource_type"),
    )
    filterset = filtersets.ResourceTypeFilterSet
    filterset_form = forms.ResourceTypeFilterSetForm
    table = tables.ResourceTypeTable


@register_model_view(ResourceType)
class ResourceTypeView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = ResourceType.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(ResourceType, "add", detail=False)
@register_model_view(ResourceType, "edit")
class ResourceTypeEditView(generic.ObjectEditView):
    queryset = ResourceType.objects.all()
    form = forms.ResourceTypeForm


@register_model_view(ResourceType, "delete")
class ResourceTypeDeleteView(generic.ObjectDeleteView):
    queryset = ResourceType.objects.all()


@register_model_view(ResourceType, "bulk_import", path="import", detail=False)
class ResourceTypeBulkImportView(generic.BulkImportView):
    queryset = ResourceType.objects.all()
    model_form = forms.ResourceTypeImportForm


@register_model_view(ResourceType, "bulk_edit", path="edit", detail=False)
class ResourceTypeBulkEditView(generic.BulkEditView):
    queryset = ResourceType.objects.all()
    filterset = filtersets.ResourceTypeFilterSet
    table = tables.ResourceTypeTable
    form = forms.ResourceTypeBulkEditForm


@register_model_view(ResourceType, "bulk_delete", path="delete", detail=False)
class ResourceTypeBulkDeleteView(generic.BulkDeleteView):
    queryset = ResourceType.objects.all()
    filterset = filtersets.ResourceTypeFilterSet
    table = tables.ResourceTypeTable


#
# Resources
#


@register_model_view(Resource, "list", path="", detail=False)
class ResourceListView(generic.ObjectListView):
    queryset = Resource.objects.annotate(
        allocation_count=Count("allocations"),
    )
    filterset = filtersets.ResourceFilterSet
    filterset_form = forms.ResourceFilterSetForm
    table = tables.ResourceTable


@register_model_view(Resource)
class ResourceView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Resource.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(Resource, "add", detail=False)
@register_model_view(Resource, "edit")
class ResourceEditView(generic.ObjectEditView):
    queryset = Resource.objects.all()
    form = forms.ResourceForm


@register_model_view(Resource, "delete")
class ResourceDeleteView(generic.ObjectDeleteView):
    queryset = Resource.objects.all()


@register_model_view(Resource, "bulk_import", path="import", detail=False)
class ResourceBulkImportView(generic.BulkImportView):
    queryset = Resource.objects.all()
    model_form = forms.ResourceImportForm


@register_model_view(Resource, "bulk_edit", path="edit", detail=False)
class ResourceBulkEditView(generic.BulkEditView):
    queryset = Resource.objects.all()
    filterset = filtersets.ResourceFilterSet
    table = tables.ResourceTable
    form = forms.ResourceBulkEditForm


@register_model_view(Resource, "bulk_delete", path="delete", detail=False)
class ResourceBulkDeleteView(generic.BulkDeleteView):
    queryset = Resource.objects.all()
    filterset = filtersets.ResourceFilterSet
    table = tables.ResourceTable
