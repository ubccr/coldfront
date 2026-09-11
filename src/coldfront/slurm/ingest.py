# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Cluster ingestion / seeding from slurm.conf and the Slurm REST API.

Seeds ColdFront's SlurmCluster / SlurmPartition / SlurmQOS records from one of
two sources:

* ``ingest_cluster_from_conf()`` — parses a slurm.conf file.
* ``ingest_cluster_from_api()`` — fetches from the Slurm REST API.
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.core.exceptions import ImproperlyConfigured

from coldfront.slurm.choices import (
    SlurmPartitionStateChoices,
    SlurmPreemptModeChoices,
    SlurmPriorityFlagsChoices,
    SlurmPriorityTypeChoices,
    SlurmPriorityUsageResetPeriodChoices,
)
from coldfront.slurm.client import SlurmClient
from coldfront.slurm.models import (
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
)
from coldfront.slurm.parser import (
    ParsedSlurmConfig,
    SlurmTime,
    parse_slurm_conf,
    parse_slurm_time,
    parse_tres_weights,
)
from coldfront.slurm.utils import build_client

logger = logging.getLogger(__name__)


@dataclass
class ImportReport:
    """Report from a cluster import operation."""

    cluster: str
    success: bool = False
    cluster_created: bool = False
    cluster_updated: bool = False
    cluster_found: bool = False
    partitions_created: int = 0
    partitions_updated: int = 0
    partitions_found: int = 0
    qos_created: int = 0
    qos_found: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _cluster_conf_kwargs(parsed: ParsedSlurmConfig) -> dict[str, Any]:
    """Build SlurmCluster kwargs for cluster-level slurm.conf config.

    Only includes keys present in the parsed slurm.conf. Never sets
    enforce_su_limits (a ColdFront-only decision, not in slurm.conf).
    TRESBillingWeights is expressed per-partition (DEFAULT is absorbed at
    parse time), so no cluster-level billing key is set here.
    """
    kwargs: dict[str, Any] = {}
    if parsed.priority_flags:
        flags = [f.strip() for f in parsed.priority_flags.split(",") if f.strip()]
        kwargs["priority_flags"] = [f for f in flags if f in SlurmPriorityFlagsChoices.values()]
    if parsed.priority_type:
        if parsed.priority_type in SlurmPriorityTypeChoices.values():
            kwargs["priority_type"] = parsed.priority_type
    if parsed.priority_decay_half_life:
        kwargs["priority_decay_half_life"] = parsed.priority_decay_half_life
    if parsed.priority_usage_reset_period:
        if parsed.priority_usage_reset_period in SlurmPriorityUsageResetPeriodChoices.values():
            kwargs["priority_usage_reset_period"] = parsed.priority_usage_reset_period
    return kwargs


