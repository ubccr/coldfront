# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.registry import register_model_view
from coldfront.views import generic
from coldfront.views.mixins import GetRelatedModelsMixin

from . import filtersets, forms, tables
from .models import Tenant, TenantGroup

#
# Tenant groups
#


@register_model_view(TenantGroup, "list", path="", detail=False)
class TenantGroupListView(generic.ObjectListView):
    queryset = TenantGroup.objects.add_related_count(
        TenantGroup.objects.all(), Tenant, "group", "tenant_count", cumulative=True
    )
    filterset = filtersets.TenantGroupFilterSet
    filterset_form = forms.TenantGroupFilterSetForm
    table = tables.TenantGroupTable


@register_model_view(TenantGroup)
class TenantGroupView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = TenantGroup.objects.all()

    def get_extra_context(self, request, instance):
        groups = instance.get_descendants(include_self=True)

        return {
            "related_models": self.get_related_models(request, groups),
        }


@register_model_view(TenantGroup, "add", detail=False)
@register_model_view(TenantGroup, "edit")
class TenantGroupEditView(generic.ObjectEditView):
    queryset = TenantGroup.objects.all()
    form = forms.TenantGroupForm


@register_model_view(TenantGroup, "delete")
class TenantGroupDeleteView(generic.ObjectDeleteView):
    queryset = TenantGroup.objects.all()


@register_model_view(TenantGroup, "bulk_import", path="import", detail=False)
class TenantGroupBulkImportView(generic.BulkImportView):
    queryset = TenantGroup.objects.all()
    model_form = forms.TenantGroupImportForm


@register_model_view(TenantGroup, "bulk_edit", path="edit", detail=False)
class TenantGroupBulkEditView(generic.BulkEditView):
    queryset = TenantGroup.objects.all()
    filterset = filtersets.TenantGroupFilterSet
    table = tables.TenantGroupTable
    form = forms.TenantGroupBulkEditForm


@register_model_view(TenantGroup, "bulk_delete", path="delete", detail=False)
class TenantGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = TenantGroup.objects.add_related_count(
        TenantGroup.objects.all(),
        Tenant,
        "group",
        "tenant_count",
        cumulative=True,
    )
    filterset = filtersets.TenantGroupFilterSet
    table = tables.TenantGroupTable


#
#  Tenants
#


@register_model_view(Tenant, "list", path="", detail=False)
class TenantListView(generic.ObjectListView):
    queryset = Tenant.objects.all()
    filterset = filtersets.TenantFilterSet
    filterset_form = forms.TenantFilterSetForm
    table = tables.TenantTable


@register_model_view(Tenant)
class TenantView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Tenant.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(Tenant, "add", detail=False)
@register_model_view(Tenant, "edit")
class TenantEditView(generic.ObjectEditView):
    queryset = Tenant.objects.all()
    form = forms.TenantForm


@register_model_view(Tenant, "delete")
class TenantDeleteView(generic.ObjectDeleteView):
    queryset = Tenant.objects.all()


@register_model_view(Tenant, "bulk_import", path="import", detail=False)
class TenantBulkImportView(generic.BulkImportView):
    queryset = Tenant.objects.all()
    model_form = forms.TenantImportForm


@register_model_view(Tenant, "bulk_edit", path="edit", detail=False)
class TenantBulkEditView(generic.BulkEditView):
    queryset = Tenant.objects.all()
    filterset = filtersets.TenantFilterSet
    table = tables.TenantTable
    form = forms.TenantBulkEditForm


@register_model_view(Tenant, "bulk_delete", path="delete", detail=False)
class TenantBulkDeleteView(generic.BulkDeleteView):
    queryset = Tenant.objects.all()
    filterset = filtersets.TenantFilterSet
    table = tables.TenantTable
