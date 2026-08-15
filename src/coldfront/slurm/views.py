# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from coldfront.ras.models import Allocation
from coldfront.registry import register_model_view
from coldfront.slurm import filtersets, forms, tables
from coldfront.slurm.dump import generate_cluster_dump
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.utils.query import count_related
from coldfront.views import generic
from coldfront.views.mixins import GetRelatedModelsMixin
from coldfront.views.object_actions import EditObject
from coldfront.views.utils import ViewTab, get_action_url

#
# Slurm QOS
#


@register_model_view(SlurmQOS, "list", path="", detail=False)
class SlurmQOSListView(generic.ObjectListView):
    queryset = SlurmQOS.objects.all()
    filterset = filtersets.SlurmQOSFilterSet
    filterset_form = forms.SlurmQOSFilterSetForm
    table = tables.SlurmQOSTable


@register_model_view(SlurmQOS)
class SlurmQOSView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = SlurmQOS.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(SlurmQOS, "add", detail=False)
@register_model_view(SlurmQOS, "edit")
class SlurmQOSEditView(generic.ObjectEditView):
    queryset = SlurmQOS.objects.all()
    form = forms.SlurmQOSForm


@register_model_view(SlurmQOS, "delete")
class SlurmQOSDeleteView(generic.ObjectDeleteView):
    queryset = SlurmQOS.objects.all()


@register_model_view(SlurmQOS, "bulk_import", path="import", detail=False)
class SlurmQOSBulkImportView(generic.BulkImportView):
    queryset = SlurmQOS.objects.all()
    model_form = forms.SlurmQOSImportForm


@register_model_view(SlurmQOS, "bulk_edit", path="edit", detail=False)
class SlurmQOSBulkEditView(generic.BulkEditView):
    queryset = SlurmQOS.objects.all()
    filterset = filtersets.SlurmQOSFilterSet
    table = tables.SlurmQOSTable
    form = forms.SlurmQOSBulkEditForm


@register_model_view(SlurmQOS, "bulk_delete", path="delete", detail=False)
class SlurmQOSBulkDeleteView(generic.BulkDeleteView):
    queryset = SlurmQOS.objects.all()
    filterset = filtersets.SlurmQOSFilterSet
    table = tables.SlurmQOSTable


#
# Slurm clusters
#


@register_model_view(SlurmCluster, "list", path="", detail=False)
class SlurmClusterListView(generic.ObjectListView):
    queryset = SlurmCluster.objects.annotate(
        partition_count=count_related(SlurmPartition, "cluster"),
    )
    filterset = filtersets.SlurmClusterFilterSet
    filterset_form = forms.SlurmClusterFilterSetForm
    table = tables.SlurmClusterTable


@register_model_view(SlurmCluster)
class SlurmClusterView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = SlurmCluster.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(SlurmCluster, "add", detail=False)
@register_model_view(SlurmCluster, "edit")
class SlurmClusterEditView(generic.ObjectEditView):
    queryset = SlurmCluster.objects.all()
    form = forms.SlurmClusterForm


@register_model_view(SlurmCluster, "delete")
class SlurmClusterDeleteView(generic.ObjectDeleteView):
    queryset = SlurmCluster.objects.all()


@register_model_view(SlurmCluster, "bulk_import", path="import", detail=False)
class SlurmClusterBulkImportView(generic.BulkImportView):
    queryset = SlurmCluster.objects.all()
    model_form = forms.SlurmClusterImportForm


@register_model_view(SlurmCluster, "bulk_edit", path="edit", detail=False)
class SlurmClusterBulkEditView(generic.BulkEditView):
    queryset = SlurmCluster.objects.all()
    filterset = filtersets.SlurmClusterFilterSet
    table = tables.SlurmClusterTable
    form = forms.SlurmClusterBulkEditForm


@register_model_view(SlurmCluster, "bulk_delete", path="delete", detail=False)
class SlurmClusterBulkDeleteView(generic.BulkDeleteView):
    queryset = SlurmCluster.objects.all()
    filterset = filtersets.SlurmClusterFilterSet
    table = tables.SlurmClusterTable


