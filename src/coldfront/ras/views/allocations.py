# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.shortcuts import get_object_or_404

from coldfront.ras import filtersets, flows, forms, tables
from coldfront.ras import object_actions as actions
from coldfront.ras.flows import get_permitted_transition_actions
from coldfront.ras.models import Allocation, Project
from coldfront.registry import register_model_view
from coldfront.views import generic
from coldfront.views.mixins import GetRelatedModelsMixin

#
# Allocations
#


@register_model_view(Allocation, "list", path="", detail=False)
class AllocationListView(generic.ObjectListView):
    queryset = Allocation.objects.all()
    filterset = filtersets.AllocationFilterSet
    filterset_form = forms.AllocationFilterSetForm
    table = tables.AllocationTable


@register_model_view(Allocation)
class AllocationView(GetRelatedModelsMixin, generic.ObjectView):
    queryset = Allocation.objects.all()
    flow = flows.AllocationStatusFlow

    def get_extra_context(self, request, instance):
        # Get the outgoing transitions for the current status so we can display the appropriate buttons
        transitions = get_permitted_transition_actions(instance, request.user)

        return {
            "transitions": transitions,
            "related_models": self.get_related_models(request, instance),
        }


@register_model_view(Allocation, "add", detail=False)
@register_model_view(Allocation, "edit")
class AllocationEditView(generic.ObjectEditView):
    queryset = Allocation.objects.all()
    form = forms.AllocationForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.owner = request.user

        return super().alter_object(obj, request, url_args, url_kwargs)


@register_model_view(Allocation, "delete")
class AllocationDeleteView(generic.ObjectDeleteView):
    queryset = Allocation.objects.all()


@register_model_view(Allocation, "bulk_import", path="import", detail=False)
class AllocationBulkImportView(generic.BulkImportView):
    queryset = Allocation.objects.all()
    model_form = forms.AllocationImportForm


@register_model_view(Allocation, "bulk_edit", path="edit", detail=False)
class AllocationBulkEditView(generic.BulkEditView):
    queryset = Allocation.objects.all()
    filterset = filtersets.AllocationFilterSet
    table = tables.AllocationTable
    form = forms.AllocationBulkEditForm


@register_model_view(Allocation, "bulk_delete", path="delete", detail=False)
class AllocationBulkDeleteView(generic.BulkDeleteView):
    queryset = Allocation.objects.all()
    filterset = filtersets.AllocationFilterSet
    table = tables.AllocationTable


#
# Allocation status workflow
#


class BaseAllocationFlowView(generic.ObjectFlowView):
    queryset = Allocation.objects.all()
    form = forms.AllocationReviewForm
    flow = flows.AllocationStatusFlow


# Allocations are requested from a project
@register_model_view(Project, "allocationrequest", path="allocation-request")
class AllocationRequestView(BaseAllocationFlowView):
    template_name = "ras/project/allocation_request.html"
    form = forms.AllocationRequestForm
    action = actions.RequestObject

    def get_object(self, **kwargs):
        project = get_object_or_404(Project.objects.all(), **kwargs)
        return Allocation(project=project, tenant=project.tenant)

    def alter_object(self, obj, request, url_args, url_kwargs):
        obj.owner = request.user
        return obj

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        return context


@register_model_view(Allocation, "approve")
class AllocationApproveView(BaseAllocationFlowView):
    action = actions.ApproveObject


@register_model_view(Allocation, "deny")
class AllocationDenyView(BaseAllocationFlowView):
    action = actions.DenyObject


@register_model_view(Allocation, "revoke")
class AllocationRevokeView(BaseAllocationFlowView):
    action = actions.RevokeObject


@register_model_view(Allocation, "renew")
class AllocationRenewView(BaseAllocationFlowView):
    action = actions.RenewObject


@register_model_view(Allocation, "activate")
class AllocationActivateView(BaseAllocationFlowView):
    form = forms.AllocationActivateForm
    action = actions.ActivateObject
