# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


import logging
from dataclasses import asdict

import humanize
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from coldfront.ras.models import Allocation
from coldfront.registry import register_model_view
from coldfront.storage import filtersets, forms, tables
from coldfront.storage.backends.base import ErrNotFound
from coldfront.storage.backends.registry import get_backend, get_backend_choices
from coldfront.storage.models import (
    StorageCluster,
    StorageQuota,
    StorageResource,
    StorageSnapshotPolicy,
)
from coldfront.storage.object_actions import SyncQuotaAction
from coldfront.storage.sync import sync_storage_quota
from coldfront.utils.data import shallow_compare_dict
from coldfront.utils.query import count_related
from coldfront.utils.serialization import serialize_object
from coldfront.views import ViewTab, generic, get_action_url
from coldfront.views.mixins import GetRelatedModelsMixin
from coldfront.views.object_actions import EditObject

#
# Storage Resources
#

logger = logging.getLogger(__name__)


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
# Storage Quota backend status
#


@register_model_view(StorageQuota, "status")
class StorageQuotaStatusView(generic.ObjectView):
    """Show live backend status for every cluster a quota belongs to."""

    queryset = StorageQuota.objects.all()
    actions = (SyncQuotaAction,)
    template_name = "storage/storagequota/status.html"
    tab = ViewTab(
        label=_("Backend Status"),
        visible=lambda quota: len(get_backend_choices()) > 1,
        permission="storage.view_storagequota",
        weight=100,
    )

    def get_extra_context(self, request, instance):
        clusters = instance.get_clusters()
        cluster_names = [c.name for c in clusters]
        return {
            "diffs": self._compute_diffs(clusters, instance),
            "cluster_names": cluster_names,
            "fetched_at": timezone.now(),
        }

    def _compute_diffs(self, clusters, instance):
        diffs = []
        for cluster in clusters:
            backend_path = cluster.backend_path
            if not backend_path:
                continue

            backend = get_backend(backend_path, cluster_name=cluster.name)
            diff = {"name": cluster.name, "backend": backend.display_name()}
            quota = None
            path = None

            try:
                quota = backend.get_quota(instance.path)
                diff["quota_exists"] = True
            except ErrNotFound:
                diff["quota_exists"] = False
            except Exception as exc:
                logger.error(
                    f"Failed to fetch quota {instance} from cluster {cluster.name} using backend {backend.display_name()}: {exc}",
                    exc_info=True,
                )
                diff["error"] = f"Failed to fetch quota from {cluster.name}"

            try:
                path = backend.stat_path(instance.path)
                diff["path_exists"] = True
            except ErrNotFound:
                diff["path_exists"] = False
            except Exception as exc:
                logger.error(
                    f"Failed to stat path for quota {instance} from cluster {cluster.name} using backend {backend.display_name()}: {exc}",
                    exc_info=True,
                )
                diff["error"] = f"Failed to stat path from {cluster.name}"

            instance_data = serialize_object(
                instance,
                include=["path_mode", "hard_limit_bytes", "hard_limit_files", "soft_limit_bytes", "soft_limit_files"],
            )
            instance_data["owning_user"] = instance.owning_user.username
            instance_data["owning_group"] = instance.owning_group.name
            quota_data = {}
            if quota:
                quota_data.update(asdict(quota))
            if path:
                quota_data.update(asdict(path))

            diff_added = shallow_compare_dict(
                quota_data,
                instance_data,
            )
            diff_removed = {x: quota_data.get(x) for x in diff_added}
            for f in [
                "hard_limit_bytes",
                "soft_limit_bytes",
            ]:
                if f in diff_added:
                    diff_added[f] = humanize.naturalsize(diff_added[f]) if diff_added[f] else None
                    diff_removed[f] = humanize.naturalsize(diff_removed[f]) if diff_removed[f] else None

            diff["diff_added"] = diff_added
            diff["diff_removed"] = diff_removed
            diff["quota"] = quota
            diff["path"] = path

            diffs.append(diff)
        return diffs


@register_model_view(StorageQuota, "sync")
class StorageQuotaSyncView(generic.ObjectConfirmationView):
    """Sync storage quota to backend cluster."""

    queryset = StorageQuota.objects.all()
    action = "sync"
    action_label = "Sync Storage Quota"

    def get_return_url(self, request, obj):
        return get_action_url(obj, action="status", kwargs={"pk": obj.pk})

    def perform_action(self, request, obj, form):
        """Run the per-quota sync, then refresh the status page."""
        if not request.user.has_perm("storage.change_storagequota"):
            raise PermissionDenied

        reports = sync_storage_quota(obj)
        for report in reports:
            if report.errors:
                messages.error(request, f"{report.cluster}: " + "; ".join(report.errors))
            else:
                messages.success(request, f"{report.cluster}: synced")


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