@register_model_view(SlurmCluster, "dump", path="dump")
class SlurmClusterDumpView(generic.ObjectView):
    queryset = SlurmCluster.objects.all()
    template_name = "slurm/slurmcluster/dump.html"
    actions = ()
    tab = ViewTab(
        label=_("Export Dump"),
        #        badge=lambda obj: _count_active_assocs(obj),
        permission="slurm.view_slurmcluster",
        weight=500,
    )

    def get_extra_context(self, request, instance):
        dump_content = generate_cluster_dump(instance)
        return {
            "dump_content": dump_content,
        }

    def get(self, request, *args, **kwargs):
        # If the Export button was clicked (download=True), return a file
        if request.GET.get("download"):
            instance = self.get_object(**kwargs)
            dump_content = generate_cluster_dump(instance)
            response = HttpResponse(dump_content, content_type="text/plain")
            filename = f"slurm_dump_{instance.name}.txt"
            response["Content-Disposition"] = f"attachment; filename={filename}"
            return response
        return super().get(request, *args, **kwargs)


def _count_active_assocs(cluster):
    """Count active associations for a cluster (for the tab badge)."""
    from coldfront.slurm.dump import _get_active_associations

    return len(_get_active_associations(cluster))


#
# Slurm partitions
#


@register_model_view(SlurmPartition, "list", path="", detail=False)
class SlurmPartitionListView(generic.ObjectListView):
    queryset = SlurmPartition.objects.all()
    filterset = filtersets.SlurmPartitionFilterSet
    filterset_form = forms.SlurmPartitionFilterSetForm
    table = tables.SlurmPartitionTable


@register_model_view(SlurmPartition)
class SlurmPartitionView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = SlurmPartition.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(SlurmPartition, "add", detail=False)
@register_model_view(SlurmPartition, "edit")
class SlurmPartitionEditView(generic.ObjectEditView):
    queryset = SlurmPartition.objects.all()
    form = forms.SlurmPartitionForm


@register_model_view(SlurmPartition, "delete")
class SlurmPartitionDeleteView(generic.ObjectDeleteView):
    queryset = SlurmPartition.objects.all()


@register_model_view(SlurmPartition, "bulk_import", path="import", detail=False)
class SlurmPartitionBulkImportView(generic.BulkImportView):
    queryset = SlurmPartition.objects.all()
    model_form = forms.SlurmPartitionImportForm


@register_model_view(SlurmPartition, "bulk_edit", path="edit", detail=False)
class SlurmPartitionBulkEditView(generic.BulkEditView):
    queryset = SlurmPartition.objects.all()
    filterset = filtersets.SlurmPartitionFilterSet
    table = tables.SlurmPartitionTable
    form = forms.SlurmPartitionBulkEditForm


@register_model_view(SlurmPartition, "bulk_delete", path="delete", detail=False)
class SlurmPartitionBulkDeleteView(generic.BulkDeleteView):
    queryset = SlurmPartition.objects.all()
    filterset = filtersets.SlurmPartitionFilterSet
    table = tables.SlurmPartitionTable


#
# Slurm accounts
#


@register_model_view(SlurmAccount, "list", path="", detail=False)
class SlurmAccountListView(generic.ObjectListView):
    queryset = SlurmAccount.objects.all()
    filterset = filtersets.SlurmAccountFilterSet
    filterset_form = forms.SlurmAccountFilterSetForm
    table = tables.SlurmAccountTable


@register_model_view(SlurmAccount)
class SlurmAccountView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = SlurmAccount.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(SlurmAccount, "add", detail=False)
@register_model_view(SlurmAccount, "edit")
class SlurmAccountEditView(generic.ObjectEditView):
    queryset = SlurmAccount.objects.all()
    form = forms.SlurmAccountForm


@register_model_view(SlurmAccount, "delete")
class SlurmAccountDeleteView(generic.ObjectDeleteView):
    queryset = SlurmAccount.objects.all()


@register_model_view(SlurmAccount, "bulk_import", path="import", detail=False)
class SlurmAccountBulkImportView(generic.BulkImportView):
    queryset = SlurmAccount.objects.all()
    model_form = forms.SlurmAccountImportForm


@register_model_view(SlurmAccount, "bulk_edit", path="edit", detail=False)
class SlurmAccountBulkEditView(generic.BulkEditView):
    queryset = SlurmAccount.objects.all()
    filterset = filtersets.SlurmAccountFilterSet
    table = tables.SlurmAccountTable
    form = forms.SlurmAccountBulkEditForm


@register_model_view(SlurmAccount, "bulk_delete", path="delete", detail=False)
class SlurmAccountBulkDeleteView(generic.BulkDeleteView):
    queryset = SlurmAccount.objects.all()
    filterset = filtersets.SlurmAccountFilterSet
    table = tables.SlurmAccountTable


#
# Slurm associations
#


