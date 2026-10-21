# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm listeners: DB-only consistency for active allocations.

All handlers are DB-only — they keep ColdFront's ``SlurmUser`` records in
sync with active allocations, keyed on ``STATUS_ACTIVE``. The REST side is
handled exclusively by the batch reconciliation sync (``sync_slurm_clusters``),
which the CLI and system jobs call. There are no targeted/real-time enqueues.

The single shared helper :func:`_sync_slurm_users_for_user` reconciles a
user's ``SlurmUser`` records against active allocations across all projects
they belong to — creating on gain of access, updating ``default_account`` on
change, deleting on loss of access. Every handler just calls it for the
affected users.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from coldfront.lib.flows import register_target_callback, register_transition_permission_callback
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.ras.models import Allocation, ProjectUser
from coldfront.slurm.models import (
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmUser,
)


def _get_cluster_account_pairs(project):
    """
    Given a project, return a dict mapping SlurmCluster -> slurm_account
    (the first SlurmAccount from active allocations on that cluster).

    Only considers active (STATUS_ACTIVE) allocations whose resource_object
    is a SlurmCluster or SlurmPartition.
    """
    result = {}
    allocations = Allocation.objects.filter(
        project=project,
        status=AllocationStatusChoices.STATUS_ACTIVE,
    ).select_related(
        "resource_object_type",
    )
    for allocation in allocations:
        resource = allocation.resource_object
        if resource is None:
            continue
        if isinstance(resource, SlurmPartition):
            cluster = resource.cluster
        elif isinstance(resource, SlurmCluster):
            cluster = resource
        else:
            continue

        if cluster.pk in result:
            continue  # already have an account for this cluster

        try:
            association = SlurmAssociation.objects.get(allocation=allocation)
        except SlurmAssociation.DoesNotExist:
            continue

        if association.slurm_account is None:
            continue

        result[cluster.pk] = (cluster, association.slurm_account)

    return result


def _sync_slurm_users_for_user(user):
    """
    Reconcile SlurmUser records for a given user against all projects they
    belong to.

    For each cluster the user has access to (via an active slurm allocation
    on any project), ensure a SlurmUser exists with the correct default_account.
    For clusters the user no longer has access to, remove the SlurmUser record.
    """
    # Collect all cluster->account pairs across all projects this user belongs to
    cluster_account = {}  # cluster_pk -> (cluster, slurm_account)
    for pu in ProjectUser.objects.filter(user=user).select_related("project"):
        pairs = _get_cluster_account_pairs(pu.project)
        for pk, (cluster, account) in pairs.items():
            if pk not in cluster_account:
                cluster_account[pk] = (cluster, account)

    # Get all SlurmUser records for this user
    existing_users = {su.cluster.pk: su for su in SlurmUser.objects.filter(user=user).select_related("cluster")}

    # For each cluster the user has access to
    for pk, (cluster, slurm_account) in cluster_account.items():
        if pk in existing_users:
            # Update if the default_account changed
            su = existing_users[pk]
            if su.default_account != slurm_account:
                su.default_account = slurm_account
                su.save()
        else:
            # Create a new SlurmUser
            SlurmUser.objects.create(
                user=user,
                cluster=cluster,
                default_account=slurm_account,
            )

    # For clusters the user no longer has access to, remove the SlurmUser
    for pk, su in existing_users.items():
        if pk not in cluster_account:
            su.delete()


@receiver(post_save, sender=ProjectUser)
def on_project_user_saved(instance, created, **kwargs):
    """
    When a ProjectUser is created (or updated), ensure SlurmUser records
    exist for the user based on all active slurm allocations on the project.
    """
    if created:
        _sync_slurm_users_for_user(instance.user)


@receiver(post_delete, sender=ProjectUser)
def on_project_user_deleted(instance, **kwargs):
    """
    When a ProjectUser is deleted, reconcile SlurmUser records for the user
    against all remaining projects they belong to. The REST removal of the
    user's associations is handled by the next batch reconciliation sync.
    """
    _sync_slurm_users_for_user(instance.user)


def _sync_project_users(project):
    """Reconcile SlurmUser records for every member of a project."""
    for pu in project.users.all():
        if pu.user:
            _sync_slurm_users_for_user(pu.user)


def _allocation_cluster(allocation):
    """Return the SlurmCluster for an allocation's resource, or None."""
    resource = allocation.resource_object
    if resource is None:
        return None
    if isinstance(resource, SlurmCluster):
        return resource
    if isinstance(resource, SlurmPartition):
        return resource.cluster
    return None


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_ACTIVE)
def on_allocation_activated(allocation, *, source, target):
    """
    On allocation activate: reconcile SlurmUser records for each project
    member. The allocation is now ACTIVE, so members gain access — SlurmUser
    records are created (or their default_account updated) on the cluster.
    """
    if _allocation_cluster(allocation) is None:
        return
    _sync_project_users(allocation.project)


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_EXPIRED)
def on_allocation_expired(allocation, *, source, target):
    """
    On allocation expired: reconcile SlurmUser records for each project
    member. The allocation is no longer ACTIVE, so members lose this access —
    SlurmUser records are removed unless the user has another active
    allocation on the cluster. The REST removal is handled by the batch sync.
    """
    if _allocation_cluster(allocation) is None:
        return
    _sync_project_users(allocation.project)


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_REVOKED)
def on_allocation_revoked(allocation, *, source, target):
    """
    On allocation revoked: reconcile SlurmUser records for each project
    member. Same semantics as expiry — members lose this access unless they
    have another active allocation. REST removal is handled by the batch sync.
    """
    if _allocation_cluster(allocation) is None:
        return
    _sync_project_users(allocation.project)


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_DENIED)
def on_allocation_denied(allocation, *, source, target):
    """
    On allocation denied: reconcile SlurmUser records for each project member.
    The allocation is not ACTIVE, so members lose this access unless they have
    another active allocation. REST removal is handled by the batch sync.
    """
    if _allocation_cluster(allocation) is None:
        return
    _sync_project_users(allocation.project)


@register_transition_permission_callback(AllocationStatusFlow, "activate")
def can_activate_check(allocation, user):
    """
    Permission callback for the "activate" transition.

    Blocks activation if the allocation has a SlurmAssociation that still
    has no slurm_account set.  Non-slurm allocations are always allowed.
    """
    resource = allocation.resource_object
    if not isinstance(resource, (SlurmCluster, SlurmPartition)):
        return True

    association = SlurmAssociation.objects.filter(allocation=allocation).first()
    if association is None:
        return False

    return association.slurm_account is not None