def ingest_cluster_from_conf(
    conf_path: str,
    noop: bool = False,
    update: bool = False,
) -> ImportReport:
    """Import a cluster from a slurm.conf file.

    Parses the config file, then creates or updates SlurmCluster,
    SlurmPartition, and SlurmQOS records in ColdFront.

    Args:
        conf_path: Path to the slurm.conf file.
        noop: If True, print what would happen without writing to DB.
        update: If True, update existing records; otherwise skip.

    Returns:
        An ImportReport with counts and errors.
    """
    report = ImportReport(cluster="", success=False)

    parsed = parse_slurm_conf(conf_path)
    if not parsed.cluster_name:
        report.errors.append("No ClusterName found in slurm.conf")
        return report

    report.cluster = parsed.cluster_name

    # --- QOS ---
    for qos_name in sorted(parsed.qos_names):
        if noop:
            report.qos_found += 1
            continue
        try:
            SlurmQOS.objects.get(name=qos_name)
            report.qos_found += 1
        except SlurmQOS.DoesNotExist:
            SlurmQOS.objects.create(name=qos_name)
            report.qos_created += 1

    # --- Cluster ---
    cluster_billing = _cluster_conf_kwargs(parsed)
    if noop:
        report.cluster_created = True  # Would create
    else:
        try:
            cluster = SlurmCluster.objects.get(name=parsed.cluster_name)
            if update:
                for k, v in cluster_billing.items():
                    setattr(cluster, k, v)
                cluster.save()
                report.cluster_updated = True
            else:
                report.cluster_found = True
        except SlurmCluster.DoesNotExist:
            cluster = SlurmCluster.objects.create(
                name=parsed.cluster_name,
                **cluster_billing,
            )
            report.cluster_created = True

    # --- Partitions ---
    if not noop and not parsed.partitions:
        report.warnings.append("No partitions found in slurm.conf")
        report.success = True
        return report

    for pp in parsed.partitions:
        # Skip DEFAULT template partition (it's not a real partition)
        if pp.name.upper() == "DEFAULT":
            continue

        if noop:
            report.partitions_created += 1
            continue

        # Build partition kwargs
        kwargs: dict[str, Any] = {
            "cluster": cluster,
            "name": pp.name,
        }
        if pp.nodes:
            kwargs["nodes"] = pp.nodes
        if pp.priority is not None:
            kwargs["priority"] = pp.priority
        kwargs["is_default"] = pp.is_default
        if pp.max_time:
            kwargs["max_time"] = parse_slurm_time(pp.max_time)
        if pp.default_time:
            kwargs["default_time"] = parse_slurm_time(pp.default_time)
        if pp.state:
            # Validate state against SlurmPartitionStateChoices
            state_upper = pp.state.upper()
            if state_upper in SlurmPartitionStateChoices.values():
                kwargs["state"] = state_upper
            else:
                kwargs["state"] = pp.state
        if pp.preempt_mode:
            # Validate preempt_mode against SlurmPreemptModeChoices
            preempt_upper = pp.preempt_mode.upper()
            if preempt_upper in SlurmPreemptModeChoices.values():
                kwargs["preempt_mode"] = preempt_upper
            else:
                kwargs["preempt_mode"] = pp.preempt_mode
        if pp.def_mem_per_cpu is not None:
            kwargs["def_mem_per_cpu"] = pp.def_mem_per_cpu
        if pp.def_mem_per_node is not None:
            kwargs["def_mem_per_node"] = pp.def_mem_per_node
        if pp.priority_tier is not None:
            kwargs["priority_tier"] = pp.priority_tier
        if pp.max_nodes is not None:
            kwargs["max_nodes"] = pp.max_nodes
        if pp.max_cpus_per_node is not None:
            kwargs["max_cpus_per_node"] = pp.max_cpus_per_node
        if pp.tres_billing_weights:
            kwargs["tres_billing_weights"] = parse_tres_weights(pp.tres_billing_weights)

        try:
            partition = SlurmPartition.objects.get(cluster=cluster, name=pp.name)
            if update:
                for k, v in kwargs.items():
                    setattr(partition, k, v)
                partition.save()
                report.partitions_updated += 1
            else:
                report.partitions_found += 1
        except SlurmPartition.DoesNotExist:
            partition = SlurmPartition(**kwargs)
            partition.save()
            report.partitions_created += 1

        # Link QOS references
        if not noop:
            # AllowQOS (whitelist) -> partition.allow_qos M2M
            if pp.allow_qos and pp.allow_qos.upper() != "ALL":
                allow_qos_names = [n.strip() for n in pp.allow_qos.split(",") if n.strip()]
                allow_qos_objs = SlurmQOS.objects.filter(name__in=allow_qos_names)
                partition.allow_qos.set(allow_qos_objs)

            # DenyQOS (blocklist) -> partition.deny_qos M2M
            if pp.deny_qos and pp.deny_qos.upper() != "ALL":
                deny_qos_names = [n.strip() for n in pp.deny_qos.split(",") if n.strip()]
                deny_qos_objs = SlurmQOS.objects.filter(name__in=deny_qos_names)
                partition.deny_qos.set(deny_qos_objs)

            # QOS (assigned partition QOS) -> partition.qos FK
            if pp.qos and pp.qos.upper() != "ALL":
                try:
                    partition.qos = SlurmQOS.objects.get(name=pp.qos.strip())
                    partition.save()
                except SlurmQOS.DoesNotExist:
                    pass

    report.success = len(report.errors) == 0
    return report


