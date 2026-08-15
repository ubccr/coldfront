# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from coldfront.views.generic import ObjectEditView


class AllocatableResourceRequestView(ObjectEditView):
    """
    View for resource-specific post-request forms on allocatable resources.

    Subclasses set:
    - ``queryset`` (the bridge model, e.g., StorageQuota)
    - ``form`` (form with resource-specific fields)
    - ``allocation_fk`` (the FK field name linking back to Allocation)

    The view automatically disables all form fields when the linked
    allocation is not in NEW or RENEW status.  Subclasses can override
    ``editable_statuses`` to permit editing in other statuses.
    """

    allocation_fk = "allocation"
    editable_statuses = None  # set lazily via get_editable_statuses()

    def get_editable_statuses(self):
        """
        Return the list of allocation statuses in which the form should be
        editable.  Defaults to ``[AllocationStatusChoices.STATUS_REQUESTED,
        AllocationStatusChoices.STATUS_RENEW]``.
        """
        if self.editable_statuses is not None:
            return self.editable_statuses
        from coldfront.ras.choices import AllocationStatusChoices

        return [AllocationStatusChoices.STATUS_REQUESTED, AllocationStatusChoices.STATUS_RENEW]

    def get_allocation(self, obj):
        """
        Return the Allocation linked to the bridge model instance via
        ``allocation_fk``, or None if the FK is not set.
        """
        return getattr(obj, self.allocation_fk, None)

    def alter_form(self, form, request, obj):
        """
        Disable all form fields when the linked allocation is not in an
        editable status.
        """
        allocation = self.get_allocation(obj)
        if allocation is None:
            return
        editable = self.get_editable_statuses()
        if allocation.status not in editable:
            for f in form.fields.values():
                f.disabled = True

    def post(self, request, *args, **kwargs):
        """
        Reject POST requests when the allocation is not in an editable status.
        """
        obj = self.get_object(**kwargs)
        allocation = self.get_allocation(obj)
        if allocation is not None:
            editable = self.get_editable_statuses()
            if allocation.status not in editable:
                raise PermissionDenied(_("This allocation is no longer editable."))
        return super().post(request, *args, **kwargs)
