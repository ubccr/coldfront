# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Partition-config generation from ColdFront records and the live REST API.

Renders the ``PartitionName`` sections of slurm.conf from ColdFront's
``SlurmPartition`` records, optionally merged with the running partition
config fetched from ``GET /partitions/``.

DEFAULT is absorbed into each partition at import time (see
``coldfront.slurm.parser``), so every partition section is self-contained —
no ``PartitionName=DEFAULT`` template line is emitted.

Parity: ColdFront's effective partition model matches the REST ``/partitions``
config shape. We do NOT match arbitrary slurm.conf authoring styles
(DEFAULT-as-template headers, ``NodeName``/``NodeSet`` sections, node-range
lists, etc.) — we output the partition sections we can produce from
ColdFront's records, overlaid on the running config.
"""

from typing import Any

from coldfront.slurm.models import SlurmCluster, SlurmPartition
from coldfront.slurm.parser import format_slurm_time

# ---------------------------------------------------------------------------
# Canonical slurm.conf subparam order for PartitionName sections.
# ---------------------------------------------------------------------------
_CANONICAL_SUBPARAMS: list[str] = [
    "PartitionName",
    "Nodes",
    "NodeSets",
    "AllowAccounts",
    "AllowGroups",
    "AllowQOS",
    "DenyQOS",
    "QOS",
    "Default",
    "MaxTime",
    "DefaultTime",
    "Priority",
    "PriorityTier",
    "MaxNodes",
    "MaxCPUsPerNode",
    "MaxCPUsPerSocket",
    "MinNodes",
    "DefMemPerCPU",
    "DefMemPerNode",
    "PreemptMode",
    "State",
    "TRESBillingWeights",
    "GraceTime",
    "Alternate",
    "Topology",
    "OverTimeLimit",
    "OverSubscribe",
    "JobDefaults",
    "SuspendTime",
    "ResumeTimeout",
    "SuspendTimeout",
]

# REST partition_info path -> slurm.conf subparam.
# Derived from the authoritative PARTITION_INFO array in
# src/plugins/data_parser/v0.0.45/parsers.c. Removed raws
# (defaults/memory_per_cpu, maximums/memory_per_cpu, maximums/shares,
# maximums/oversubscribe/*) and read-only computed fields (cluster,
# select_type, cpus/*, nodes/total, tres/configured, partition/exclusive)
# are excluded — they are not slurm.conf keys.
_REST_TO_SUBPARAM: dict[str, str] = {
    "name": "PartitionName",
    "nodes/configured": "Nodes",
    "node_sets": "NodeSets",
    "accounts/allowed": "AllowAccounts",
    "groups/allowed": "AllowGroups",
    "qos/allowed": "AllowQOS",
    "qos/deny": "DenyQOS",
    "qos/assigned": "QOS",
    "maximums/time": "MaxTime",
    "defaults/time": "DefaultTime",
    "priority/job_factor": "Priority",
    "priority/tier": "PriorityTier",
    "maximums/nodes": "MaxNodes",
    "maximums/cpus_per_node": "MaxCPUsPerNode",
    "maximums/cpus_per_socket": "MaxCPUsPerSocket",
    "minimums/nodes": "MinNodes",
    "defaults/partition_memory_per_cpu": "DefMemPerCPU",
    "defaults/partition_memory_per_node": "DefMemPerNode",
    "preempt_mode": "PreemptMode",
    "tres/billing_weights": "TRESBillingWeights",
    "grace_time": "GraceTime",
    "alternate": "Alternate",
    "topology": "Topology",
    "maximums/over_time_limit": "OverTimeLimit",
    "partition/oversubscribe": "OverSubscribe",
    "defaults/job": "JobDefaults",
    "suspend_time": "SuspendTime",
    "timeouts/resume": "ResumeTimeout",
    "timeouts/suspend": "SuspendTimeout",
}

# ---------------------------------------------------------------------------
# Fetch running partition config from the REST API
# ---------------------------------------------------------------------------


def _rest_value(part: dict[str, Any], path: str) -> Any:
    """Walk a dotted ``path`` (``a/b``) into the partition dict."""
    node: Any = part
    for key in path.split("/"):
        if isinstance(node, dict):
            node = node.get(key)
        else:
            return None
    return node


def _normalize_rest_value(value: Any) -> str:
    """Normalize a REST partition_info leaf value to a canonical string.

    Handles:
    - ``UINT*_NO_VAL`` structs ``{"set", "infinite", "number"}``:
      infinite -> "UNLIMITED"; set with number>0 -> str(number); else "".
    - flag-bit arrays (lists of strings): join with commas.
    - scalar wrappers (dicts keyed by a single field name).
    - scalars and bools.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, list):
        strs = [str(v) for v in value if v is not None]
        return ",".join(strs) if strs else ""
    if isinstance(value, dict):
        # UINT*_NO_VAL structs (times/limits carry set/infinite/number).
        if "infinite" in value or "set" in value:
            if value.get("infinite"):
                return "UNLIMITED"
            if value.get("set"):
                number = value.get("number")
                if number:
                    return str(number)
                # number == 0 is "unset" for mem/limit fields — omit it
                # (avoids rendering DefMemPerNode=0 artifacts).
                return ""
            return ""
        # Single-key scalar wrapper (e.g. {"state": "UP"}).
        if len(value) == 1:
            for inner in value.values():
                if inner is not None:
                    return _normalize_rest_value(inner)
        return ""
    return str(value)