def ingest_cluster_from_api(
    cluster_name: str,
    client: SlurmClient | None = None,
    noop: bool = False,
    update: bool = False,
) -> ImportReport:
    """Import a cluster from the Slurm REST API.

    Fetches partition info from slurmctld and QOS info from slurmdbd,
    then creates or updates models in ColdFront.

    Args:
        cluster_name: Name of the cluster to import.
        client: A SlurmClient instance. If None, builds one from settings.
        noop: If True, print what would happen without writing to DB.
        update: If True, update existing records; otherwise skip.

    Returns:
        An ImportReport with counts and errors.
    """
    report = ImportReport(cluster=cluster_name, success=False)

    # Build client if needed
    if client is None:
        try:
            client = build_client(cluster_name)
        except ImproperlyConfigured as exc:
            report.errors.append(f"slurmrestd not configured: {exc}")
            return report

    # Fetch partitions from slurmctld
    try:
        part_data = client.get_partitions()
    except Exception as exc:
        report.errors.append(f"Failed to fetch partitions: {exc}")
        return report

    partitions = part_data.get("partitions", [])
    if not partitions:
        report.warnings.append("No partitions returned by slurmctld")
        report.success = True
        return report

    # Fetch QOS from slurmdbd
    try:
        qos_data = client.get_qos()
    except Exception as exc:
        report.warnings.append(f"Failed to fetch QOS (non-fatal): {exc}")
        qos_data = {}

    api_qos_list = qos_data.get("qos", [])
    api_qos_names: set[str] = set()
    for q in api_qos_list:
        if isinstance(q, dict):
            qname = q.get("name", "")
            if qname:
                api_qos_names.add(qname)

    # --- QOS ---
    if noop:
        report.qos_found = len(api_qos_names)
    else:
        for qos_name in sorted(api_qos_names):
            try:
                SlurmQOS.objects.get(name=qos_name)
                report.qos_found += 1
            except SlurmQOS.DoesNotExist:
                SlurmQOS.objects.create(
                    name=qos_name,
                )
                report.qos_created += 1

    # --- Cluster ---
    if noop:
        report.cluster_created = True
    else:
        try:
            cluster = SlurmCluster.objects.get(name=cluster_name)
            if update:
                cluster.save()
                report.cluster_updated = True
            else:
                report.cluster_found = True
        except SlurmCluster.DoesNotExist:
            cluster = SlurmCluster.objects.create(
                name=cluster_name,
            )
            report.cluster_created = True

    # --- Partitions ---
    for part in partitions:
        if not isinstance(part, dict):
            continue
        part_name = part.get("name", "")
        if not part_name:
            continue

        if noop:
            report.partitions_created += 1
            continue

        # Build kwargs from API response fields
        kwargs: dict[str, Any] = {
            "cluster": cluster,
            "name": part_name,
        }

        nodes_str = part.get("nodes", "")
        if isinstance(nodes_str, dict):
            # Live GET nests the node list under ``nodes.configured``
            # (the ``Nodes`` slurm.conf param), not under ``nodes.nodes``.
            nodes_list = nodes_str.get("configured", nodes_str.get("name", ""))
            if isinstance(nodes_list, list):
                kwargs["nodes"] = ",".join(nodes_list)
            else:
                kwargs["nodes"] = str(nodes_list)
        elif nodes_str:
            kwargs["nodes"] = nodes_str

        priority = part.get("priority")
        if priority is not None:
            try:
                kwargs["priority"] = int(priority)
            except (ValueError, TypeError):
                pass

        # State — live nests under partition/state as a flag-bit array
        partition_obj = part.get("partition") if isinstance(part.get("partition"), dict) else {}
        state = partition_obj.get("state", "")
        if isinstance(state, list):
            state = state[0] if state else ""
        elif isinstance(state, dict):
            state = state.get("state", "UP")
        state_upper = state.upper() if state else "UP"
        # Validate against SlurmPartitionStateChoices
        if state_upper in SlurmPartitionStateChoices.values():
            kwargs["state"] = state_upper
        else:
            kwargs["state"] = state_upper  # still accept it but warn

        # Default flag
        kwargs["is_default"] = part.get("default", "NO") == "YES"

        # Preempt mode — live top-level preempt_mode is a flag-bit array
        preempt = part.get("preempt_mode", "")
        if isinstance(preempt, list):
            preempt = preempt[0] if preempt else ""
        elif isinstance(preempt, dict):
            preempt = preempt.get("preempt_mode", "")
        preempt_upper = preempt.upper()
        # Validate against SlurmPreemptModeChoices
        if preempt_upper and preempt_upper in SlurmPreemptModeChoices.values():
            kwargs["preempt_mode"] = preempt_upper
        elif preempt:
            kwargs["preempt_mode"] = preempt
        else:
            kwargs["preempt_mode"] = ""

        # Max time -> max_time (SlurmTime), nested under maximums/time
        maximums_map = part.get("maximums") or {}
        if isinstance(maximums_map, dict):
            max_time_obj = maximums_map.get("time")
            if isinstance(max_time_obj, dict):
                if max_time_obj.get("infinite"):
                    kwargs["max_time"] = SlurmTime()
                elif max_time_obj.get("set") and max_time_obj.get("number"):
                    kwargs["max_time"] = SlurmTime(duration=timedelta(minutes=int(max_time_obj["number"])))

        # Default time -> default_time (SlurmTime), nested under defaults/time
        defaults_map = part.get("defaults") or {}
        if isinstance(defaults_map, dict):
            default_time_obj = defaults_map.get("time")
            if isinstance(default_time_obj, dict):
                if default_time_obj.get("infinite"):
                    kwargs["default_time"] = SlurmTime()
                elif default_time_obj.get("set") and default_time_obj.get("number"):
                    kwargs["default_time"] = SlurmTime(duration=timedelta(minutes=int(default_time_obj["number"])))

        # DefMemPerCPU (nested under defaults/partition_memory_per_cpu)
        defaults_obj = part.get("defaults", {})
        if not isinstance(defaults_obj, dict):
            defaults_obj = {}
        def_mem = defaults_obj.get("partition_memory_per_cpu")
        if def_mem is None:
            def_mem = part.get("def_mem_per_cpu")
        if def_mem is not None:
            try:
                kwargs["def_mem_per_cpu"] = int(def_mem)
            except (ValueError, TypeError):
                pass

        # DefMemPerNode (defaults/partition_memory_per_node)
        mem_per_node = defaults_obj.get("partition_memory_per_node")
        if mem_per_node is not None:
            try:
                kwargs["def_mem_per_node"] = int(mem_per_node)
            except (ValueError, TypeError):
                pass

        # PriorityTier (priority/tier)
        priority_obj = part.get("priority")
        if isinstance(priority_obj, dict):
            tier = priority_obj.get("tier")
            if tier is not None:
                try:
                    kwargs["priority_tier"] = int(tier)
                except (ValueError, TypeError):
                    pass

        # MaxNodes / MaxCPUsPerNode (maximums/nodes, maximums/cpus_per_node)
        maximums = part.get("maximums", {})
        if not isinstance(maximums, dict):
            maximums = {}
        max_nodes = maximums.get("nodes")
        if max_nodes is not None:
            try:
                kwargs["max_nodes"] = int(max_nodes)
            except (ValueError, TypeError):
                pass
        max_cpus = maximums.get("cpus_per_node")
        if max_cpus is not None:
            try:
                kwargs["max_cpus_per_node"] = int(max_cpus)
            except (ValueError, TypeError):
                pass

        # TRESBillingWeights (tres/billing_weights)
        tres_obj = part.get("tres", {})
        if isinstance(tres_obj, dict):
            billing_weights = tres_obj.get("billing_weights")
            if billing_weights:
                kwargs["tres_billing_weights"] = parse_tres_weights(billing_weights)

        # QOS references
        # Live GET nests partition QOS under ``part["qos"]`` as an object
        # (``allowed`` = AllowQOS, ``deny`` = DenyQOS, ``assigned`` = QOS),
        # not as flat top-level ``allow_qos``/``qos`` keys.
        qos_obj = part.get("qos", {})
        if not isinstance(qos_obj, dict):
            qos_obj = {}
        allow_qos_names: set[str] = set()
        allow_qos = qos_obj.get("allowed", "")
        if isinstance(allow_qos, str) and allow_qos and allow_qos.upper() != "ALL":
            allow_qos_names.update(n.strip() for n in allow_qos.split(","))
        qos_deny = qos_obj.get("deny", "")
        qos_assigned = qos_obj.get("assigned", "")

        try:
            partition = SlurmPartition.objects.get(cluster=cluster, name=part_name)
            if update:
                for k, v in kwargs.items():
                    if k != "cluster":
                        setattr(partition, k, v)
                partition.save()
                report.partitions_updated += 1
            else:
                report.partitions_found += 1
        except SlurmPartition.DoesNotExist:
            partition = SlurmPartition(**kwargs)
            partition.save()
            report.partitions_created += 1

        # Link QOS references
        # AllowQOS (whitelist) -> partition.allow_qos M2M
        if allow_qos_names:
            allow_qos_objs = SlurmQOS.objects.filter(name__in=list(allow_qos_names))
            partition.allow_qos.set(allow_qos_objs)

        # DenyQOS (blocklist) -> partition.deny_qos M2M
        if isinstance(qos_deny, str) and qos_deny and qos_deny.upper() != "ALL":
            deny_qos_names = [n.strip() for n in qos_deny.split(",") if n.strip()]
            deny_qos_objs = SlurmQOS.objects.filter(name__in=deny_qos_names)
            partition.deny_qos.set(deny_qos_objs)

        # QOS (assigned partition QOS) -> partition.qos FK
        if isinstance(qos_assigned, str) and qos_assigned and qos_assigned.upper() != "ALL":
            try:
                partition.qos = SlurmQOS.objects.get(name=qos_assigned.strip())
                partition.save()
            except SlurmQOS.DoesNotExist:
                pass

    report.success = len(report.errors) == 0
    return report
