# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.db.models import F

from coldfront.flows import register_target_callback
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource
from coldfront.storage.sync import enqueue_activate_allocation, enqueue_deactivate_allocation

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
    On allocation activate: enqueue the REST API call to create the
    path and quota on each cluster.  The StorageQuota already exists
    (created on request) with the storage set.

    If ``quota.clusters`` is set, create on those clusters only.
    If null, create on ALL clusters backing ``quota.storage``.
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

    for cluster in target_clusters:
        enqueue_activate_allocation(
            allocation.pk,
            cluster_id=cluster.pk,
            share_type=quota.share_type,
        )

    # Apply snapshot policy: policy is owned by one cluster.
    # Only apply it to its owning cluster, not to all target clusters.
    if quota.snapshot_policy_id:
        policy_cluster = quota.snapshot_policy.cluster
        if policy_cluster in target_clusters:
            # Skip if the policy's owning cluster has no backend
            if policy_cluster.backend_path is None:
                logger.warning(
                    "Cluster %s has no backend — cannot apply snapshot policy for allocation %s",
                    policy_cluster.name,
                    allocation.pk,
                )
            else:
                from coldfront.storage.backends.registry import get_backend

                backend = get_backend(policy_cluster.backend_path, cluster_name=policy_cluster.name)
                if hasattr(backend, "apply_snapshot_policy"):
                    try:
                        backend.apply_snapshot_policy(
                            path=quota.path,
                            policy={
                                "interval": quota.snapshot_policy.interval,
                                "retention_days": quota.snapshot_policy.retention_days,
                                "extra_config": quota.snapshot_policy.extra_config,
                            },
                        )
                    except Exception as exc:
                        logger.warning(
                            "Failed to apply snapshot policy for allocation %s: %s",
                            allocation.pk,
                            exc,
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
    On allocation expired: enqueue deactivation to remove quota and
    optionally lock the path on each cluster.
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
    for cluster in target_clusters:
        enqueue_deactivate_allocation(allocation.pk, cluster_id=cluster.pk)

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
    On allocation revoked: enqueue deactivation to remove quota and
    optionally lock/delete the path on each cluster.
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
    for cluster in target_clusters:
        enqueue_deactivate_allocation(allocation.pk, cluster_id=cluster.pk)

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
