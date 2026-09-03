# Slurm

ColdFront has a Slurm app (`coldfront.slurm`) that integrates with the
[Slurm](https://slurm.schedmd.com/) workload manager. The integration maps
ColdFront allocations to Slurm accounting entities for access control and
synchronizes them using the Slurm REST API. ColdFront can also optionally
intergrate with Slurm's [Trackable RESources (TRES)](https://slurm.schedmd.com/tres.html) for usage tracking and billing.

## Slurm Entities

ColdFront models the following Slurm entities:

- **SlurmCluster** — A compute cluster managed by Slurm. Has a name,
  tenant, default QOS, fairshare, features, and classification, plus the
  SU billing TRES configuration (see below).
- **SlurmPartition** — A named partition within a cluster. Has limits
  such as max jobs, max TRES per job, and wall duration. Each partition
  has an `allow_qos` list and a single assigned QOS.
- **SlurmQOS** — A Quality of Service profile. Defines priority, job
  limits per user and account, and wall duration limits.
- **SlurmAccount** — A named Slurm accounting account. Accounts are lean
  containers with a name and description. All per-association limits live
  on the association instead. Carries `service_units` — the SU grant that
  backs enforcement and usage reporting.
- **SlurmAssociation** — Bridges an Allocation to its SlurmAccount.
  Carries all per-association limits such as fairshare, max jobs, max TRES
  per job, and wall duration. Created when an allocation is requested.
- **SlurmUser** — Tracks each user's default account per cluster. One
  record per user per cluster.
- **SlurmAccountUsage** — A per-account usage aggregate tracking consumed and
  completed service units, node hours, and billing-by-QOS breakdowns.

## Sync Mechanism

The Slurm integration uses a hybrid approach:

1. **Targeted handlers** — When an allocation is activated, the system
   creates associations for all project users on that allocation's
   account and partition. When an allocation expires or is revoked,
   the system removes those associations and kills running jobs.

2. **Periodic batch sync** — A scheduled job runs a full reconciliation
   using `POST /slurmdb/{version}/config` to upsert the complete
   accounting state. This catches any drift or manual changes that targeted handlers missed.

3. **Usage sync** — A separate scheduled job (`SlurmUsageSyncJob`)
   aggregates consumed service units daily from Slurm's job accounting
   (`GET /slurmdb/{version}/jobs/`) into `SlurmAccountUsage` rows. An
   on-demand job (`SlurmUsageSyncNowJob`) and a `coldfront slurm_usage_sync`
   command let admins re-ingest immediately. See [Service Units Billing](#service-units-billing)
   below.

## REST API

The integration communicates with `slurmrestd` over HTTP using JWT
authentication. The client supports API versions v0.0.41 through v0.0.45 with a
single set of serializers.

## Service Units Billing

ColdFront supports billing for **service units** (SU) — the compute-time billing
dimension for a cluster. ColdFront leverages Slurm's [Trackable RESources
(TRES)](https://slurm.schedmd.com/tres.html) billing type (Billing TRES) for
usage based billing. A [background job](background-jobs.md) can be scheduled to
aggregate consumed service units from Slurm allowing centers to invoice per
service unit of consumed usage.

## Dump Generation

ColdFront can generate Slurm association dump files compatible with
`sacctmgr dump`. The dump maps ColdFront models to Slurm's association
hierarchy format with cluster headers, account lines, and user lines.
