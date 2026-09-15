# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import random
from datetime import datetime, timedelta
from typing import Optional

from django.conf import settings

from .base import RESTRICTED_PATHS, ErrNotFound, StorageBackend, StoragePath, StorageQuotaDTO

logger = logging.getLogger(__name__)


class DummyBackend(StorageBackend):
    """Stateful in-memory storage backend for development and testing.

    No API calls — every operation mutates an in-memory path and quota
    store with the same semantics as a real backend: unknown paths and
    quotas raise ``ErrNotFound``, created records come back from
    ``stat_path``/``get_quota``/``get_all_quotas``, and locks flip the
    ``locked`` flag on the path record.

    The store is shared class-wide, keyed by cluster name, so state
    persists across ``get_backend()`` instantiations — mirroring a real
    array that survives between syncs.  Each cluster's cache starts
    empty, exactly like a freshly provisioned array; ``StorageConfig``
    reconciles the dummy clusters at startup (when
    ``STORAGE_DUMMY_AUTO_SEED`` is enabled), so the cache comes up
    matching ColdFront's active quotas.  Thereafter the sync engine
    maintains it like any real backend.

    Tests reset the shared caches via ``reset()`` (an autouse fixture in
    ``tests/storage/conftest.py``); the sync engine's ``backends`` test
    seam seeds instances with initial state.
    """

    # Snapshot policy methods are implemented below.
    supports_snapshot_policies = True

    #: Shared per-cluster state: {cluster_name: {"paths": {}, "quotas": {},
    #:   "snapshot_policies": {}, "next_id": int}}.
    _state: dict[str, dict] = {}

    #: Cluster names whose cache has already been seeded this process.
    #: Marked before the bootstrap sync runs so construction can't recurse.
    _bootstrapped: set[str] = set()

    @classmethod
    def display_name(cls):
        """The display name of the backend"""
        return "Dummy"

    @classmethod
    def reset(cls):
        """Discard all shared caches and bootstrap flags (test isolation)."""
        cls._state.clear()
        cls._bootstrapped.clear()

    def __init__(self, cluster_name: str = "", random_usage: bool = True):
        super().__init__(cluster_name)
        state = self._state.setdefault(
            cluster_name,
            {"paths": {}, "quotas": {}, "snapshot_policies": {}, "next_id": 1},
        )
        self._paths = state["paths"]
        self._quotas = state["quotas"]
        self._snapshot_policies = state["snapshot_policies"]
        self._shared = state
        self._random_usage = random_usage
        self._maybe_bootstrap(cluster_name)

    def _maybe_bootstrap(self, cluster_name):
        """Seed the cluster's cache from ColdFront's active quotas on first use.

        When ``STORAGE_DUMMY_AUTO_SEED`` is enabled, the first construction
        for a cluster runs the real reconciliation sync so the shared cache
        comes up matching the DB — like a real array that has already
        received its first sync.  The cluster is marked *before* the sync
        call, so the sync's own ``get_backend()`` construction (which shares
        the cache) sees the flag and does not recurse.  If the tables are
        not migrated yet, the attempt is skipped and the next normal sync
        reconciles the (still empty) cache instead.
        """
        if not cluster_name or cluster_name in self._bootstrapped:
            return
        self._bootstrapped.add(cluster_name)

        if not settings.STORAGE_DUMMY_AUTO_SEED:
            return

        try:
            from coldfront.storage import sync as _sync

            _sync.sync_storage_clusters([cluster_name])
        except Exception as exc:
            logger.warning("Dummy backend bootstrap skipped for %s (%s)", cluster_name, exc)

    # --- Paths ---

    def stat_path(self, path: str) -> StoragePath:
        logger.info("stat_path(path=%r)", path)
        try:
            path = self._paths[path]
            if self._random_usage:
                # Set access time randomly between now and 2 days ago
                now = datetime.now()
                two_days_ago = now - timedelta(days=2)
                total_seconds = int((now - two_days_ago).total_seconds())
                random_seconds = random.randint(0, total_seconds)
                random_datetime = now - timedelta(seconds=random_seconds)
                path.atime = random_datetime.strftime("%Y-%m-%d %H:%M:%S")

            return path
        except KeyError:
            raise ErrNotFound from None

    def create_path(self, path: str, user: str, group: str, mode: int) -> None:
        logger.info("create_path(path=%r, user=%r, group=%r, mode=%r)", path, user, group, mode)
        self._paths[path] = StoragePath(
            path=path,
            owning_user=user,
            owning_group=group,
            path_mode=mode,
        )

    def delete_path(self, path: str) -> None:
        logger.info("delete_path(path=%r)", path)
        if path in RESTRICTED_PATHS:
            raise Exception(f"Not removing restricted path {path}")
        try:
            del self._paths[path]
        except KeyError:
            raise ErrNotFound from None

    def lock_path(self, path: str) -> None:
        logger.info("lock_path(path=%r)", path)
        if path in RESTRICTED_PATHS:
            raise Exception(f"Not locking restricted path {path}")
        stat = self.stat_path(path)
        stat.locked = True

    def unlock_path(self, path: str) -> None:
        logger.info("unlock_path(path=%r)", path)
        stat = self.stat_path(path)
        stat.locked = False

    # --- Quotas ---

    def get_quota(self, path: str) -> StorageQuotaDTO:
        logger.info("get_quota(path=%r)", path)
        try:
            quota = self._quotas[path]
            if self._random_usage:
                # Set usaged randomly between 1G-10G
                quota.used_bytes = random.randint(1000000000000, 10000000000000)
                self._quotas[path] = quota
            return quota
        except KeyError:
            raise ErrNotFound from None

    def create_quota(
        self,
        path: str,
        share_type: str,
        hard_limit_bytes: Optional[int],
        files_limit: Optional[int],
        grace: Optional[str],
        *,
        soft_limit_bytes: Optional[int] = None,
        soft_limit_files: Optional[int] = None,
    ) -> dict:
        logger.info(
            "create_quota(path=%r, share_type=%r, hard_limit_bytes=%r, files_limit=%r, grace=%r, "
            "soft_limit_bytes=%r, soft_limit_files=%r)",
            path,
            share_type,
            hard_limit_bytes,
            files_limit,
            grace,
            soft_limit_bytes,
            soft_limit_files,
        )
        self._shared["next_id"] += 1
        quota_id = self._shared["next_id"]
        self._quotas[path] = StorageQuotaDTO(
            id=quota_id,
            path=path,
            name=path,
            state="OK",
            hard_limit_bytes=hard_limit_bytes,
            soft_limit_bytes=soft_limit_bytes,
            hard_limit_files=files_limit,
            soft_limit_files=soft_limit_files,
            grace_period=grace,
        )
        return {"id": quota_id, "path": path}

    def update_quota(
        self,
        quota_id: int,
        hard_limit_bytes: Optional[int],
        files_limit: Optional[int],
        soft_limit_bytes: Optional[int] = None,
        soft_limit_files: Optional[int] = None,
        grace_period: Optional[str] = None,
    ) -> None:
        logger.info(
            "update_quota(quota_id=%r, hard_limit_bytes=%r, files_limit=%r, "
            "soft_limit_bytes=%r, soft_limit_files=%r, grace_period=%r)",
            quota_id,
            hard_limit_bytes,
            files_limit,
            soft_limit_bytes,
            soft_limit_files,
            grace_period,
        )
        try:
            quota = next(q for q in self._quotas.values() if q.id == quota_id)
        except StopIteration:
            raise ErrNotFound from None
        quota.hard_limit_bytes = hard_limit_bytes
        quota.hard_limit_files = files_limit
        quota.soft_limit_bytes = soft_limit_bytes
        quota.soft_limit_files = soft_limit_files
        quota.grace_period = grace_period

    def delete_quota(self, path: str) -> None:
        logger.info("delete_quota(path=%r)", path)
        try:
            del self._quotas[path]
        except KeyError:
            raise ErrNotFound from None

    def get_all_quotas(self) -> list[StorageQuotaDTO]:
        logger.info("get_all_quotas()")
        return list(self._quotas.values())

    # --- Optional snapshot methods ---

    def apply_snapshot_policy(self, path: str, policy: dict) -> None:
        logger.info("apply_snapshot_policy(path=%r, policy=%r)", path, policy)
        self._snapshot_policies[path] = dict(policy)

    def remove_snapshot_policy(self, path: str) -> None:
        logger.info("remove_snapshot_policy(path=%r)", path)
        try:
            del self._snapshot_policies[path]
        except KeyError:
            raise ErrNotFound from None

    def get_snapshot_status(self, path: str) -> Optional[dict]:
        logger.info("get_snapshot_status(path=%r)", path)
        return self._snapshot_policies.get(path)


def seed_dummy_backends(sender, **kwargs):
    """Initializes each storage dummy backend before running the dev server so the cache is seeded at startup"""
    from coldfront.storage.models import StorageCluster

    if not os.environ.get("RUN_MAIN") == "true":
        return

    if not settings.STORAGE_DUMMY_AUTO_SEED:
        return

    try:
        clusters = list(StorageCluster.objects.filter(backend_path="coldfront.storage.backends.dummy.DummyBackend"))
    except Exception as exc:
        logger.warning("Failed to seed dummy storage backend: (%s)", exc)
        return

    if not clusters:
        return

    for cluster in clusters:
        try:
            logger.warning("Seeding dummy storage backend for cluster: %s", cluster.name)
            DummyBackend(cluster_name=cluster.name)
        except Exception as exc:
            logger.warning("Dummy backend seeding failed for cluster: %s (%s)", cluster.name, exc)