def fetch_partition_config(client: Any) -> list[dict[str, Any]]:
    """Fetch the running partition config from the REST API.

    Args:
        client: A SlurmClient with a discovered version.

    Returns:
        A list of canonical partition-section dicts keyed by slurm.conf
        subparam, one per partition reported by ``GET /partitions/``.
    """
    body = client.get_partitions()
    sections: list[dict[str, Any]] = []
    for part in body.get("partitions", []):
        if not isinstance(part, dict):
            continue
        section: dict[str, Any] = {}
        for path, subparam in _REST_TO_SUBPARAM.items():
            value = _normalize_rest_value(_rest_value(part, path))
            if value:
                section[subparam] = value
        # Default flag from the flags list.
        flags = part.get("flags", [])
        default = any(
            isinstance(f, str) and f.upper() == "DEFAULT" for f in (flags if isinstance(flags, list) else [flags])
        )
        section["Default"] = "YES" if default else "NO"
        # State from partition/state.
        state = _normalize_rest_value(_rest_value(part, "partition/state"))
        if state:
            section["State"] = state
        sections.append(section)
    return sections


# ---------------------------------------------------------------------------
# Build canonical sections from ColdFront DB records
# ---------------------------------------------------------------------------


def _tres_weights_string(weights: dict[str, Any]) -> str:
    """Render a TRESBillingWeights dict back to ``CPU=1.0,Node=3.0``."""
    parts: list[str] = []
    for tres, weight in weights.items():
        if weight is None:
            continue
        parts.append(f"{tres}={weight}")
    return ",".join(parts)


def _names(qs: Any) -> str:
    return ",".join(sorted(str(obj.name) for obj in qs.all()))


def _db_section(partition: SlurmPartition) -> dict[str, Any]:
    """Build the canonical section dict from a SlurmPartition record."""
    section: dict[str, Any] = {"PartitionName": partition.name}
    if partition.nodes:
        section["Nodes"] = partition.nodes

    allow_qos = _names(partition.allow_qos.all())
    if allow_qos:
        section["AllowQOS"] = allow_qos
    deny_qos = _names(partition.deny_qos.all())
    if deny_qos:
        section["DenyQOS"] = deny_qos
    allow_groups = _names(partition.allow_groups.all())
    if allow_groups:
        section["AllowGroups"] = allow_groups
    allow_accounts = _names(partition.allow_accounts.all())
    if allow_accounts:
        section["AllowAccounts"] = allow_accounts
    if partition.qos:
        section["QOS"] = partition.qos.name

    if partition.is_default:
        section["Default"] = "YES"

    if partition.max_time is not None:
        section["MaxTime"] = format_slurm_time(partition.max_time)
    if partition.default_time is not None:
        section["DefaultTime"] = format_slurm_time(partition.default_time)

    if partition.priority is not None:
        section["Priority"] = str(partition.priority)
    if partition.priority_tier is not None:
        section["PriorityTier"] = str(partition.priority_tier)
    if partition.max_nodes is not None:
        section["MaxNodes"] = str(partition.max_nodes)
    if partition.max_cpus_per_node is not None:
        section["MaxCPUsPerNode"] = str(partition.max_cpus_per_node)
    if partition.def_mem_per_cpu is not None:
        section["DefMemPerCPU"] = str(partition.def_mem_per_cpu)
    if partition.def_mem_per_node is not None:
        section["DefMemPerNode"] = str(partition.def_mem_per_node)

    if partition.preempt_mode:
        section["PreemptMode"] = str(partition.preempt_mode).upper()
    if partition.state:
        section["State"] = str(partition.state).upper()
    if partition.tres_billing_weights:
        section["TRESBillingWeights"] = _tres_weights_string(partition.tres_billing_weights)
    return section


