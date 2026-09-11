# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Shared utility functions for the Slurm app.

These helpers are used across the export, sync, ingest, and view layers and
are intentionally importable on their own (no package re-export).
"""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models.allocations import Allocation
from coldfront.slurm.client import SlurmClient
from coldfront.slurm.models import (
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
)


def slurmrestd_configured(cluster: SlurmCluster) -> bool:
    """Return ``True`` if slurmrestd is configured for a cluster.

    A cluster is "configured" when its entry in ``settings.SLURMRESTD_CLUSTERS``
    (or the ``"default"`` fallback) has a non-empty ``url``. This is the only
    gate in the batch-only sync model — a cluster without slurmrestd cannot be
    synced, so the system jobs skip it and the CLI reports it as an error.
    """
    clusters_config = getattr(settings, "SLURMRESTD_CLUSTERS", {})
    config = clusters_config.get(cluster.name) or clusters_config.get("default", {})
    return bool(config.get("url", ""))


def get_active_associations(cluster: SlurmCluster) -> list[SlurmAssociation]:
    """Get all SlurmAssociations whose allocations are active and whose
    resource targets the given cluster.

    Returns:
        list of SlurmAssociation (with prefetched allocation, project)
    """
    cluster_ct = ContentType.objects.get_for_model(SlurmCluster)
    partition_ct = ContentType.objects.get_for_model(SlurmPartition)

    # Allocations targeting this cluster directly
    cluster_allocations = Allocation.objects.filter(
        resource_object_type=cluster_ct,
        resource_object_id=cluster.pk,
        status=AllocationStatusChoices.STATUS_ACTIVE,
    )

    # Allocations targeting partitions that belong to this cluster
    partition_ids = cluster.partitions.values_list("pk", flat=True)
    partition_allocations = Allocation.objects.filter(
        resource_object_type=partition_ct,
        resource_object_id__in=partition_ids,
        status=AllocationStatusChoices.STATUS_ACTIVE,
    )

    # Collect all allocation IDs
    allocation_ids = set(cluster_allocations.values_list("pk", flat=True))
    allocation_ids.update(partition_allocations.values_list("pk", flat=True))

    if not allocation_ids:
        return []

    # Get associations for these allocations
    return list(
        SlurmAssociation.objects.filter(
            allocation_id__in=allocation_ids,
            slurm_account__isnull=False,
        ).select_related("allocation", "slurm_account")
    )


def build_client(cluster: str = "default") -> SlurmClient:
    """Build a :class:`SlurmClient` from Django settings.

    Looks up the cluster name in ``settings.SLURMRESTD_CLUSTERS``.
    Falls back to the ``"default"`` entry when the cluster is not
    listed or when the requested cluster is ``"default"`` itself.

    Raises :class:`django.core.exceptions.ImproperlyConfigured` if
    slurmrestd is not configured (empty URL), the configured Slurm
    version is unsupported, or the API version cannot be discovered.
    """
    clusters_config = getattr(settings, "SLURMRESTD_CLUSTERS", {})

    config = clusters_config.get(cluster) or clusters_config.get("default", {})

    url = config.get("url", "")
    if not url:
        raise ImproperlyConfigured(
            f"Slurm slurmrestd is not configured: SLURMRESTD_CLUSTERS has an empty 'url' for cluster {cluster!r}"
        )

    jwt = config.get("jwt_token", "")
    version = config.get("version", "") or None  # Slurm release, e.g. "25.11.8"
    timeout = config.get("timeout", 30)
    retries = config.get("retries", 3)
    backoff = config.get("retry_backoff", 1.5)

    try:
        client = SlurmClient(
            base_url=url,
            jwt_token=jwt,
            version=version,
            timeout=timeout,
            retries=retries,
            retry_backoff=backoff,
        )
        if version is None:
            client.discover_version()
    except (ValueError, RuntimeError) as exc:
        raise ImproperlyConfigured(f"Slurm client cannot be built: {exc}") from exc

    return client
