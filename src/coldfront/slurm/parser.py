# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re
from dataclasses import dataclass, field

from coldfront.slurm.choices import SlurmPartitionStateChoices, SlurmPreemptModeChoices

# ---------------------------------------------------------------------------
# slurm.conf parsing utilities
# ---------------------------------------------------------------------------


@dataclass
class ParsedPartition:
    """Parsed partition from a slurm.conf PartitionName line."""

    name: str
    nodes: str = ""
    priority: int | None = None
    is_default: bool = False
    default_time: str | None = None
    max_time: str | None = None
    state: str = "UP"
    preempt_mode: str = ""
    def_mem_per_cpu: int | None = None
    allow_qos: str = ""
    qos: str = ""
    allow_accounts: str = ""
    allow_groups: str = ""
    tres_billing_weights: str = ""


@dataclass
class ParsedNode:
    """Parsed node from a slurm.conf NodeName line."""

    name: str
    features: str = ""
    gres: str = ""
    cpus: int | None = None
    real_memory: int | None = None
    sockets: int | None = None
    cores_per_socket: int | None = None
    threads_per_core: int | None = None


@dataclass
class ParsedSlurmConfig:
    """Parsed slurm.conf file contents."""

    cluster_name: str = ""
    partitions: list[ParsedPartition] = field(default_factory=list)
    nodes: list[ParsedNode] = field(default_factory=list)
    qos_names: set[str] = field(default_factory=set)

    # Global SU billing TRES settings (1-1 to slurm.conf keys)
    priority_flags: str = ""
    priority_type: str = ""
    priority_decay_half_life: str = ""
    priority_usage_reset_period: str = ""
    default_tres_billing_weights: str = ""


# Regex for slurm.conf key=value lines
_CONF_LINE_RE = re.compile(r"^(\w+)\s*=\s*(.*)$")

# Known array-type keys in slurm.conf that span multiple lines
_ARRAY_KEYS = {"PartitionName", "NodeName"}


def _parse_conf_value(value: str) -> str:
    """Strip surrounding quotes and whitespace from a config value."""
    value = value.strip()
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value


def parse_tres_weights(raw: str) -> dict[str, float]:
    """Parse a TRESBillingWeights value into a dict of TRES -> weight.

    Handles formats like ``CPU=1.0,Mem=0.25G,gres/gpu=2.0``. An empty
    string returns an empty dict (effective {"CPU": 1.0}).
    """
    if not raw:
        return {}
    weights: dict[str, float] = {}
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            continue
        name, val = token.split("=", 1)
        val = val.strip()
        # Strip a trailing unit suffix (K/M/G/T) used by Slurm for Mem/FS etc.
        if val and not val[-1].isdigit():
            val = val[:-1]
        try:
            weights[name.strip()] = float(val)
        except ValueError:
            continue
    return weights


