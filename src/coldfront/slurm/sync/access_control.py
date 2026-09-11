# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Access-control sync: associations + QOS pushed to Slurm via REST.

Reconciles ColdFront's association/QOS records with the Slurm REST API
(``slurmrestd``). The single code path is :func:`sync_slurm_clusters` — it
performs a full ColdFront -> Slurm reconciliation for one cluster or all,
and is called by the CLI command, the periodic system sync job, and the
on-demand "sync now" job.

The sync is batch-only: there are no targeted/real-time workers. Per cluster
it upserts QOS definitions, creates the desired account/user/association
hierarchy, then sweeps Slurm for orphans — killing running jobs for orphaned
associations before deleting them, then removing orphaned users, accounts,
and QOS. Unconfigured clusters (no slurmrestd ``url``) yield an error report.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from coldfront.slurm.client import SlurmClient
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.slurm.utils import build_client, get_active_associations
from coldfront.users.models import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SyncReport
# ---------------------------------------------------------------------------


@dataclass
class SyncReport:
    """Detailed report returned by sync operations."""

    cluster: str
    success: bool = False
    accounts_created: int = 0
    accounts_deleted: int = 0
    associations_created: int = 0
    associations_deleted: int = 0
    users_created: int = 0
    users_deleted: int = 0
    qos_synced: int = 0
    qos_deleted: int = 0
    jobs_killed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Full reconciliation sync
# ---------------------------------------------------------------------------


def sync_slurm_clusters(cluster_names: list[str] | None = None) -> list[SyncReport]:
    """Perform a full ColdFront -> Slurm reconciliation sync.

    The single code path shared by the CLI, the periodic system sync job, and
    the on-demand "sync now" job. For each cluster:

    1. Always reconcile ColdFront records first (:func:`_ensure_slurm_users_for_cluster`
       — SlurmUser creation/update for active allocation members), independent
       of slurmrestd.
    2. Run the REST reconciliation (:func:`_sync_cluster`), which upserts QOS,
       creates the desired entities, and sweeps Slurm for orphans.

    Args:
        cluster_names: Optional list of cluster names to sync.  ``None`` syncs
            all clusters.

    Returns:
        List of ``SyncReport`` — one per cluster processed.
    """
    clusters = SlurmCluster.objects.all()
    if cluster_names is not None:
        clusters = clusters.filter(name__in=cluster_names)

    reports: list[SyncReport] = []
    for cluster in clusters:
        # (1) Always reconcile ColdFront records, independent of slurmrestd.
        # The DB catch-up (SlurmUser creation for active allocation members)
        # is separate from the REST push below.
        _ensure_slurm_users_for_cluster(cluster)

        # (2) REST reconciliation (error report when slurmrestd misconfigured).
        reports.append(_sync_cluster(cluster))

    return reports


def _sync_cluster(cluster: SlurmCluster) -> SyncReport:
    """REST reconciliation of a single cluster with slurmrestd.

    Assumes the ColdFront records have already been reconciled by the caller
    (``sync_slurm_clusters`` calls :func:`_ensure_slurm_users_for_cluster`
    first, independent of slurmrestd).
    """
    start = timezone.now()
    report = SyncReport(cluster=cluster.name, success=False)

    try:
        client = build_client(cluster.name)
    except ImproperlyConfigured as exc:
        report.errors.append(f"slurmrestd not configured: {exc}")
        report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
        return report

    # ---- Step 1: Upsert QOS definitions ----
    # QOS records live in slurmdbd and are referenced by the associations
    # created below, so they must exist first. Definitions are global to
    # slurmdbd (not per-cluster); the upsert is idempotent across clusters.
    try:
        _sync_qos_definitions(client)
        report.qos_synced = SlurmQOS.objects.count()
    except Exception as exc:
        report.errors.append(f"QOS sync failed: {exc}")
        report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
        return report

    # ---- Step 2: Create desired entities ----
    # POST /config is an upsert-only endpoint (it does not create), so creates
    # go through the entity endpoints. Order matters: accounts + their
    # account-level parents first (accounts_association add_cond), then user
    # records, then the user-level associations.
    config = _build_config_payload(cluster)
    if config is not None:
        try:
            _create_entities(client, cluster, config, report)
        except Exception as exc:
            report.errors.append(f"Entity creation failed: {exc}")
            report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
            return report

    # ---- Step 3: Sweep Slurm for orphans ----
    _orphan_sweep(client, cluster, report)

    report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
    report.success = len(report.errors) == 0
    return report


