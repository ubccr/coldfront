# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Slurm association flat-file dump generation.

Renders the Slurm association dump format consumed by ``sacctmgr`` — the
``Cluster`` / ``Account`` / ``User`` hierarchy lines — from ColdFront records.
"""

from coldfront.slurm.choices import SlurmAdminLevelChoices
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.slurm.utils import get_active_associations


def generate_association_dump(cluster: SlurmCluster) -> str:
    """Generate the Slurm association dump content for a given cluster.

    The dump format follows the Slurm dump file format used by sacctmgr:
      - Cluster header line
      - Parent/Account hierarchy lines
      - User lines under each account

    Only active allocations (STATUS_ACTIVE) contribute associations.
    Accounts with no active associations are excluded.
    """
    lines = []

    # -- QOS definitions (global to slurmdbd) --
    qos_objects = list(SlurmQOS.objects.all())
    for qos in qos_objects:
        qos_line = _format_qos(qos)
        if qos_line:
            lines.append(qos_line)
    if qos_objects:
        lines.append("")

    # -- Cluster header --
    cluster_line = _format_cluster(cluster)
    lines.append(cluster_line)
    lines.append("")

    # -- Root user (slurm default administrator) --
    lines.append("Parent - 'root'")
    lines.append("User - 'root':DefaultAccount='root':AdminLevel='Administrator':Fairshare=1")
    lines.append("")

    # -- SlurmAccounts with active associations --
    active_assocs = get_active_associations(cluster)
    accounts_with_assocs = _get_accounts_for_assocs(active_assocs)

    for account in accounts_with_assocs:
        # Find the first association for this account to determine parent
        account_assocs = [a for a in active_assocs if a.slurm_account_id == account.pk]
        if not account_assocs:
            continue

        # Parent line: from association's parent account, or root
        parent_account = account_assocs[0].parent
        if parent_account:
            parent_name = parent_account.name
        else:
            parent_name = "root"
        lines.append(f"Parent - '{parent_name}'")

        # Account line
        account_line = _format_account(account, cluster)
        lines.append(account_line)

        # sacctmgr attaches a User line's association to the current Parent -
        # line, not the preceding Account - line. Emit Parent - '<account>' so
        # this account's user lines land under it (mirrors the real dump's
        # recursive Parent/children structure).
        lines.append(f"Parent - '{account.name}'")

        # User lines for associations under this account
        for assoc in account_assocs:
            user_lines = _format_user_lines(assoc, cluster)
            lines.extend(user_lines)

        lines.append("")

    return "\n".join(lines)


def _format_cluster(cluster: SlurmCluster) -> str:
    """Format the Cluster header line."""
    parts = [f"Cluster - '{cluster.name}'"]

    # Default QOS
    if cluster.default_qos:
        parts.append(f"DefaultQOS='{cluster.default_qos.name}'")

    # Fairshare
    parts.append(f"Fairshare={cluster.fairshare}")

    # QOS list — absolute assignment since cluster is the root
    qos_names = _get_qos_names(cluster.qos_list.all())
    if qos_names:
        parts.append(f"QOS='{','.join(qos_names)}'")

    return ":".join(parts)


def _format_qos(qos: SlurmQOS) -> str:
    """Format a QOS definition line."""
    parts = [f"QOS - '{qos.name}'"]

    # Description (inherited from OrganizationalModel)
    if qos.description:
        parts.append(f"Description='{qos.description}'")

    # Priority
    if qos.priority is not None:
        parts.append(f"Priority={qos.priority}")

    # MaxSubmitJobsPU
    if qos.max_submit_jobs_per_user is not None:
        parts.append(f"MaxSubmitJobsPU={qos.max_submit_jobs_per_user}")

    # MaxJobsPU
    if qos.max_jobs_per_user is not None:
        parts.append(f"MaxJobsPU={qos.max_jobs_per_user}")

    # MaxSubmitJobsPA
    if qos.max_submit_jobs_per_account is not None:
        parts.append(f"MaxSubmitJobsPA={qos.max_submit_jobs_per_account}")

    # MaxJobsPA
    if qos.max_jobs_per_account is not None:
        parts.append(f"MaxJobsPA={qos.max_jobs_per_account}")

    # MaxWallDurationPerJob
    if qos.max_wall_duration_per_job is not None:
        seconds = qos.max_wall_duration_per_job.to_seconds()
        if seconds is not None:
            parts.append(f"MaxWallDurationPerJob={seconds}")

    # LimitFactor
    if qos.limit_factor is not None:
        parts.append(f"LimitFactor={qos.limit_factor}")

    # GraceTime
    if qos.grace_time is not None:
        parts.append(f"GraceTime={qos.grace_time}")

    return ":".join(parts)


def _format_account(account: SlurmAccount, cluster: SlurmCluster) -> str:
    """Format an Account line.

    Args:
        account: SlurmAccount to format.
        cluster: The SlurmCluster the account belongs to (used for the
            enforce_su_limits gate).
    """
    parts = [f"Account - '{account.name}'"]

    # Fairshare — only include if set
    if account.fairshare is not None:
        parts.append(f"Fairshare={account.fairshare}")

    # SU enforcement — GrpTresMins=billing on the account association
    if cluster.enforce_su_limits and account.service_units:
        parts.append(f"GrpTresMins=billing={account.service_units * 60}")

    # QOS add/remove — combined +/- format
    qos_add_names = _get_qos_names(account.qos_add.all())
    qos_remove_names = _get_qos_names(account.qos_remove.all())
    if qos_add_names or qos_remove_names:
        qos_items = [f"+{n}" for n in qos_add_names] + [f"-{n}" for n in qos_remove_names]
        parts.append(f"QOS='{','.join(qos_items)}'")

    return ":".join(parts)


def _format_user_lines(assoc: SlurmAssociation, cluster: SlurmCluster) -> list[str]:
    """
    Format User lines for a given association.

    Generates one line per project user in the allocation's project.
    """
    lines = []
    allocation = assoc.allocation
    if not allocation:
        return lines

    project = allocation.project
    if not project:
        return lines

    # Determine resource and QOS list
    resource = allocation.resource_object
    if resource is None:
        return lines

    # Get allowed QOS list from partition or cluster
    if isinstance(resource, SlurmPartition):
        qos_list = resource.allow_qos.all()
        partition_name = resource.name
    elif isinstance(resource, SlurmCluster):
        qos_list = resource.qos_list.all()
        partition_name = None
    else:
        # Non-slurm resource — skip
        return lines

    qos_names = _get_qos_names(qos_list)

    # Fairshare logic: if account has fairshare, users inherit via parent
    account = assoc.slurm_account
    if account and account.fairshare is not None:
        fairshare_value = "parent"
    else:
        fairshare_value = assoc.fairshare

    # Get project users
    project_users = project.users.all()

    for pu in project_users:
        user = pu.user
        if not user:
            continue

        # Look up SlurmUser for this user+cluster
        slurm_user = _get_slurm_user(user, cluster)

        # Default account: from SlurmUser, fall back to association account
        if slurm_user and slurm_user.default_account:
            default_acct_name = slurm_user.default_account.name
        elif account:
            default_acct_name = account.name
        else:
            default_acct_name = "root"

        # Build user line
        parts = [f"User - '{user.username}'"]
        parts.append(f"DefaultAccount='{default_acct_name}'")

        # Partition (only if targeting a specific partition)
        if partition_name:
            parts.append(f"Partition='{partition_name}'")

        # Fairshare
        parts.append(f"Fairshare={fairshare_value}")

        # Default QOS from the association
        if assoc.default_qos:
            parts.append(f"DefaultQOS='{assoc.default_qos.name}'")

        # QOS list — combine partition allow_qos with association add/remove
        qos_add_names = _get_qos_names(assoc.qos_add.all())
        qos_remove_names = _get_qos_names(assoc.qos_remove.all())

        if qos_names or qos_add_names or qos_remove_names:
            # Build combined QOS string with + prefix for add, - prefix for remove
            qos_parts = []
            for qn in qos_names:
                qos_parts.append(f"+{qn}")
            for qn in qos_add_names:
                qos_parts.append(f"+{qn}")
            for qn in qos_remove_names:
                qos_parts.append(f"-{qn}")
            parts.append(f"QOS='{','.join(qos_parts)}'")

        # Limits from association
        limits = _format_limits(assoc)
        if limits:
            parts.extend(limits)

        # Admin level and default WCKey from SlurmUser
        if slurm_user:
            if slurm_user.admin_level and slurm_user.admin_level > 0:
                # Map numeric admin level to Slurm dump string format
                admin_map = {
                    SlurmAdminLevelChoices.LEVEL_NONE: "None",
                    SlurmAdminLevelChoices.LEVEL_OPERATOR: "Operator",
                    SlurmAdminLevelChoices.LEVEL_ADMIN: "Administrator",
                }
                admin_str = admin_map.get(slurm_user.admin_level, "")
                if admin_str:
                    parts.append(f"AdminLevel='{admin_str}'")
            if slurm_user.default_wckey:
                parts.append(f"DefaultWCKey='{slurm_user.default_wckey}'")

        lines.append(":".join(parts))

    return lines


def _get_slurm_user(user, cluster: SlurmCluster) -> SlurmUser | None:
    """Get SlurmUser for the given user and cluster, or None."""
    try:
        return SlurmUser.objects.get(user=user, cluster=cluster)
    except SlurmUser.DoesNotExist:
        return None


def _get_qos_names(qos_list) -> list[str]:
    """Return a list of QOS names from a queryset."""
    return [qos.name for qos in qos_list]


def _format_limits(assoc: SlurmAssociation) -> list[str]:
    """Format limit fields from a SlurmAssociation into key=value parts."""
    parts = []

    if assoc.max_jobs is not None:
        parts.append(f"MaxJobs={assoc.max_jobs}")

    if assoc.max_submit_jobs is not None:
        parts.append(f"MaxSubmitJobs={assoc.max_submit_jobs}")

    if assoc.max_tres_per_job is not None and assoc.max_tres_per_job != "":
        parts.append(f"MaxTRESPerJob={assoc.max_tres_per_job}")

    if assoc.max_tres_mins_per_job is not None and assoc.max_tres_mins_per_job != "":
        parts.append(f"MaxTRESMinsPerJob={assoc.max_tres_mins_per_job}")

    if assoc.max_wall_duration_per_job is not None:
        # SlurmTime; convert to whole seconds for Slurm. UNLIMITED is skipped.
        seconds = assoc.max_wall_duration_per_job.to_seconds()
        if seconds is not None:
            parts.append(f"MaxWallDurationPerJob={seconds}")

    return parts


def _get_accounts_for_assocs(assocs) -> list[SlurmAccount]:
    """
    Get unique SlurmAccounts referenced by the given associations,
    preserving the order they first appear.
    """
    seen = set()
    accounts = []
    for a in assocs:
        acct = a.slurm_account
        if acct and acct.pk not in seen:
            seen.add(acct.pk)
            accounts.append(acct)
    return accounts