def _parse_conf_key_value(line: str) -> tuple[str, str] | None:
    """Parse a single key=value line from slurm.conf.

    Returns (key, raw_value) or None if the line is a comment/blank.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    m = _CONF_LINE_RE.match(stripped)
    if not m:
        return None
    return m.group(1), m.group(2)


def parse_slurm_conf(filepath: str) -> ParsedSlurmConfig:
    """Parse a slurm.conf file into a :class:`ParsedSlurmConfig`.

    Args:
        filepath: Path to the slurm.conf file.

    Returns:
        A ParsedSlurmConfig with cluster name, partitions, nodes, and QOS names.
    """
    result = ParsedSlurmConfig()

    # Read and join continuations
    lines = _read_slurm_conf(filepath)

    # Track current partition default values (PartitionName=DEFAULT ...)
    partition_defaults: dict[str, str] = {}
    node_defaults: dict[str, str] = {}

    # Track PartitionName and NodeName multi-line arrays
    partition_buffer: list[str] = []
    node_buffer: list[str] = []

    for line in lines:
        kv = _parse_conf_key_value(line)
        if kv is None:
            continue

        key, raw_value = kv
        value = _parse_conf_value(raw_value)

        if key == "ClusterName":
            result.cluster_name = value

        elif key == "PriorityFlags":
            result.priority_flags = value

        elif key == "PriorityType":
            result.priority_type = value

        elif key == "PriorityDecayHalfLife":
            result.priority_decay_half_life = value

        elif key == "PriorityUsageResetPeriod":
            result.priority_usage_reset_period = value

        elif key == "PartitionName":
            partition_buffer.append(raw_value)
            if not line.endswith("\\") and not line.endswith("\\ ") and not line.rstrip(" \\t").endswith("\\"):
                # Flush buffer - this PartitionName line is complete
                _flush_partition_buffer(partition_buffer, partition_defaults, result)
                partition_buffer = []

        elif key == "NodeName":
            node_buffer.append(raw_value)
            # NodeName lines are typically single-line, but can be continued
            if not line.endswith("\\") and not line.endswith("\\ ") and not line.rstrip(" \\t").endswith("\\"):
                _flush_node_buffer(node_buffer, node_defaults, result)
                node_buffer = []

        elif key == "QOSName":
            # QOS definitions in slurm.conf (rare, usually in slurmdbd.conf)
            result.qos_names.add(value)

    # Flush any remaining buffers
    if partition_buffer:
        _flush_partition_buffer(partition_buffer, partition_defaults, result)
    if node_buffer:
        _flush_node_buffer(node_buffer, node_defaults, result)

    return result


def _read_slurm_conf(filepath: str) -> list[str]:
    """Read a slurm.conf file, joining continuation lines (backslash-newline)."""
    with open(filepath, "r") as f:
        raw_lines = f.read().split("\n")

    joined: list[str] = []
    buf: str = ""
    for line in raw_lines:
        stripped = line.rstrip()
        if stripped.endswith("\\") or stripped.endswith("\\ ") or stripped.endswith("\\") or stripped.endswith("\\ "):
            # Remove trailing whitespace and continuation marker
            buf += stripped[:-1].strip() + " "
        else:
            buf += stripped
            joined.append(buf)
            buf = ""
    if buf:
        joined.append(buf)
    return joined


def _parse_partition_subparams(param_str: str) -> dict[str, str]:
    """Parse sub-parameters from a PartitionName line's leftover.

    Handles format: ``Nodes=cpn-[10-20] Default=YES DefMemPerCPU=2800 ...``
    """
    params: dict[str, str] = {}
    # Tokenize on whitespace, respecting quoted values
    tokens = param_str.split()
    for token in tokens:
        if "=" in token:
            k, v = token.split("=", 1)
            params[k] = _parse_conf_value(v)
    return params


def _flush_partition_buffer(
    buffer: list[str],
    defaults: dict[str, str],
    result: ParsedSlurmConfig,
) -> None:
    """Process a complete PartitionName entry (possibly multi-line)."""
    full_line = " ".join(buffer).strip()
    if not full_line:
        return

    # Extract partition name (first token before the first space)
    # Format: "name subparam1=val subparam2=val"
    name_end = full_line.find(" ")
    if name_end == -1:
        name = _parse_conf_value(full_line)
        result.partitions.append(ParsedPartition(name=name))
        return

    name = _parse_conf_value(full_line[:name_end])
    rest = full_line[name_end:].strip()

    params = _parse_partition_subparams(rest)

    # Merge with defaults
    merged_defaults = defaults.copy()
    for k, v in params.items():
        merged_defaults[k] = v

    # Build ParsedPartition
    pp = ParsedPartition(name=name)

    # Nodes
    nodes_str = merged_defaults.get("Nodes", "")
    if nodes_str and nodes_str.upper() != "ALL":
        pp.nodes = nodes_str

    # Priority
    priority_str = merged_defaults.get("Priority", "")
    if priority_str:
        try:
            pp.priority = int(priority_str)
        except ValueError:
            pass

    # Default
    default_str = merged_defaults.get("Default", "").upper()
    if default_str == "YES":
        pp.is_default = True

    # Times
    pp.default_time = merged_defaults.get("DefaultTime", "")
    pp.max_time = merged_defaults.get("MaxTime", "")

    # State — validate against SlurmPartitionStateChoices
    state_str = merged_defaults.get("State", "UP").upper()
    if state_str in SlurmPartitionStateChoices.values():
        pp.state = state_str
    elif state_str:
        # Warn about invalid state but accept it
        pp.state = state_str

    # PreemptMode — validate against SlurmPreemptModeChoices
    preempt_str = merged_defaults.get("PreemptMode", "").upper()
    if preempt_str and preempt_str in SlurmPreemptModeChoices.values():
        pp.preempt_mode = preempt_str
    elif preempt_str:
        # Warn about invalid preempt mode but accept it
        pp.preempt_mode = preempt_str

    # DefMemPerCPU
    def_mem_str = merged_defaults.get("DefMemPerCPU", "")
    if def_mem_str:
        try:
            pp.def_mem_per_cpu = int(def_mem_str)
        except ValueError:
            pass

    # QOS references
    pp.allow_qos = merged_defaults.get("AllowQOS", "")
    pp.qos = merged_defaults.get("QOS", "")

    # Account/Groups references
    pp.allow_accounts = merged_defaults.get("AllowAccounts", "")
    pp.allow_groups = merged_defaults.get("AllowGroups", "")

    # TRES billing weights
    pp.tres_billing_weights = merged_defaults.get("TRESBillingWeights", "")

    # Capture the DEFAULT template's TRESBillingWeights as the cluster default
    if name.upper() == "DEFAULT" and pp.tres_billing_weights:
        result.default_tres_billing_weights = pp.tres_billing_weights

    # Collect QOS names referenced by this partition
    for qos_field in (pp.allow_qos, pp.qos):
        if qos_field and qos_field.upper() != "ALL":
            for qname in qos_field.split(","):
                qname = qname.strip()
                if qname:
                    result.qos_names.add(qname)

    result.partitions.append(pp)


def _flush_node_buffer(
    buffer: list[str],
    defaults: dict[str, str],
    result: ParsedSlurmConfig,
) -> None:
    """Process a complete NodeName entry."""
    full_line = " ".join(buffer).strip()
    if not full_line:
        return

    # Extract node name or "DEFAULT"
    name_end = full_line.find(" ")
    if name_end == -1:
        return

    name = _parse_conf_value(full_line[:name_end])
    rest = full_line[name_end:].strip()
    params = _parse_partition_subparams(rest)

    if name.upper() == "DEFAULT":
        # Store as defaults for subsequent NodeName lines
        for k, v in params.items():
            defaults[k] = v
        return

    # Merge with defaults
    merged = defaults.copy()
    for k, v in params.items():
        merged[k] = v

    pn = ParsedNode(name=name)
    pn.features = merged.get("Feature", "")
    pn.gres = merged.get("Gres", "")
    cpu_str = merged.get("CPUs", "")
    if cpu_str:
        try:
            pn.cpus = int(cpu_str)
        except ValueError:
            pass
    mem_str = merged.get("RealMemory", "")
    if mem_str:
        try:
            pn.real_memory = int(mem_str)
        except ValueError:
            pass
    sock_str = merged.get("Sockets", "")
    if sock_str:
        try:
            pn.sockets = int(sock_str)
        except ValueError:
            pass
    core_str = merged.get("CoresPerSocket", "")
    if core_str:
        try:
            pn.cores_per_socket = int(core_str)
        except ValueError:
            pass
    thread_str = merged.get("ThreadsPerCore", "")
    if thread_str:
        try:
            pn.threads_per_core = int(thread_str)
        except ValueError:
            pass

    result.nodes.append(pn)


__all__ = (
    "ParsedPartition",
    "ParsedNode",
    "ParsedSlurmConfig",
    "parse_slurm_conf",
    "parse_tres_weights",
)
