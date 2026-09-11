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

# Cron schedule for the periodic batch access-control sync job.  Evaluated in
# the default timezone (Django's TIME_ZONE); missed occurrences are skipped.
# Defaults to nightly at 04:00.  Can be set more frequently for faster
# convergence, at the cost of increased slurmrestd load.
SLURM_SYNC_CRON = ENV.str("COLDFRONT_SLURM_SYNC_CRON", default="0 4 * * *")

# Cron schedule for the periodic SU usage ingest job.  Defaults to 05:00
# nightly (staggered an hour after SLURM_SYNC_CRON), after the previous day
# has completed.  Independent of SLURM_SYNC_CRON so the two syncs can run on
# different cadences.
SLURM_USAGE_SYNC_CRON = ENV.str("COLDFRONT_SLURM_USAGE_SYNC_CRON", default="0 5 * * *")
