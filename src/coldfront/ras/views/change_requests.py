# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from coldfront.ras import filtersets, forms, tables
from coldfront.ras import object_actions as actions
from coldfront.ras.choices import AllocationChangeRequestStatusChoices
from coldfront.ras.flows.change_requests import (
    AllocationChangeRequestFlow,
    get_permitted_transition_actions,
)
from coldfront.ras.models import Allocation
from coldfront.ras.models.change_requests import AllocationChangeRequest
from coldfront.registry import get_allocation_extensions, register_model_view
from coldfront.utils.data import shallow_compare_dict
from coldfront.views import ViewTab, generic
from coldfront.views.object_actions import (
    AddObject,
    BulkDelete,
    BulkExport,
    BulkImport,
    CloneObject,
    EditObject,
)

#
# AllocationChangeRequest list + detail
#


@register_model_view(AllocationChangeRequest, "list", path="", detail=False)
class AllocationChangeRequestListView(generic.ObjectListView):
    queryset = AllocationChangeRequest.objects.all()
    filterset = filtersets.AllocationChangeRequestFilterSet
    filterset_form = forms.AllocationChangeRequestFilterSetForm
    table = tables.AllocationChangeRequestTable
    actions = (AddObject, BulkImport, BulkExport, BulkDelete)


@register_model_view(AllocationChangeRequest)
class AllocationChangeRequestView(generic.ObjectView):
    queryset = AllocationChangeRequest.objects.all()
    flow = AllocationChangeRequestFlow

    def get_permitted_actions(self, user, model=None, actions=None):
        permitted = super().get_permitted_actions(user, model, actions)
        if model is not None and model.pk is not None:
            if model.status == AllocationChangeRequestStatusChoices.STATUS_APPLIED:
                permitted = [a for a in permitted if a not in (EditObject, CloneObject)]
        return permitted

    def get_extra_context(self, request, instance):
        transitions = get_permitted_transition_actions(instance, request.user)

        allocation = instance.allocation
        pre = {}
        post = {}

        # -- allocation.end_date / extension_days --
        if instance.extension_days:
            if allocation.end_date:
                pre["end_date"] = allocation.end_date.isoformat()
                post["end_date"] = (allocation.end_date + timedelta(days=instance.extension_days)).isoformat()
            else:
                pre["end_date"] = None
                post["end_date"] = (timezone.now() + timedelta(days=instance.extension_days)).isoformat()
        elif allocation.end_date:
            pre["end_date"] = allocation.end_date.isoformat()
            post["end_date"] = pre["end_date"]

        # -- attribute_data vs attribute_changes --
        # Use snapshot if available (applied), otherwise live allocation data
        if instance.snapshot_attribute_values is not None:
            current_attrs = instance.snapshot_attribute_values
        else:
            current_attrs = allocation.attribute_data or {}
        for key, value in current_attrs.items():
            pre[f"attribute.{key}"] = value
            post.setdefault(f"attribute.{key}", value)
        if instance.attribute_changes:
            for key, value in instance.attribute_changes.items():
                post[f"attribute.{key}"] = value

        # -- extension changes --
        resource = allocation.resource_object
        if resource:
            resource_path = resource._meta.label_lower
            for model in get_allocation_extensions(resource_path):
                if model is None:
                    continue
                ext_path = model._meta.label_lower
                requestable = model.requestable_fields()

                # Current values: snapshot if applied, else live
                if instance.snapshot_extension_values:
                    current_ext = instance.snapshot_extension_values.get(ext_path, {})
                else:
                    current_ext = {}
                    try:
                        ext_instance = model.objects.get(allocation=allocation)
                        for field_name in requestable:
                            value = getattr(ext_instance, field_name, None)
                            if value is not None and value != "":
                                current_ext[field_name] = value
                    except model.DoesNotExist:
                        pass

                proposed_ext = instance.extension_changes.get(ext_path, {})

                # Apply form-field display formatting for fields with overrides
                overrides = model.requestable_fields_overrides()

                for field_name in requestable:
                    key = f"{ext_path}.{field_name}"
                    cur = current_ext.get(field_name)
                    prop = proposed_ext.get(field_name, cur)

                    # Convert timedelta to string for readable JSON output
                    if isinstance(cur, timedelta):
                        cur = str(cur)
                    if isinstance(prop, timedelta):
                        prop = str(prop)

                    # Use the override field's prepare_value for human-readable display
                    if field_name in overrides:
                        override_field = overrides[field_name]
                        if override_field is not None and hasattr(override_field, "prepare_value"):
                            cur = override_field.prepare_value(cur)
                            prop = override_field.prepare_value(prop)

                    pre[key] = cur
                    post[key] = prop

        # -- compute diff --
        diff_added = shallow_compare_dict(pre, post)
        diff_removed = {k: pre.get(k) for k in diff_added} if diff_added else {}

        return {
            "transitions": transitions,
            "pre_change_data": pre,
            "post_change_data": post,
            "diff_added": diff_added,
            "diff_removed": diff_removed,
        }


