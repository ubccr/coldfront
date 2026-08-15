# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from coldfront.models import ColdFrontModel
from coldfront.models.features import CommentingMixin
from coldfront.models.fields import AutoSlugField
from coldfront.ras.choices import AllocationChangeRequestStatusChoices


class AllocationChangeRequest(CommentingMixin, ColdFrontModel):
    """
    A bundle of proposed changes to an active allocation.  A single change
    request carries proposed changes to allocation fields (extension_days),
    allocation attributes (attribute_changes), and extension models
    (extension_changes) that are reviewed and applied as a unit by an
    administrator.
    """

    allocation = models.ForeignKey(
        to="ras.Allocation",
        on_delete=models.PROTECT,
        related_name="change_requests",
        verbose_name=_("allocation"),
    )
    slug = AutoSlugField(
        verbose_name=_("slug"),
    )
    status = models.CharField(
        verbose_name=_("status"),
        max_length=50,
        choices=AllocationChangeRequestStatusChoices,
        default=AllocationChangeRequestStatusChoices.STATUS_REQUESTED,
    )
    requested_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_allocation_changes",
        verbose_name=_("requested by"),
    )
    reviewer = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_allocation_changes",
        blank=True,
        null=True,
        verbose_name=_("reviewer"),
    )
    justification = models.TextField(
        verbose_name=_("justification"),
        blank=True,
    )

    clone_fields = ("allocation", "justification", "slug", "extension_days")

    class Meta:
        ordering = ["created"]
        verbose_name = _("allocation change request")
        verbose_name_plural = _("allocation change requests")
        permissions = (
            ("request", _("Request change")),
            ("approve", _("Approve change")),
            ("deny", _("Deny change")),
            ("apply", _("Apply change")),
        )

    def get_status_color(self):
        return AllocationChangeRequestStatusChoices.colors.get(self.status)

    def __str__(self):
        return f"Change request {self.pk} for {self.allocation.slug}"

    extension_days = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("extension (days)"),
        help_text=_(
            "Number of days to extend the allocation end_date. On apply, the end_date is increased by this many days."
        ),
    )
    attribute_changes = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("attribute changes"),
        help_text=_(
            "JSON object containing only the keys that should change. "
            "On apply, these are merged into the allocation's attribute_data "
            "and validated against the resource schema."
        ),
    )
    extension_changes = models.JSONField(
        blank=True,
        default=dict,
        verbose_name=_("extension changes"),
        help_text=_(
            "JSON object mapping extension model paths to dicts of proposed field values. "
            "On apply, each extension's apply_json_change() is called with its proposed values."
        ),
    )
    snapshot_extension_values = models.JSONField(
        blank=True,
        default=dict,
        verbose_name=_("snapshot extension values"),
        help_text=_(
            "Snapshot of extension field values at the time the change request was applied. "
            "Populated during the apply transition. Empty for unapplied requests."
        ),
    )
    snapshot_attribute_values = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("snapshot attribute values"),
        help_text=_(
            "Snapshot of allocation attribute_data at the time the change request was applied. "
            "Populated during the apply transition. Null for unapplied requests."
        ),
    )

    def clean(self):
        super().clean()

        # Skip validation on new instances — must be saved first
        if self.pk is not None:
            # Check at least one change type has a value
            has_changes = any(
                [
                    self.extension_days is not None,
                    self.attribute_changes is not None and self.attribute_changes != {},
                    self.extension_changes is not None and self.extension_changes != {},
                ]
            )
            if not has_changes:
                raise ValidationError(_("A change request must have at least one proposed change."))
