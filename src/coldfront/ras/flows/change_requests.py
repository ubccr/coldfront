# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import copy
import logging
from datetime import timedelta

import jsonschema
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from jsonschema.exceptions import ValidationError as JSONValidationError
from viewflow import fsm, this

from coldfront.exceptions import AbortRequest
from coldfront.flows import ColdFrontFlow
from coldfront.ras import object_actions as actions
from coldfront.ras.choices import AllocationChangeRequestStatusChoices
from coldfront.ras.models.change_requests import (
    AllocationChangeRequest,
)
from coldfront.ras.signals import allocation_change_request_status_change
from coldfront.users.permissions import get_permission_for_model

logger = logging.getLogger(__name__)


class AllocationChangeRequestFlow(ColdFrontFlow):
    """
    FSM workflow for Allocation Change Requests.

    Status flow:
        requested → approved → applied
        requested → denied
    """

    status = fsm.State(
        AllocationChangeRequestStatusChoices,
        default=AllocationChangeRequestStatusChoices.STATUS_REQUESTED,
    )
    label = "Change Request"
    actions = (
        actions.ApproveChange,
        actions.DenyChange,
        actions.ApplyChange,
    )

    def __init__(self, change_request):
        self.change_request = change_request

    @status.setter()
    def _set_change_request_status(self, value):
        self.change_request.status = value

    @status.getter()
    def _get_change_request_status(self):
        return self.change_request.status

    @status.on_success()
    def _on_success_transition(self, descriptor, source, target):
        if self.change_request is None:
            return

        with transaction.atomic():
            self.change_request.save()

        allocation_change_request_status_change.send(
            sender=self.__class__,
            source=source,
            target=target,
        )

        # Dispatch registered plugin callbacks for this target state
        self._dispatch_target_callbacks(self.change_request, source=source, target=target)

    @status.transition(
        source=AllocationChangeRequestStatusChoices.STATUS_REQUESTED,
        target=AllocationChangeRequestStatusChoices.STATUS_APPROVED,
        label=_("Approve"),
        permission=this.can_approve,
    )
    def approve(self):
        pass

    @status.transition(
        source=AllocationChangeRequestStatusChoices.STATUS_REQUESTED,
        target=AllocationChangeRequestStatusChoices.STATUS_DENIED,
        label=_("Deny"),
        permission=this.can_deny,
    )
    def deny(self):
        pass

    @status.transition(
        source=AllocationChangeRequestStatusChoices.STATUS_APPROVED,
        target=AllocationChangeRequestStatusChoices.STATUS_APPLIED,
        label=_("Apply"),
        permission=this.can_apply,
    )
    def apply(self):
        """
        Apply all proposed changes atomically:

        1. Snapshot the allocation.
        2. Apply extension_days → add days to end_date.
        3. Apply attribute_changes → merge JSON keys and validate against schema.
        4. Apply extension_changes → call apply_json_change() on each extension.
        5. Save all modified models.
        6. Set status to "applied".
        """
        change_request = self.change_request
        allocation = change_request.allocation

        with transaction.atomic():
            # Snapshot the allocation for changelog
            if hasattr(allocation, "snapshot"):
                allocation.snapshot()

            # --- Apply extension_days ---
            if change_request.extension_days is not None:
                if allocation.end_date:
                    allocation.end_date += timedelta(days=change_request.extension_days)
                else:
                    allocation.end_date = timezone.now() + timedelta(days=change_request.extension_days)

            # --- Apply attribute_changes ---
            if change_request.attribute_changes:
                # Snapshot current attribute_data before applying
                change_request.snapshot_attribute_values = copy.deepcopy(allocation.attribute_data) or {}

                current = allocation.attribute_data or {}
                current.update(change_request.attribute_changes)
                allocation.attribute_data = current

                # Validate merged attribute_data against resource schema
                resource = allocation.resource_object
                if resource and resource.schema:
                    try:
                        jsonschema.validate(
                            allocation.attribute_data,
                            schema=resource.schema,
                        )
                    except JSONValidationError as e:
                        raise ValidationError(_("Invalid attribute data after merge: {error}").format(error=e))

            # --- Apply extension_changes ---
            if change_request.extension_changes:
                from django.apps import apps as django_apps

                # Snapshot current extension values before applying
                current_values = {}
                for ext_path in change_request.extension_changes:
                    model = django_apps.get_model(ext_path)
                    if model is None:
                        logger.error(
                            "Extension model '%s' not found — ignoring extension_changes for allocation %s",
                            ext_path,
                            allocation.pk,
                        )
                        continue
                    try:
                        ext_instance = model.objects.get(allocation=allocation)
                        current_values[ext_path] = ext_instance.serialize_object()
                    except model.DoesNotExist:
                        current_values[ext_path] = {}
                        continue
                if current_values:
                    change_request.snapshot_extension_values = current_values

                # Apply proposed changes to live instances
                for ext_path, values in change_request.extension_changes.items():
                    model = django_apps.get_model(ext_path)
                    if model is None:
                        continue
                    try:
                        ext_instance = model.objects.get(allocation=allocation)
                        ext_instance.apply_json_change(values)
                    except model.DoesNotExist:
                        continue
                    except ValidationError as e:
                        raise AbortRequest(
                            _("Validation error applying {ext_path}: {error}").format(
                                ext_path=ext_path,
                                error=", ".join(e.messages),
                            )
                        )

            # Save the change request
            change_request.save()

            # Save the allocation
            allocation.save()

    def can_approve(self, user):
        if not self._check_permission_callbacks("approve", self.change_request, user):
            return False
        return True

    def can_deny(self, user):
        if not self._check_permission_callbacks("deny", self.change_request, user):
            return False
        return True

    def can_apply(self, user):
        if not self._check_permission_callbacks("apply", self.change_request, user):
            return False
        return True


def get_permitted_transition_actions(change_request, user):
    """
    Return a list of ObjectAction instances the user may perform on the given
    change request, based on its current state.  Checks both Django model
    permissions and FSM plugin permission callbacks.
    """
    if not change_request.status:
        return []

    outgoing = AllocationChangeRequestFlow.status.get_outgoing_transitions(change_request.status)
    action_classes = AllocationChangeRequestFlow.get_actions([t.slug for t in outgoing])

    permitted = []
    flow = AllocationChangeRequestFlow(change_request)
    for action in action_classes:
        # Gate 1: Django model permission
        required_perms = [get_permission_for_model(AllocationChangeRequest, p) for p in action.permissions_required]
        if required_perms and not user.has_perms(required_perms):
            continue
        # Gate 2: FSM plugin callbacks
        transition_func = getattr(flow, action.transition)
        if not transition_func.has_perm(user):
            continue
        permitted.append(action)

    return permitted