def _create_entities(
    client: SlurmClient,
    cluster: SlurmCluster,
    config: dict[str, Any],
    report: SyncReport,
) -> None:
    """Create the desired account/user/association hierarchy in dependency order.

    Accounts + their account-level parents via the accounts_association add_cond
    endpoint (only that endpoint can create the ``user=""`` parent), then user
    records, then user-level associations.
    """
    # 2a. Accounts + account-level parents (add_cond)
    for acct_payload in config.get("accounts", []):
        acct_name = acct_payload["name"]
        account_assoc = next(
            (a for a in config.get("associations", []) if a.get("user") == "" and a.get("account") == acct_name),
            None,
        )
        grptresmins = account_assoc if account_assoc and account_assoc.get("grptresmins") else None
        _create_account_with_parent(
            client,
            cluster,
            acct_name,
            acct_payload.get("description"),
            grptresmins,
            report,
        )

    # 2b. User records
    for user_payload in config.get("users", []):
        client.create_users([user_payload])
        report.users_created += 1

    # 2c. User-level associations
    for assoc_payload in config.get("associations", []):
        if assoc_payload.get("user") == "":
            continue  # account-level parent — handled in 2a
        client.create_associations([assoc_payload])
        report.associations_created += 1


def _orphan_sweep(client: SlurmClient, cluster: SlurmCluster, report: SyncReport) -> None:
    """Delete orphaned associations, users, accounts, and QOS from Slurm.

    Runs in dependency order: orphaned user-level associations first (killing
    the user's running jobs on that account/partition before deleting), then
    orphaned users and accounts, then orphaned QOS definitions.

    Association cleanup is always safe. User/account cleanup is skipped when
    entity creation reported errors, so we never delete a user/account based
    on a possibly-incomplete create. QOS cleanup runs last — a QOS still
    referenced by an association shouldn't be removed before associations are
    reconciled.
    """
    kept_users, kept_accounts = _sweep_orphan_associations(client, cluster, report)

    if report.errors:
        return  # creation may be incomplete — don't delete users/accounts

    _sweep_orphan_users(client, cluster, report, kept_users)
    _sweep_orphan_accounts(client, cluster, report, kept_accounts)

    # QOS definitions are global to slurmdbd; delete ones ColdFront no longer
    # defines. slurmdbd unlinks a QOS from any referencing associations on
    # delete, so this is safe even for non-ColdFront associations.
    _sweep_orphan_qos(client, cluster, report)


def _sweep_orphan_associations(
    client: SlurmClient,
    cluster: SlurmCluster,
    report: SyncReport,
) -> tuple[set[str], set[str]]:
    """Query Slurm associations and delete those not expected by ColdFront.

    Kills the user's running jobs on the (account, partition) before deleting.
    Account-level parents (``user=""``) are always kept — they are the
    hierarchy roots, not tracked per-user in ``expected``. Returns the set of
    users and accounts that still retain a kept (expected) association, so the
    user/account sweeps can follow.
    """
    try:
        existing = client.get_associations(cluster=cluster.name)
    except Exception as exc:
        report.errors.append(f"Failed to query existing associations: {exc}")
        return set(), set()

    expected = _build_expected_tuples(cluster)

    # Users/accounts that still have a kept (expected) user-level association.
    kept_users: set[str] = set()
    kept_accounts: set[str] = set()

    for assoc in existing.get("associations", []):
        acct = assoc.get("account", "")
        user = assoc.get("user", "")
        partition = assoc.get("partition", "")
        if user == "":
            continue  # account-level parent — always kept
        key = (acct, user, partition)
        if key in expected:
            kept_users.add(user)
            kept_accounts.add(acct)
            continue

        # Orphaned: kill running jobs first, then delete the association.
        _kill_user_jobs(client, user, acct, partition)
        report.jobs_killed += 1
        try:
            client.delete_associations(acct, user, cluster.name, partition or None)
            report.associations_deleted += 1
        except Exception as exc:
            report.errors.append(
                f"Failed to delete orphaned association (account={acct}, user={user}, partition={partition}): {exc}"
            )

    # Record the kept sets for the downstream sweeps.
    return kept_users, kept_accounts


