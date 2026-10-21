# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""DB-only consistency handlers for storage allocations.

All handlers are DB-only — they track capacity sums and validate limits
against active allocations.  The REST side is handled exclusively by the
batch reconciliation sync (``sync_storage_clusters``), which the CLI
commands and system jobs call.  There are no targeted/real-time enqueues.
"""

import logging

from django.db.models import F

from coldfront.lib.flows import register_target_callback
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource

logger = logging.getLogger(__name__)


def _get_target_clusters(quota, resource):
    """Return the list of clusters a quota should apply to.

    If ``quota.clusters`` is set, use those.  Otherwise use ALL clusters
    backing the resource.
    """
    if quota.clusters.exists():
        return list(quota.clusters.all())
    return list(resource.clusters.all())


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_APPROVED)
def on_allocation_approved(allocation, *, source, target):
    """
    On allocation approved: StorageQuota already exists (created on
    request).  The admin reviews and sets the final hard_limit_bytes, path,
    owning_user, owning_group, and cluster selection before activation.

    Validate that the proposed hard_limit_bytes doesn't exceed resource or
    cluster capacity.
    """
    resource = allocation.resource_object
    if not isinstance(resource, StorageResource):
        return

    try:
        quota = StorageQuota.objects.get(allocation=allocation)
    except StorageQuota.DoesNotExist:
        logger.warning("StorageQuota not found for allocation %s — skipping", allocation.pk)
        return

    # Capacity validation against the hard_limit_bytes
    # (advisory — admin can still approve).  The final hard_limit_bytes
    # is validated later in on_allocation_activated.
    requested = quota.hard_limit_bytes
    if requested:
        target_clusters = _get_target_clusters(quota, resource)

        if resource.capacity_bytes:
            projected = resource.allocated_bytes + requested
            if projected > resource.capacity_bytes:
                logger.warning(
                    "Approval of allocation %s would exceed resource capacity: "
                    "%d / %d bytes already allocated, +%d requested",
                    allocation.pk,
                    resource.allocated_bytes,
                    resource.capacity_bytes,
                    requested,
                )

        for cluster in target_clusters:
            if cluster.capacity_bytes:
                projected = cluster.allocated_bytes + requested
                if projected > cluster.capacity_bytes:
                    logger.warning(
                        "Approval of allocation %s would exceed cluster %s capacity: "
                        "%d / %d bytes already allocated, +%d requested",
                        allocation.pk,
                        cluster.name,
                        cluster.allocated_bytes,
                        cluster.capacity_bytes,
                        requested,
                    )


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_ACTIVE)
def on_allocation_activated(allocation, *, source, target):
    """
    On allocation activate: update resource and cluster capacity
    tracking.  The REST side (path and quota creation on the backend) is
    handled exclusively by the batch reconciliation sync.
    """
    resource = allocation.resource_object
    if not isinstance(resource, StorageResource):
        return

    try:
        quota = StorageQuota.objects.get(allocation=allocation)
    except StorageQuota.DoesNotExist:
        logger.warning("StorageQuota not found for allocation %s — skipping", allocation.pk)
        return

    target_clusters = _get_target_clusters(quota, resource)

    # Capacity validation against the final hard_limit_bytes
    if quota.hard_limit_bytes:
        if resource.capacity_bytes:
            projected = resource.allocated_bytes + quota.hard_limit_bytes
            if projected > resource.capacity_bytes:
                logger.warning(
                    "Activation of allocation %s exceeds resource capacity: %d / %d bytes allocated, +%d activating",
                    allocation.pk,
                    resource.allocated_bytes,
                    resource.capacity_bytes,
                    quota.hard_limit_bytes,
                )
        for cluster in target_clusters:
            if cluster.capacity_bytes:
                projected = cluster.allocated_bytes + quota.hard_limit_bytes
                if projected > cluster.capacity_bytes:
                    logger.warning(
                        "Activation of allocation %s exceeds cluster %s capacity: "
                        "%d / %d bytes allocated, +%d activating",
                        allocation.pk,
                        cluster.name,
                        cluster.allocated_bytes,
                        cluster.capacity_bytes,
                        quota.hard_limit_bytes,
                    )

    # Update resource and cluster capacity tracking
    if quota.hard_limit_bytes:
        StorageResource.objects.filter(pk=quota.storage_id).update(
            allocated_bytes=F("allocated_bytes") + quota.hard_limit_bytes,
        )
        for cluster in target_clusters:
            StorageCluster.objects.filter(pk=cluster.pk).update(
                allocated_bytes=F("allocated_bytes") + quota.hard_limit_bytes,
            )


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_EXPIRED)
def on_allocation_expired(allocation, *, source, target):
    """
    On allocation expired: update resource and cluster capacity tracking.
    Quota removal and path locking are handled exclusively by the batch
    reconciliation sync.
    """
    resource = allocation.resource_object
    if not isinstance(resource, StorageResource):
        return

    try:
        quota = StorageQuota.objects.get(allocation=allocation)
    except StorageQuota.DoesNotExist:
        logger.warning("StorageQuota not found for allocation %s — skipping", allocation.pk)
        return

    target_clusters = _get_target_clusters(quota, resource)

    # Update capacity tracking
    if quota.hard_limit_bytes:
        StorageResource.objects.filter(
            pk=quota.storage_id,
            allocated_bytes__gte=quota.hard_limit_bytes,
        ).update(
            allocated_bytes=F("allocated_bytes") - quota.hard_limit_bytes,
        )
        for cluster in target_clusters:
            StorageCluster.objects.filter(
                pk=cluster.pk,
                allocated_bytes__gte=quota.hard_limit_bytes,
            ).update(
                allocated_bytes=F("allocated_bytes") - quota.hard_limit_bytes,
            )


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_REVOKED)
def on_allocation_revoked(allocation, *, source, target):
    """
    On allocation revoked: update resource and cluster capacity tracking.
    Quota removal and path locking are handled exclusively by the batch
    reconciliation sync.
    """
    resource = allocation.resource_object
    if not isinstance(resource, StorageResource):
        return

    try:
        quota = StorageQuota.objects.get(allocation=allocation)
    except StorageQuota.DoesNotExist:
        logger.warning("StorageQuota not found for allocation %s — skipping", allocation.pk)
        return

    target_clusters = _get_target_clusters(quota, resource)

    # Update capacity tracking
    if quota.hard_limit_bytes:
        StorageResource.objects.filter(
            pk=quota.storage_id,
            allocated_bytes__gte=quota.hard_limit_bytes,
        ).update(
            allocated_bytes=F("allocated_bytes") - quota.hard_limit_bytes,
        )
        for cluster in target_clusters:
            StorageCluster.objects.filter(
                pk=cluster.pk,
                allocated_bytes__gte=quota.hard_limit_bytes,
            ).update(
                allocated_bytes=F("allocated_bytes") - quota.hard_limit_bytes,
            )


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_DENIED)
def on_allocation_denied(allocation, *, source, target):
    """
    On allocation denied: clean up the StorageQuota skeleton that was
    created on request.  No backend action is needed — the quota was
    never activated.
    """
    resource = allocation.resource_object
    if not isinstance(resource, StorageResource):
        return

    StorageQuota.objects.filter(allocation=allocation).delete()
