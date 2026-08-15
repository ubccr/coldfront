# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from generic_notifications import send_notification
from viewflow import fsm, this

from coldfront.flows import ColdFrontFlow
from coldfront.ras import object_actions as actions
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation
from coldfront.ras.notifications import AllocationsNotificationType
from coldfront.ras.signals import allocation_status_change
from coldfront.users.permissions import get_permission_for_model


class AllocationStatusFlow(ColdFrontFlow):
    """
    Allocation Status workflow defines the transitions between the statuses of an Allocation.
    """

    status = fsm.State(AllocationStatusChoices, default=AllocationStatusChoices.STATUS_REQUESTED)
    label = "Allocation"
    actions = (
        actions.ApproveObject,
        actions.DenyObject,
        actions.ActivateObject,
        actions.RenewObject,
        actions.RevokeObject,
    )

    def __init__(self, allocation):
        self.allocation = allocation

    @status.setter()
    def _set_allocation_status(self, value):
        self.allocation.status = value

    @status.getter()
    def _get_allocation_status(self):
        return self.allocation.status

    @status.on_success()
    def _on_success_transition(self, descriptor, source, target):
        if self.allocation is None:
            return

        with transaction.atomic():
            self.allocation.save()

        allocation_status_change.send(sender=self.__class__, source=source, target=target)

        # Send notification for approved allocations
        if target == AllocationStatusChoices.STATUS_APPROVED:
            allocation = self.allocation
            subject = f"Allocation {allocation.slug} has been approved"
            text = f"The allocation '{allocation.slug}' for project {allocation.project} has been approved."
            url = allocation.get_absolute_url()

            # Notify the allocation owner
            send_notification(
                recipient=allocation.owner,
                notification_type=AllocationsNotificationType,
                target=allocation,
                subject=subject,
                text=text,
                url=url,
            )

        # Dispatch registered plugin callbacks for this target state
        self._dispatch_target_callbacks(self.allocation, source=source, target=target)

    @status.transition(
        source=AllocationStatusChoices.STATUS_REQUESTED,
        target=AllocationStatusChoices.STATUS_REQUESTED,
        label=_("Request"),
        permission=this.can_request,
    )
    def request(self):
        pass

    @status.transition(
        source={
            AllocationStatusChoices.STATUS_REQUESTED,
            AllocationStatusChoices.STATUS_RENEW,
        },
        target=AllocationStatusChoices.STATUS_APPROVED,
        permission=this.can_approve,
        label=_("Approve"),
    )
    def approve(self):
        pass

    @status.transition(
        source={
            AllocationStatusChoices.STATUS_REQUESTED,
            AllocationStatusChoices.STATUS_RENEW,
        },
        target=AllocationStatusChoices.STATUS_DENIED,
        permission=this.can_deny,
        label=_("Deny"),
    )
    def deny(self):
        pass

    @status.transition(
        source={
            AllocationStatusChoices.STATUS_ACTIVE,
            AllocationStatusChoices.STATUS_EXPIRED,
            AllocationStatusChoices.STATUS_REVOKED,
            AllocationStatusChoices.STATUS_DENIED,
        },
        target=AllocationStatusChoices.STATUS_RENEW,
        permission=this.can_renew,
        label=_("Renew"),
    )
    def renew(self):
        pass

    @status.transition(
        source={
            AllocationStatusChoices.STATUS_APPROVED,
        },
        target=AllocationStatusChoices.STATUS_ACTIVE,
        label=_("Activate"),
        permission=this.can_activate,
    )
    def activate(self):
        pass

    @status.transition(
        source=AllocationStatusChoices.STATUS_ACTIVE,
        target=AllocationStatusChoices.STATUS_EXPIRED,
        permission=this.can_expire,
        label=_("Expire"),
    )
    def expire(self):
        pass

    @status.transition(
        source=AllocationStatusChoices.STATUS_ACTIVE,
        target=AllocationStatusChoices.STATUS_REVOKED,
        permission=this.can_revoke,
        label=_("Revoke"),
    )
    def revoke(self):
        pass

    def can_request(self, user):
        """
        This function checks to see if the allocation can be requested.
        """
        if not self._check_permission_callbacks("request", self.allocation, user):
            return False
        return True

    def can_approve(self, user):
        """
        This function checks to see if the allocation can be approved.
        """
        if not self._check_permission_callbacks("approve", self.allocation, user):
            return False
        return True

    def can_deny(self, user):
        """
        This function checks to see if the allocation can be denied.
        """
        if not self._check_permission_callbacks("deny", self.allocation, user):
            return False
        return True

    def can_activate(self, user):
        """
        This function checks to see if the allocation can be activated.
        """
        # Check registered plugin permission callbacks
        if not self._check_permission_callbacks("activate", self.allocation, user):
            return False
        return True

    def can_expire(self, user):
        """
        This function checks to see if the allocation can be expired.
        """
        if not self._check_permission_callbacks("expire", self.allocation, user):
            return False
        return True

    def can_renew(self, user):
        """
        This function checks to see if the allocation can be renewed.
        """
        if not self._check_permission_callbacks("renew", self.allocation, user):
            return False
        return True

    def can_revoke(self, user):
        """
        This function checks to see if the allocation can be revoked.
        """
        if not self._check_permission_callbacks("revoke", self.allocation, user):
            return False
        return True


def get_permitted_transition_actions(allocation, user):
    """
    Return a list of ObjectAction instances the user may perform on the given
    allocation, based on its current state.  Checks both Django model
    permissions and FSM plugin permission callbacks.
    """
    if not allocation.status:
        return []

    outgoing = AllocationStatusFlow.status.get_outgoing_transitions(allocation.status)
    action_classes = AllocationStatusFlow.get_actions([t.slug for t in outgoing])

    permitted = []
    flow = AllocationStatusFlow(allocation)
    for action in action_classes:
        # Gate 1: Django model permission
        required_perms = [get_permission_for_model(Allocation, p) for p in action.permissions_required]
        if required_perms and not user.has_perms(required_perms):
            continue
        # Gate 2: FSM plugin callbacks
        transition_func = getattr(flow, action.transition)
        if not transition_func.has_perm(user):
            continue
        permitted.append(action)

    return permitted
