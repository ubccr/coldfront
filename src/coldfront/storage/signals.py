# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StorageQuota)
def on_storagequota_hard_limit_changed(sender, instance, **kwargs):
    """Detect hard_limit_bytes changes on active quotas and adjust allocated_bytes.

    When an admin changes ``hard_limit_bytes`` on a ``StorageQuota`` whose
    allocation is ACTIVE, update ``allocated_bytes`` on both the resource
    and its clusters by the delta.
    """
    if kwargs.get("raw", False):
        return

    # Detect hard_limit_bytes change using the saved model's previous value
    try:
        prev = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    delta = (instance.hard_limit_bytes or 0) - (prev.hard_limit_bytes or 0)
    if delta == 0:
        return

    # Only adjust if the allocation is ACTIVE
    if instance.allocation.status != AllocationStatusChoices.STATUS_ACTIVE:
        return

    # Determine target clusters (same logic as callbacks)
    resource = instance.storage
    target_clusters = list(instance.clusters.all()) if instance.clusters.exists() else list(resource.clusters.all())

    # Update resource and cluster allocated_bytes atomically
    StorageResource.objects.filter(pk=resource.pk).update(
        allocated_bytes=F("allocated_bytes") + delta,
    )
    for cluster in target_clusters:
        StorageCluster.objects.filter(pk=cluster.pk).update(
            allocated_bytes=F("allocated_bytes") + delta,
        )