def _sweep_orphan_users(
    client: SlurmClient,
    cluster: SlurmCluster,
    report: SyncReport,
    kept_users: set[str],
) -> None:
    """Delete Slurm users ColdFront manages but which no longer have any
    expected association, so they don't linger after association cleanup.

    Scoped to users that exist in the ColdFront ``User`` table — system /
    non-ColdFront users (e.g. root) are never deleted.
    """
    kept_users = kept_users or set()
    try:
        slurm_users = client.get_users()
    except Exception as exc:
        report.errors.append(f"Failed to query existing users: {exc}")
        return

    coldfront_users = {u.username for u in User.objects.all()}
    for u in slurm_users.get("users", []):
        name = u.get("name", "")
        if not name:
            continue
        if name in kept_users:
            continue
        if name not in coldfront_users:
            continue  # system / non-ColdFront user — leave alone
        try:
            client.delete_user(name, cluster.name)
            report.users_deleted += 1
        except Exception as exc:
            report.errors.append(f"Failed to delete orphaned user '{name}': {exc}")


def _sweep_orphan_accounts(
    client: SlurmClient,
    cluster: SlurmCluster,
    report: SyncReport,
    kept_accounts: set[str],
) -> None:
    """Delete Slurm accounts ColdFront manages but which have no kept
    user-level association (only their account-level parent, if any).

    Scoped to accounts that exist as ColdFront ``SlurmAccount`` records for
    this cluster — non-ColdFront accounts (e.g. root) are never deleted.
    """
    kept_accounts = kept_accounts or set()
    try:
        slurm_accounts = client.get_accounts()
    except Exception as exc:
        report.errors.append(f"Failed to query existing accounts: {exc}")
        return

    coldfront_accts = {a.name for a in SlurmAccount.objects.filter(cluster=cluster)}
    for a in slurm_accounts.get("accounts", []):
        name = a.get("name", "")
        if not name:
            continue
        if name in kept_accounts:
            continue
        if name not in coldfront_accts:
            continue  # non-ColdFront account (e.g. root) — leave alone
        try:
            client.delete_account(name, cluster.name)
            report.accounts_deleted += 1
        except Exception as exc:
            report.errors.append(f"Failed to delete orphaned account '{name}': {exc}")


def _sweep_orphan_qos(client: SlurmClient, cluster: SlurmCluster, report: SyncReport) -> None:
    """Delete QOS definitions present in slurmdbd but not in ColdFront."""
    try:
        got = client.get_qos()
    except Exception as exc:
        report.errors.append(f"Failed to query existing QOS: {exc}")
        return

    expected = {q.name for q in SlurmQOS.objects.all()}

    # A QOS referenced by a live association (including system/stock QOS on
    # root associations) must NOT be deleted — removing it can destabilize
    # slurmdbd's association cache and drop its DB connection. Only delete a
    # live QOS that ColdFront neither tracks nor references.
    referenced: set[str] = set()
    try:
        existing = client.get_associations(cluster=cluster.name)
    except Exception as exc:
        report.errors.append(f"Failed to query associations for QOS sweep: {exc}")
        return
    for a in existing.get("associations", []):
        for q in a.get("qos", []):
            if isinstance(q, dict):
                referenced.add(q.get("name", ""))
            else:
                referenced.add(str(q))
        default = a.get("default", {}) or {}
        if default.get("qos"):
            referenced.add(str(default["qos"]))

    for q in got.get("qos", []):
        name = q.get("name", "")
        if not name:
            continue
        if name in expected:
            continue
        if name in referenced:
            continue
        try:
            client.delete_qos(name)
            report.qos_deleted += 1
        except Exception as exc:
            report.errors.append(f"Failed to delete orphaned QOS '{name}': {exc}")


# ---------------------------------------------------------------------------
# QOS definition sync
# ---------------------------------------------------------------------------


def _sync_qos_definitions(client: SlurmClient) -> None:
    """Upsert every SlurmQOS definition into slurmdbd.

    QOS records are global to slurmdbd (they are not tied to one cluster) and
    are referenced by the associations the access-control sync creates, so
    they are pushed before the account/association entities. The upsert is
    idempotent: existing records are updated, missing ones are created.
    """
    payloads = [_serialize_qos_record(q) for q in SlurmQOS.objects.all()]
    if payloads:
        client.upsert_qos(payloads)


