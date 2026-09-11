# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Slurm sync package: access-control (association/QOS) + usage rollup.

The package re-exports the public sync API. Internal helpers live in the
``access_control`` / ``usage`` submodules.

The access-control path is batch-only: :func:`sync_slurm_clusters` is the
single code path shared by the CLI, the periodic system sync job, and the
on-demand "sync now" job. There are no targeted/real-time workers.
"""

from .access_control import (
    SyncReport,
    sync_slurm_clusters,
)
from .usage import (
    UsageSyncReport,
    resolve_catchup_range,
    run_usage_sync,
)

__all__ = [
    "SyncReport",
    "UsageSyncReport",
    "sync_slurm_clusters",
    "run_usage_sync",
    "resolve_catchup_range",
]
