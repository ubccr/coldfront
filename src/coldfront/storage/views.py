# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.utils.translation import gettext_lazy as _

from coldfront.ras.models import Allocation
from coldfront.registry import register_model_view
from coldfront.storage import filtersets, forms, tables
from coldfront.storage.models import (
    StorageCluster,
    StorageQuota,
    StorageResource,
    StorageSnapshotPolicy,
)
from coldfront.utils.query import count_related
from coldfront.views import generic
from coldfront.views.mixins import GetRelatedModelsMixin
from coldfront.views.object_actions import EditObject
from coldfront.views.utils import ViewTab, get_action_url

#
# Storage Resources
#


@register_model_view(StorageResource, "list", path="", detail=False)
class StorageResourceListView(generic.ObjectListView):
    queryset = StorageResource.objects.annotate(
        quota_count=count_related(StorageQuota, "storage"),
    )
    filterset = filtersets.StorageResourceFilterSet
    filterset_form = forms.StorageResourceFilterSetForm
    table = tables.StorageResourceTable


@register_model_view(StorageResource)
class StorageResourceView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = StorageResource.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(StorageResource, "add", detail=False)
@register_model_view(StorageResource, "edit")
class StorageResourceEditView(generic.ObjectEditView):
    queryset = StorageResource.objects.all()
    form = forms.StorageResourceForm


@register_model_view(StorageResource, "delete")
class StorageResourceDeleteView(generic.ObjectDeleteView):
    queryset = StorageResource.objects.all()


@register_model_view(StorageResource, "bulk_import", path="import", detail=False)
class StorageResourceBulkImportView(generic.BulkImportView):
    queryset = StorageResource.objects.all()
    model_form = forms.StorageResourceImportForm


@register_model_view(StorageResource, "bulk_edit", path="edit", detail=False)
class StorageResourceBulkEditView(generic.BulkEditView):
    queryset = StorageResource.objects.all()
    filterset = filtersets.StorageResourceFilterSet
    table = tables.StorageResourceTable
    form = forms.StorageResourceBulkEditForm


@register_model_view(StorageResource, "bulk_delete", path="delete", detail=False)
class StorageResourceBulkDeleteView(generic.BulkDeleteView):
    queryset = StorageResource.objects.all()
    filterset = filtersets.StorageResourceFilterSet
    table = tables.StorageResourceTable


#
# Storage Clusters
#


@register_model_view(StorageCluster, "list", path="", detail=False)
class StorageClusterListView(generic.ObjectListView):
    queryset = StorageCluster.objects.annotate(
        quota_count=count_related(StorageQuota, "clusters"),
    )
    filterset = filtersets.StorageClusterFilterSet
    filterset_form = forms.StorageClusterFilterSetForm
    table = tables.StorageClusterTable


@register_model_view(StorageCluster)
class StorageClusterView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = StorageCluster.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(StorageCluster, "add", detail=False)
@register_model_view(StorageCluster, "edit")
class StorageClusterEditView(generic.ObjectEditView):
    queryset = StorageCluster.objects.all()
    form = forms.StorageClusterForm


@register_model_view(StorageCluster, "delete")
class StorageClusterDeleteView(generic.ObjectDeleteView):
    queryset = StorageCluster.objects.all()


@register_model_view(StorageCluster, "bulk_import", path="import", detail=False)
class StorageClusterBulkImportView(generic.BulkImportView):
    queryset = StorageCluster.objects.all()
    model_form = forms.StorageClusterImportForm


@register_model_view(StorageCluster, "bulk_edit", path="edit", detail=False)
class StorageClusterBulkEditView(generic.BulkEditView):
    queryset = StorageCluster.objects.all()
    filterset = filtersets.StorageClusterFilterSet
    table = tables.StorageClusterTable
    form = forms.StorageClusterBulkEditForm


@register_model_view(StorageCluster, "bulk_delete", path="delete", detail=False)
class StorageClusterBulkDeleteView(generic.BulkDeleteView):
    queryset = StorageCluster.objects.all()
    filterset = filtersets.StorageClusterFilterSet
    table = tables.StorageClusterTable


#
# Storage Quotas
#


@register_model_view(StorageQuota, "list", path="", detail=False)
class StorageQuotaListView(generic.ObjectListView):
    queryset = StorageQuota.objects.all()
    filterset = filtersets.StorageQuotaFilterSet
    filterset_form = forms.StorageQuotaFilterSetForm
    table = tables.StorageQuotaTable