@register_model_view(AllocationChangeRequest, "add", detail=False)
@register_model_view(AllocationChangeRequest, "edit")
class AllocationChangeRequestEditView(generic.ObjectEditView):
    queryset = AllocationChangeRequest.objects.all()
    form = forms.AllocationChangeRequestForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            obj.requested_by = request.user
        return super().alter_object(obj, request, url_args, url_kwargs)

    def alter_form(self, form, request, obj):
        if obj.pk and obj.status == AllocationChangeRequestStatusChoices.STATUS_APPLIED:
            for f in form.fields.values():
                f.disabled = True

    def post(self, request, *args, **kwargs):
        obj = self.get_object(**kwargs)
        if obj.pk and obj.status == AllocationChangeRequestStatusChoices.STATUS_APPLIED:
            raise PermissionDenied(_("This change request has already been applied and is no longer editable."))
        return super().post(request, *args, **kwargs)


@register_model_view(AllocationChangeRequest, "delete")
class AllocationChangeRequestDeleteView(generic.ObjectDeleteView):
    queryset = AllocationChangeRequest.objects.all()


#
# AllocationChangeRequest flow views
#


class BaseAllocationChangeRequestFlowView(generic.ObjectFlowView):
    queryset = AllocationChangeRequest.objects.all()
    flow = AllocationChangeRequestFlow

    def alter_object(self, obj, request, url_args, url_kwargs):
        obj.reviewer = request.user
        return super().alter_object(obj, request, url_args, url_kwargs)


@register_model_view(AllocationChangeRequest, "approve")
class AllocationChangeRequestApproveView(BaseAllocationChangeRequestFlowView):
    form = forms.AllocationChangeRequestReviewForm
    action = actions.ApproveChange


@register_model_view(AllocationChangeRequest, "deny")
class AllocationChangeRequestDenyView(BaseAllocationChangeRequestFlowView):
    form = forms.AllocationChangeRequestReviewForm
    action = actions.DenyChange


@register_model_view(AllocationChangeRequest, "apply")
class AllocationChangeRequestApplyView(BaseAllocationChangeRequestFlowView):
    form = forms.AllocationChangeRequestApplyForm
    action = actions.ApplyChange


#
# Allocation tab: show change requests for a given allocation
#


@register_model_view(Allocation, "change_requests", path="change-requests")
class AllocationChangeRequestTabView(generic.ObjectChildrenView):
    actions = ()
    queryset = Allocation.objects.all()
    child_model = AllocationChangeRequest
    table = tables.AllocationChangeRequestTable
    filterset = filtersets.AllocationChangeRequestFilterSet
    filterset_form = forms.AllocationChangeRequestFilterSetForm
    template_name = "ras/allocation/change_requests.html"
    tab = ViewTab(
        label=_("Change Requests"),
        badge=lambda obj: obj.change_requests.count(),
        permission="ras.view_allocationchangerequest",
        weight=500,
    )

    def get_children(self, request, parent):
        return parent.change_requests.restrict(request.user, "view")
