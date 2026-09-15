# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.config.env import ENV

# ------------------------------------------------------------------------------
# Sync scheduling (global defaults)
# ------------------------------------------------------------------------------

# Cron schedule for the periodic full reconciliation sync job.  Evaluated in
# the default timezone (Django's TIME_ZONE); missed occurrences are skipped.
# Defaults to nightly at 04:30 (staggered half an hour after SLURM_SYNC_CRON).
# Can be set more frequently for faster convergence, at the cost of increased
# backend API load.
STORAGE_SYNC_CRON = ENV.str("COLDFRONT_STORAGE_SYNC_CRON", default="30 4 * * *")

# Cron schedule for the periodic usage-only sync job.  Defaults to hourly,
# since the usage sync is read-only with respect to the backend and keeps
# resource/cluster usage figures fresh between nightly reconciles.
# Independent of STORAGE_SYNC_CRON so the two syncs can run on different
# cadences.
STORAGE_USAGE_SYNC_CRON = ENV.str("COLDFRONT_STORAGE_USAGE_SYNC_CRON", default="0 * * * *")

# When True, StorageConfig seeds each cluster's DummyBackend cache at
# startup by running the real reconciliation sync, so a dev ``runserver``
# comes up with the in-memory backend already matching ColdFront's active
# quotas.  Dummy clusters start from an empty cache (like a fresh array);
# this just gives them their first sync at server start.  Disabled in the
# test environment (``.env.testing``) so engine tests see the empty-cache
# first-sync behavior deterministically.
STORAGE_DUMMY_AUTO_SEED = ENV.bool("COLDFRONT_STORAGE_DUMMY_AUTO_SEED", default=False)