def _serialize_qos_record(qos: SlurmQOS) -> dict[str, Any]:
    """Map a SlurmQOS record to the REST ``qos_rec`` wire format."""
    max_wall = qos.max_wall_duration_per_job
    max_wall_minutes = max_wall.to_minutes() if max_wall is not None else None
    return SlurmClient.serialize_qos(
        name=qos.name,
        description=qos.description or None,
        priority=qos.priority,
        limit_factor=qos.limit_factor,
        max_submit_jobs_per_user=qos.max_submit_jobs_per_user,
        max_jobs_per_user=qos.max_jobs_per_user,
        max_submit_jobs_per_account=qos.max_submit_jobs_per_account,
        max_jobs_per_account=qos.max_jobs_per_account,
        max_wall_duration_per_job=max_wall_minutes,
        grace_time=qos.grace_time,
    )


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def _ensure_slurm_users_for_cluster(cluster: SlurmCluster) -> None:
    """Create/reconcile a ColdFront ``SlurmUser`` record for each member of an
    active association on the cluster.

    ``default_account`` follows first-account-wins per user (mirrors the
    listener's ``_sync_slurm_users_for_user`` semantics). Existing records are
    updated when their ``default_account`` differs, so a ``slurm_account``
    change on an active allocation propagates on the batch path.
    """
    active = get_active_associations(cluster)

    # user pk -> (user instance, default account); first account wins.
    user_accounts: dict[int, tuple[Any, SlurmAccount]] = {}
    for a in active:
        allocation = a.allocation
        if not allocation or not allocation.project:
            continue
        for pu in allocation.project.users.all():
            if pu.user:
                user_accounts.setdefault(pu.user.pk, (pu.user, a.slurm_account))

    for user, slurm_account in user_accounts.values():
        su, _ = SlurmUser.objects.get_or_create(
            user=user,
            cluster=cluster,
            defaults={"default_account": slurm_account},
        )
        if su.default_account != slurm_account:
            su.default_account = slurm_account
            su.save()


def _build_config_payload(cluster: SlurmCluster) -> dict[str, Any] | None:
    """Build the full ``openapi_slurmdbd_config_resp`` payload for a cluster.

    Returns ``None`` if the cluster has no active associations.
    """
    active = get_active_associations(cluster)
    if not active:
        return None

    # Collect unique accounts
    account_ids = set()
    for a in active:
        if a.slurm_account_id:
            account_ids.add(a.slurm_account_id)

    accounts = SlurmAccount.objects.filter(pk__in=account_ids)

    # Collect unique users across all project members
    user_set: set[int] = set()
    for a in active:
        allocation = a.allocation
        if allocation and allocation.project:
            for pu in allocation.project.users.all():
                if pu.user:
                    user_set.add(pu.user.pk)

    users = SlurmUser.objects.filter(
        cluster=cluster,
        user_id__in=user_set,
    ).select_related("user", "default_account")

    # Build association payloads
    assoc_payloads = []
    for a in active:
        allocation = a.allocation
        if not allocation:
            continue
        resource = allocation.resource_object
        if resource is None:
            continue

        for pu in allocation.project.users.all():
            if not pu.user:
                continue
            assoc_payloads.append(_build_assoc_payload(a, pu.user, cluster, resource))

    # Build account payloads
    account_payloads = [
        {
            "name": acct.name,
            "description": acct.description or "",
        }
        for acct in accounts
    ]

    # Account-level (parent) associations — always emitted so the hierarchy
    # exists (a user-level assoc is silently dropped without its parent).
    # GrpTresMins (SU grant) is attached only when enforcement is on.
    for acct in accounts:
        account_assoc: dict[str, Any] = {
            "account": acct.name,
            "user": "",
            "cluster": cluster.name,
            "partition": "",
        }
        grptresmins = _build_account_assoc_payload(acct, cluster)
        if grptresmins:
            account_assoc["grptresmins"] = grptresmins["grptresmins"]
        assoc_payloads.append(account_assoc)

    # Build user payloads
    user_payloads = []
    for su in users:
        user_payloads.append(
            {
                "name": su.user.username,
                "default": {
                    "account": su.default_account.name,
                    "wckey": su.default_wckey or "",
                },
            }
        )

    return {
        "accounts": account_payloads,
        "users": user_payloads,
        "associations": assoc_payloads,
    }


def _build_effective_qos(
    account: SlurmAccount | None,
    association: SlurmAssociation,
) -> list[str] | None:
    """
    Compute the effective QOS list for an association by merging
    account-level and association-level qos_add/qos_remove.

    The effective list is:
        (account_qos_add ∪ assoc_qos_add) ∖ (account_qos_remove ∪ assoc_qos_remove)

    Returns ``None`` if both sources have no QOS add/remove entries.
    """
    qos_add_names: set[str] = set()
    qos_remove_names: set[str] = set()

    # Account-level QOS
    if account:
        qos_add_names.update(q.name for q in account.qos_add.all())
        qos_remove_names.update(q.name for q in account.qos_remove.all())

    # Association-level QOS
    qos_add_names.update(q.name for q in association.qos_add.all())
    qos_remove_names.update(q.name for q in association.qos_remove.all())

    # Compute effective list
    effective = list(qos_add_names - qos_remove_names)
    return effective if effective else None