def db_partition_config(cluster: SlurmCluster) -> list[dict[str, Any]]:
    """Build canonical partition-section dicts from ColdFront DB records."""
    return [_db_section(p) for p in cluster.partitions.all()]


# ---------------------------------------------------------------------------
# Merge DB records over the running baseline
# ---------------------------------------------------------------------------


def merge_partition_config(
    db_sections: list[dict[str, Any]],
    running_sections: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    """Merge DB partition sections over the running baseline.

    Rule: a DB subparam that is present (non-empty) AND differs from the
    running value wins and is marked changed; otherwise the running value is
    kept. Partitions present in only one source are taken from that source
    (DB-only partitions mark all their keys as changed).

    Returns ``(merged, changed)`` where ``changed[name]`` is the set of
    subparams the DB explicitly overrode (or added for DB-only partitions).
    """
    running_by_name = {s["PartitionName"]: s for s in running_sections}
    db_by_name = {s["PartitionName"]: s for s in db_sections}

    merged: list[dict[str, Any]] = []
    changed: dict[str, set[str]] = {}

    for name in sorted(set(running_by_name) | set(db_by_name)):
        running = running_by_name.get(name)
        db = db_by_name.get(name)

        if running is not None:
            section = dict(running)
        else:
            section = {}

        if db is not None:
            for key, value in db.items():
                running_value = running.get(key) if running is not None else ""
                if value != "" and value != running_value:
                    section[key] = value
                    changed.setdefault(name, set()).add(key)
                elif key not in section:
                    section[key] = value
                    # DB-only partition keys (or keys running omits).
                    changed.setdefault(name, set()).add(key)

        merged.append(section)

    return merged, changed


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def diff_partition_config(
    merged: list[dict[str, Any]],
    running_sections: list[dict[str, Any]],
) -> dict[str, dict[str, tuple[Any, Any]]]:
    """Structured per-partition, per-field diff of merged vs running.

    Returns ``{name: {subparam: (running_value, merged_value)}}`` for every
    key where the merged section differs from the running baseline.
    """
    running_by_name = {s["PartitionName"]: s for s in running_sections}
    diffs: dict[str, dict[str, tuple[Any, Any]]] = {}
    for section in merged:
        name = section["PartitionName"]
        running = running_by_name.get(name, {})
        for key, value in section.items():
            running_value = running.get(key, "")
            if value != running_value:
                diffs.setdefault(name, {})[key] = (running_value, value)
    return diffs


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render_partition_section(section: dict[str, Any]) -> str:
    """Render a canonical partition-section dict as a PartitionName line."""
    parts: list[str] = []
    for key in _CANONICAL_SUBPARAMS:
        value = section.get(key)
        if value is None or value == "":
            continue
        parts.append(f"{key}={value}")
    return " ".join(parts)


def render_partition_config(sections: list[dict[str, Any]]) -> list[str]:
    """Render canonical sections to a list of PartitionName lines."""
    return [render_partition_section(s) for s in sections]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def generate_partition_config(
    cluster: SlurmCluster,
    client: Any = None,
) -> dict[str, Any]:
    """Generate partition-config sections for ``cluster``.

    Args:
        cluster: The SlurmCluster whose partitions to render.
        client: Optional SlurmClient used to fetch the running config. When
            None (or fetch fails), falls back to DB-only rendering.

    Returns:
        A dict with ``sections`` (list of PartitionName lines), ``diff``
        (structured changes vs running), ``source`` ("merged" or "db") and
        ``error`` (fetch error message, only when source == "db").
    """
    db_sections = db_partition_config(cluster)
    if client is None:
        return {
            "sections": render_partition_config(db_sections),
            "diff": {},
            "source": "db",
            "error": "",
        }
    try:
        running_sections = fetch_partition_config(client)
    except Exception as exc:  # noqa: BLE001 - fall back to DB-only
        return {
            "sections": render_partition_config(db_sections),
            "diff": {},
            "source": "db",
            "error": str(exc),
        }
    merged, changed = merge_partition_config(db_sections, running_sections)
    diffs = diff_partition_config(merged, running_sections)
    return {
        "sections": render_partition_config(merged),
        "diff": diffs,
        "source": "merged",
        "error": "",
    }
