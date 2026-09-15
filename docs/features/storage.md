# Storage

ColdFront has a Storage app (`coldfront.storage`) that manages allocations to
storage resources. Storage allocations carry a quota amount and the lifecycle
creates and removes paths and quotas on the storage system.

## Storage Resources

A **StorageResource** is an allocatable storage resource. Users request an
allocation to a storage resource and specify the requested quota amount on
a separate form. Each storage resource is backed by one or more storage
clusters.

## Storage Clusters

A **StorageCluster** represents a storage system backend. It has a
`backend_path` field that points to a Python class implementing the
`StorageBackend` interface. The cluster stores no connection settings —
each backend handles its own configuration.

## Storage Quotas

A **StorageQuota** bridges an allocation to a storage resource. It carries
the path, ownership, and quota limits such as:

- **hard_limit** — The approved quota limit in bytes
- **hard_limit_requested** — The user's requested amount
- **soft_limit** — A warning threshold before the hard limit
- **hard_limit_files** and **soft_limit_files** — File count limits
- **share_type** — POSIX, SMB, or NFS share type

The path is auto-generated from a template on the storage resource. The
template supports variables such as `{project.slug}` and `{allocation.id}`.
Admins can override the path before activation.

## Backend Plugin System

Each storage backend is a Python class that implements the abstract
`StorageBackend` interface. The interface defines methods for creating
paths, creating quotas, updating quotas, and removing quotas. Backends
are auto-discovered at startup and can also be registered by plugins.

## Snapshot Policies

Storage clusters can define snapshot policies with an interval, retention
days, and extra configuration. Each quota can optionally select a snapshot
policy. The backend receives the policy details when creating or removing
the snapshot schedule.

## Sync Mechanism

The storage integration is batch-only, like Slurm — there are no
targeted/real-time enqueues. Allocation activation and expiry are
reflected on the backend exclusively by the reconciliation sync, which
the CLI commands and system jobs call:

1. **Full reconciliation sync** (`StorageSyncJob`, nightly; also
   `coldfront storage_sync`) — fetches all quotas once per cluster and:
   creates missing paths and quotas, updates out-of-sync limits, unlocks
   re-activated paths, applies snapshot policies, sweeps orphaned quotas
   under the static path prefixes of the cluster's storage resources
   (foreign quotas elsewhere on the array are never touched), and pulls
   usage back into the quota rows.

2. **Usage-only sync** (`StorageUsageSyncJob`, hourly; also
   `coldfront storage_usage_sync`) — fetches all quotas once per cluster
   and updates used/used_files/state on the active quota rows. Never
   mutates the backend, so it can run frequently.

## Capacity Tracking

Both storage resources and clusters track capacity, allocated, and used
bytes. Callbacks update allocated bytes atomically on activation and
expiration. The sync engine updates used bytes from the backend.
