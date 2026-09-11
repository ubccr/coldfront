# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm REST API connection settings for ColdFront.

Per-cluster connection settings are defined in ``SLURMRESTD_CLUSTERS``,
modeled after Django's ``DATABASES`` setting.  A ``"default"`` key provides
fallback values used by any cluster without its own entry.

Usage::

    SLURMRESTD_CLUSTERS = {
        "default": {
            "url": "http://slurmrestd:8080",
            "jwt_token": "...",
        },
        "hpc01": {
            "url": "http://hpc01-restd:8080",
            "jwt_token": "...",
        },
    }

Clusters not listed in the dict automatically use the ``"default"`` entry.
"""

from coldfront.config.env import ENV

# ------------------------------------------------------------------------------
# Per-cluster slurmrestd connection settings
# ------------------------------------------------------------------------------

SLURMRESTD_CLUSTERS = ENV.dict(
    "COLDFRONT_SLURMRESTD_CLUSTERS",
    default={
        "default": {
            "url": ENV.str("COLDFRONT_SLURMRESTD_URL", default=""),
            "jwt_token": ENV.str("COLDFRONT_SLURMRESTD_JWT_TOKEN", default=""),
            "version": ENV.str("COLDFRONT_SLURMRESTD_VERSION", default=""),
            "auth_type": ENV.str("COLDFRONT_SLURMRESTD_AUTH_TYPE", default="jwt"),
            "timeout": ENV.int("COLDFRONT_SLURMRESTD_TIMEOUT", default=30),
            "retries": ENV.int("COLDFRONT_SLURMRESTD_RETRIES", default=3),
            "retry_backoff": ENV.float("COLDFRONT_SLURMRESTD_RETRY_BACKOFF", default=1.5),
        },
    },
)

# ------------------------------------------------------------------------------
# Sync scheduling (global defaults)
# ------------------------------------------------------------------------------

# Interval (in minutes) for the periodic batch access-control sync job.
# Defaults to 1440 (daily).  Can be set lower for more frequent convergence,
# at the cost of increased slurmrestd load.
SLURM_SYNC_INTERVAL = ENV.int("COLDFRONT_SLURM_SYNC_INTERVAL", default=1440)

# Interval (in minutes) for the periodic SU usage ingest job.  Defaults to
# 1440 (daily).  Independent of SLURM_SYNC_INTERVAL so the two syncs can run
# on different cadences.
SLURM_USAGE_SYNC_INTERVAL = ENV.int("COLDFRONT_SLURM_USAGE_SYNC_INTERVAL", default=1440)