@register_model_view(StorageQuota)
class StorageQuotaView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = StorageQuota.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(StorageQuota, "add", detail=False)
@register_model_view(StorageQuota, "edit")
class StorageQuotaEditView(generic.ObjectEditView):
    queryset = StorageQuota.objects.all()
    form = forms.StorageQuotaForm


@register_model_view(StorageQuota, "delete")
class StorageQuotaDeleteView(generic.ObjectDeleteView):
    queryset = StorageQuota.objects.all()


@register_model_view(StorageQuota, "bulk_import", path="import", detail=False)
class StorageQuotaBulkImportView(generic.BulkImportView):
    queryset = StorageQuota.objects.all()
    model_form = forms.StorageQuotaImportForm


@register_model_view(StorageQuota, "bulk_edit", path="edit", detail=False)
class StorageQuotaBulkEditView(generic.BulkEditView):
    queryset = StorageQuota.objects.all()
    filterset = filtersets.StorageQuotaFilterSet
    table = tables.StorageQuotaTable
    form = forms.StorageQuotaBulkEditForm


@register_model_view(StorageQuota, "bulk_delete", path="delete", detail=False)
class StorageQuotaBulkDeleteView(generic.BulkDeleteView):
    queryset = StorageQuota.objects.all()
    filterset = filtersets.StorageQuotaFilterSet
    table = tables.StorageQuotaTable


#
# Storage Snapshot Policies
#


@register_model_view(StorageSnapshotPolicy, "list", path="", detail=False)
class StorageSnapshotPolicyListView(generic.ObjectListView):
    queryset = StorageSnapshotPolicy.objects.all()
    filterset = filtersets.StorageSnapshotPolicyFilterSet
    filterset_form = forms.StorageSnapshotPolicyFilterSetForm
    table = tables.StorageSnapshotPolicyTable


@register_model_view(StorageSnapshotPolicy)
class StorageSnapshotPolicyView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = StorageSnapshotPolicy.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(StorageSnapshotPolicy, "add", detail=False)
@register_model_view(StorageSnapshotPolicy, "edit")
class StorageSnapshotPolicyEditView(generic.ObjectEditView):
    queryset = StorageSnapshotPolicy.objects.all()
    form = forms.StorageSnapshotPolicyForm


@register_model_view(StorageSnapshotPolicy, "delete")
class StorageSnapshotPolicyDeleteView(generic.ObjectDeleteView):
    queryset = StorageSnapshotPolicy.objects.all()


@register_model_view(StorageSnapshotPolicy, "bulk_import", path="import", detail=False)
class StorageSnapshotPolicyBulkImportView(generic.BulkImportView):
    queryset = StorageSnapshotPolicy.objects.all()
    model_form = forms.StorageSnapshotPolicyImportForm


@register_model_view(StorageSnapshotPolicy, "bulk_edit", path="edit", detail=False)
class StorageSnapshotPolicyBulkEditView(generic.BulkEditView):
    queryset = StorageSnapshotPolicy.objects.all()
    filterset = filtersets.StorageSnapshotPolicyFilterSet
    table = tables.StorageSnapshotPolicyTable
    form = forms.StorageSnapshotPolicyBulkEditForm


@register_model_view(StorageSnapshotPolicy, "bulk_delete", path="delete", detail=False)
class StorageSnapshotPolicyBulkDeleteView(generic.BulkDeleteView):
    queryset = StorageSnapshotPolicy.objects.all()
    filterset = filtersets.StorageSnapshotPolicyFilterSet
    table = tables.StorageSnapshotPolicyTable


@register_model_view(Allocation, "storage-quota", path="storage-quota")
class AllocationStorageQuotaView(generic.ObjectView):
    queryset = Allocation.objects.all()
    template_name = "storage/allocation/storage_quota.html"
    tab = ViewTab(
        label=_("Storage Quota"),
        visible=lambda obj: obj.storage_storagequota_extensions.exists(),
        permission="storage.view_storagequota",
        weight=100,
    )

    def get_permitted_actions(self, request, model=None, actions=None):
        # Actions target the StorageQuota, not the Allocation
        from coldfront.storage.models import StorageQuota

        return super().get_permitted_actions(request, model=StorageQuota, actions=(EditObject,))

    def get_extra_context(self, request, instance):
        storage_quota = instance.storage_storagequota_extensions.first()
        return_url = get_action_url(instance, action="storage-quota", kwargs={"pk": instance.pk})
        return {
            "storage_quota": storage_quota,
            "return_url": return_url,
        }