def _build_assoc_payload(
    association: SlurmAssociation,
    user: Any,
    cluster: SlurmCluster,
    resource: SlurmCluster | SlurmPartition,
) -> dict[str, Any]:
    """Build a nested ``assoc`` payload entry from ColdFront models. Delegate to
    :meth:`SlurmClient.serialize_association` so the wire format stays in one
    place.
    """
    slurm_account = association.slurm_account
    partition_name = resource.name if isinstance(resource, SlurmPartition) else ""

    # QOS add/remove — merge account-level and association-level
    qoslevel = _build_effective_qos(slurm_account, association)

    max_wall_duration_per_job: int | None = None
    if association.max_wall_duration_per_job is not None:
        # SlurmTime; the API wants whole minutes. UNLIMITED is skipped.
        max_wall_duration_per_job = association.max_wall_duration_per_job.to_minutes()

    return SlurmClient.serialize_association(
        account=slurm_account.name if slurm_account else "",
        user=user.username,
        cluster=cluster.name,
        partition=partition_name,
        default_qos=association.default_qos.name if association.default_qos else None,
        parent=association.parent.name if association.parent else None,
        fairshare=association.fairshare,
        max_jobs=association.max_jobs,
        max_submit_jobs=association.max_submit_jobs,
        max_tres_per_job=association.max_tres_per_job,
        max_tres_mins_per_job=association.max_tres_mins_per_job,
        max_wall_duration_per_job=max_wall_duration_per_job,
        qoslevel=qoslevel,
    )


def _build_account_assoc_payload(
    account: SlurmAccount,
    cluster: SlurmCluster,
) -> dict[str, Any] | None:
    """Build the ``assoc_rec_set`` GrpTresMins grant for an account.

    GrpTresMins is an association-level field; an account's SU grant is
    stored on the account-level association (``user=""``). Returns the
    ``grptresmins`` entry only when the cluster enforces SU limits and the
    account has a service_units grant.

    The value is a ``tres_list`` array (``[{"type": "billing", "count": N}]``) —
    the live API rejects the dict form with ``9208 Data parser expected a list``.
    Returns None when enforcement is off or the grant is unset.
    """
    if not cluster.enforce_su_limits or not account.service_units:
        return None
    return {"grptresmins": [{"type": "billing", "count": account.service_units * 60}]}


def _create_account_with_parent(
    client: SlurmClient,
    cluster: SlurmCluster,
    name: str,
    description: str,
    grptresmins: dict[str, Any] | None,
    report: SyncReport,
) -> None:
    """Create an account and its account-level (parent) association in one call.

    Only the accounts_association add_cond endpoint can create the account-
    level parent (user=""); the parent is required for any user-level
    association below. GrpTresMins (SU grant) is folded in when provided.
    """
    account_assoc = {"grptresmins": grptresmins["grptresmins"]} if grptresmins else None
    try:
        client.create_accounts_with_associations(
            client.serialize_accounts_add_cond(
                accounts=[name],
                clusters=[cluster.name],
                description=description,
                association=account_assoc,
            )
        )
        report.accounts_created += 1
    except Exception as exc:
        report.errors.append(f"Failed to create account '{name}': {exc}")


def _build_expected_tuples(cluster: SlurmCluster) -> set[tuple[str, str, str]]:
    """Build set of ``(account, user, partition)`` tuples expected in Slurm.

    Only includes active allocations with a non-null slurm_account.
    """
    expected: set[tuple[str, str, str]] = set()
    for a in get_active_associations(cluster):
        acct = a.slurm_account
        if acct is None:
            continue
        allocation = a.allocation
        if not allocation:
            continue
        resource = allocation.resource_object
        if resource is None:
            continue
        partition = resource.name if isinstance(resource, SlurmPartition) else ""
        for pu in allocation.project.users.all():
            if pu.user:
                expected.add((acct.name, pu.user.username, partition))
    return expected


def _kill_user_jobs(
    client: SlurmClient,
    user_name: str,
    account_name: str,
    partition_name: str,
) -> None:
    """Kill all running jobs for a user on a given account+partition."""
    kill_msg: dict[str, Any] = {
        "user_name": user_name,
        "account": account_name,
        "signal": "SIGTERM",
    }
    if partition_name:
        kill_msg["partition"] = partition_name
    try:
        client.kill_jobs(kill_msg)
    except Exception as exc:
        logger.warning(
            "Failed to kill jobs for user %s account %s partition '%s': %s",
            user_name,
            account_name,
            partition_name,
            exc,
        )
