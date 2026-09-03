# Background Jobs

ColdFront can execute certain functions as background tasks. Background tasks
are defined as Job classes and executed by a task queue.

## Scheduled Jobs

Some jobs can be configured to run at a set interval. For example, the
Slurm sync job and the Storage sync job run periodically to reconcile
ColdFront state with external systems.

## System Jobs

ColdFront defines system jobs that run automatically. These include:

- **SlurmSyncJob** — Periodically syncs Slurm accounting associations
- **StorageSyncJob** — Periodically syncs storage quotas
- **StorageSyncNowJob** — An on-demand job triggered by admin action
- **SlurmUsageSyncJob** — Daily usage aggregation (consumed service units)
- **SlurmUsageSyncNowJob** — On-demand usage re-ingest triggered by admin action

## On-Demand Jobs

Jobs can also be triggered on demand through the user interface or the
REST API. This lets administrators run a sync immediately when needed.

## Job Lifecycle

Each job has a status: pending, scheduled, running, completed, failed, or
errored. Jobs can be scheduled to run immediately or at a future time.
Scheduled jobs can repeat at a set interval.

!!! note "Current limitations"

    ColdFront currently supports scheduled jobs and system jobs only.
    Custom script execution and remote data source synchronization are
    not yet available.