@register_model_view(SlurmAssociation, "list", path="", detail=False)
class SlurmAssociationListView(generic.ObjectListView):
    queryset = SlurmAssociation.objects.all()
    filterset = filtersets.SlurmAssociationFilterSet
    filterset_form = forms.SlurmAssociationFilterSetForm
    table = tables.SlurmAssociationTable


@register_model_view(SlurmAssociation)
class SlurmAssociationView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = SlurmAssociation.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(SlurmAssociation, "add", detail=False)
@register_model_view(SlurmAssociation, "edit")
class SlurmAssociationEditView(generic.ObjectEditView):
    queryset = SlurmAssociation.objects.all()
    form = forms.SlurmAssociationForm


@register_model_view(SlurmAssociation, "delete")
class SlurmAssociationDeleteView(generic.ObjectDeleteView):
    queryset = SlurmAssociation.objects.all()


@register_model_view(SlurmAssociation, "bulk_import", path="import", detail=False)
class SlurmAssociationBulkImportView(generic.BulkImportView):
    queryset = SlurmAssociation.objects.all()
    model_form = forms.SlurmAssociationImportForm


@register_model_view(SlurmAssociation, "bulk_edit", path="edit", detail=False)
class SlurmAssociationBulkEditView(generic.BulkEditView):
    queryset = SlurmAssociation.objects.all()
    filterset = filtersets.SlurmAssociationFilterSet
    table = tables.SlurmAssociationTable
    form = forms.SlurmAssociationBulkEditForm


@register_model_view(SlurmAssociation, "bulk_delete", path="delete", detail=False)
class SlurmAssociationBulkDeleteView(generic.BulkDeleteView):
    queryset = SlurmAssociation.objects.all()
    filterset = filtersets.SlurmAssociationFilterSet
    table = tables.SlurmAssociationTable


#
# Slurm users
#


@register_model_view(SlurmUser, "list", path="", detail=False)
class SlurmUserListView(generic.ObjectListView):
    queryset = SlurmUser.objects.all()
    filterset = filtersets.SlurmUserFilterSet
    filterset_form = forms.SlurmUserFilterSetForm
    table = tables.SlurmUserTable


@register_model_view(SlurmUser)
class SlurmUserView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = SlurmUser.objects.all()

    def get_extra_context(self, request, instance):
        return {
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(SlurmUser, "add", detail=False)
@register_model_view(SlurmUser, "edit")
class SlurmUserEditView(generic.ObjectEditView):
    queryset = SlurmUser.objects.all()
    form = forms.SlurmUserForm


@register_model_view(SlurmUser, "delete")
class SlurmUserDeleteView(generic.ObjectDeleteView):
    queryset = SlurmUser.objects.all()


@register_model_view(SlurmUser, "bulk_import", path="import", detail=False)
class SlurmUserBulkImportView(generic.BulkImportView):
    queryset = SlurmUser.objects.all()
    model_form = forms.SlurmUserImportForm


@register_model_view(SlurmUser, "bulk_edit", path="edit", detail=False)
class SlurmUserBulkEditView(generic.BulkEditView):
    queryset = SlurmUser.objects.all()
    filterset = filtersets.SlurmUserFilterSet
    table = tables.SlurmUserTable
    form = forms.SlurmUserBulkEditForm


@register_model_view(SlurmUser, "bulk_delete", path="delete", detail=False)
class SlurmUserBulkDeleteView(generic.BulkDeleteView):
    queryset = SlurmUser.objects.all()
    filterset = filtersets.SlurmUserFilterSet
    table = tables.SlurmUserTable


@register_model_view(Allocation, "slurm-association", path="slurm-association")
class AllocationSlurmAssociationView(generic.ObjectView):
    queryset = Allocation.objects.all()
    template_name = "slurm/allocation/slurm_association.html"
    tab = ViewTab(
        label=_("Slurm Association"),
        visible=lambda obj: obj.slurm_slurmassociation_extensions.exists(),
        permission="slurm.view_slurmassociation",
        weight=500,
    )

    def get_permitted_actions(self, request, model=None, actions=None):
        # Actions target the SlurmAssociation, not the Allocation
        from coldfront.slurm.models import SlurmAssociation

        return super().get_permitted_actions(request, model=SlurmAssociation, actions=(EditObject,))

    def get_extra_context(self, request, instance):
        slurm_association = instance.slurm_slurmassociation_extensions.first()
        return_url = get_action_url(instance, action="slurm-association", kwargs={"pk": instance.pk})
        return {
            "slurm_association": slurm_association,
            "return_url": return_url,
        }
