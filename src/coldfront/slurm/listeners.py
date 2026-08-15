# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from coldfront.flows import register_target_callback, register_transition_permission_callback
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.ras.models import Allocation, ProjectUser
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmUser,
)
from coldfront.slurm.sync import (
    _sync_association_qos,
    enqueue_activate_allocation,
    enqueue_deactivate_allocation,
    enqueue_remove_project_user,
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
    against all remaining projects they belong to, and enqueue a targeted
    handler to remove the user's associations from Slurm.
    """
    _sync_slurm_users_for_user(instance.user)

    # Determine clusters involved in this project's active allocations
    project_cluster_ids: list[int] = []
    allocations = Allocation.objects.filter(
        project_id=instance.project_id,
        status=AllocationStatusChoices.STATUS_ACTIVE,
    ).select_related(
        "resource_object_type",
    )
    for allocation in allocations:
        resource = allocation.resource_object
        if resource is None:
            continue
        if isinstance(resource, SlurmPartition):
            if resource.cluster_id not in project_cluster_ids:
                project_cluster_ids.append(resource.cluster_id)
        elif isinstance(resource, SlurmCluster):
            if resource.pk not in project_cluster_ids:
                project_cluster_ids.append(resource.pk)

    enqueue_remove_project_user(
        instance.project_id,
        instance.user_id,
        cluster_ids=project_cluster_ids or None,
    )


@receiver(post_save, sender=SlurmAssociation)
def on_slurm_association_saved(instance, **kwargs):
    """
    When a SlurmAssociation is saved, sync SlurmUser records for all project
    members if the linked allocation is active.

    This handles the case where an admin edits a SlurmAssociation and
    changes the slurm_account on an active allocation.  The underlying
    _sync_slurm_users_for_user already handles no-ops efficiently.
    """
    allocation = instance.allocation
    if allocation.status != AllocationStatusChoices.STATUS_ACTIVE:
        return  # only sync for active allocations

    resource = allocation.resource_object
    if resource is None:
        return
    if not isinstance(resource, (SlurmCluster, SlurmPartition)):
        return

    # Sync SlurmUser for each project member
    for project_user in allocation.project.users.all():
        _sync_slurm_users_for_user(project_user.user)

    # Sync QOS changes for this association
    cluster = resource if isinstance(resource, SlurmCluster) else resource.cluster
    _sync_association_qos(instance, cluster)


# ------------------------------------------------------------------
# M2M change handlers for QOS fields
# ------------------------------------------------------------------


def _sync_associations_for_account(account: SlurmAccount) -> None:
    """
    Sync QOS for all active associations linked to an account.

    Called when ``qos_add`` or ``qos_remove`` changes on the account.
    Finds all SlurmAssociation records that reference this account
    and triggers a targeted QOS sync for each.
    """
    from coldfront.slurm.models import SlurmCluster

    # Collect unique (association, cluster) pairs
    assocs = SlurmAssociation.objects.filter(slurm_account=account).select_related(
        "allocation__resource_object_type",
    )
    for assoc in assocs:
        allocation = assoc.allocation
        if not allocation:
            continue
        if allocation.status != AllocationStatusChoices.STATUS_ACTIVE:
            continue
        resource = allocation.resource_object
        if resource is None:
            continue
        if isinstance(resource, SlurmCluster):
            cluster = resource
        elif isinstance(resource, SlurmPartition):
            cluster = resource.cluster
        else:
            continue

        _sync_association_qos(assoc, cluster)


@receiver(m2m_changed, sender=SlurmAccount.qos_add.through)
@receiver(m2m_changed, sender=SlurmAccount.qos_remove.through)
def on_account_qos_changed(action, instance, pk_set, **kwargs):
    """
    When ``qos_add`` or ``qos_remove`` changes on a ``SlurmAccount``,
    sync all active associations linked to that account.
    """
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    _sync_associations_for_account(instance)


@receiver(m2m_changed, sender=SlurmAssociation.qos_add.through)
@receiver(m2m_changed, sender=SlurmAssociation.qos_remove.through)
def on_association_qos_changed(action, instance, pk_set, **kwargs):
    """
    When ``qos_add`` or ``qos_remove`` changes on a ``SlurmAssociation``,
    sync the association's QOS with Slurm.
    """
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    allocation = instance.allocation
    if not allocation:
        return
    if allocation.status != AllocationStatusChoices.STATUS_ACTIVE:
        return
    resource = allocation.resource_object
    if resource is None:
        return
    if isinstance(resource, SlurmCluster):
        cluster = resource
    elif isinstance(resource, SlurmPartition):
        cluster = resource.cluster
    else:
        return

    _sync_association_qos(instance, cluster)


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_ACTIVE)
def on_allocation_activated(allocation, *, source, target):
    """
    On allocation activate: for each ProjectUser (allocation.project.users),
    if no SlurmUser exists for (user, cluster), create one with default_account
    set to the active allocation's slurm_account.

    Existing records are never modified by subsequent allocation activations,
    preserving the original default.
    """
    resource = allocation.resource_object
    if resource is None:
        return
    if not isinstance(resource, (SlurmCluster, SlurmPartition)):
        return

    # Determine the cluster
    if isinstance(resource, SlurmCluster):
        cluster = resource
    else:
        cluster = resource.cluster

    # Get the slurm_account from the allocation's SlurmAssociation
    try:
        association = SlurmAssociation.objects.get(allocation=allocation)
    except SlurmAssociation.DoesNotExist:
        return

    slurm_account = association.slurm_account
    if slurm_account is None:
        return  # no account set yet, nothing to do

    # For each ProjectUser, create SlurmUser if not exists
    for project_user in allocation.project.users.all():
        user = project_user.user
        # get_or_create: existing records are never modified
        SlurmUser.objects.get_or_create(
            user=user,
            cluster=cluster,
            defaults={"default_account": slurm_account},
        )

    # Enqueue REST API sync for this allocation
    enqueue_activate_allocation(allocation.pk, cluster_id=cluster.pk)


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_EXPIRED)
def on_allocation_expired(allocation, *, source, target):
    """
    On allocation expired: enqueue deactivation to kill jobs and remove
    associations from Slurm.
    """
    resource = allocation.resource_object
    if resource is None:
        return
    if not isinstance(resource, (SlurmCluster, SlurmPartition)):
        return
    cluster = resource if isinstance(resource, SlurmCluster) else resource.cluster
    enqueue_deactivate_allocation(allocation.pk, cluster_id=cluster.pk)


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_REVOKED)
def on_allocation_revoked(allocation, *, source, target):
    """
    On allocation revoked: enqueue deactivation to kill jobs and remove
    associations from Slurm.
    """
    resource = allocation.resource_object
    if resource is None:
        return
    if not isinstance(resource, (SlurmCluster, SlurmPartition)):
        return
    cluster = resource if isinstance(resource, SlurmCluster) else resource.cluster
    enqueue_deactivate_allocation(allocation.pk, cluster_id=cluster.pk)


@register_target_callback(AllocationStatusFlow, AllocationStatusChoices.STATUS_RENEW)
def on_allocation_renewed(allocation, *, source, target):
    """
    On allocation renewed: no Slurm action needed until the allocation is
    re-activated.  The renewed allocation will trigger
    ``on_allocation_activated`` when it transitions to ACTIVE again.
    """
    pass


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
