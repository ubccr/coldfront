# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


@dataclass
class StoragePath:
    """DTO for a storage path returned by the backend."""

    path: str
    owning_user: str = ""
    owning_group: str = ""
    owning_uid: Optional[int] = None
    owning_gid: Optional[int] = None
    is_directory: bool = True
    mode: Optional[int] = None
    atime: Optional[str] = None
    mtime: Optional[str] = None
    ctime: Optional[str] = None


@dataclass
class StorageQuotaDTO:
    """DTO for a storage quota returned by the backend."""

    id: int
    path: str
    name: Optional[str] = None
    state: Optional[str] = None
    used: Optional[int] = None  # bytes
    used_files: Optional[int] = None
    hard_limit_bytes: Optional[int] = None  # bytes
    soft_limit_bytes: Optional[int] = None  # bytes
    hard_limit_files: Optional[int] = None
    soft_limit_files: Optional[int] = None
    grace_period: Optional[str] = None


class StorageBackend(ABC):
    """Abstract interface for storage system API backends.

    Each backend handles its own configuration (env vars, Django settings,
    config files, etc.).  The only thing ColdFront provides is the cluster
    name and backend_path.
    """

    def __init__(self, cluster_name: str = ""):
        self.cluster_name = cluster_name

    # --- Required methods ---

    @abstractmethod
    def path_stat(self, path: str) -> StoragePath:
        """Stat a path on the storage system."""

    @abstractmethod
    def create_path(self, path: str, user: str, group: str, mode: int) -> None:
        """Create a directory on the storage system."""

    @abstractmethod
    def delete_path(self, path: str) -> None:
        """Delete a directory on the storage system."""

    @abstractmethod
    def get_quota(self, path: str) -> StorageQuotaDTO:
        """Get current quota for a path."""

    @abstractmethod
    def create_quota(
        self,
        path: str,
        share_type: str,
        hard_limit_bytes: Optional[int],
        files_limit: Optional[int],
        grace: Optional[str],
    ) -> dict:
        """Create a quota on a path.

        The ``share_type`` parameter (one of ``"posix"``, ``"smb"``,
        ``"nfs"``) lets the backend create the appropriate share type
        before applying the quota.  For SMB, the backend creates an SMB
        share with Active Directory integration; for NFS, it creates an
        NFS export; for POSIX, it creates a standard filesystem quota.

        Returns a dict with the quota's backend ID and any additional
        metadata.
        """

    @abstractmethod
    def update_quota(self, quota_id: int, hard_limit_bytes: Optional[int], files_limit: Optional[int]) -> None:
        """Update an existing quota's limits."""

    @abstractmethod
    def delete_quota(self, path: str) -> None:
        """Remove a quota from a path."""

    @abstractmethod
    def lock_path(self, path: str) -> None:
        """Lock/read-only a path (for expired allocations)."""

    @abstractmethod
    def get_all_quotas(self) -> list[StorageQuotaDTO]:
        """Fetch all quotas from the storage system for reconciliation."""

    # --- Optional capabilities ---

    def apply_snapshot_policy(self, path: str, policy: dict) -> None:
        """Apply a snapshot policy to a path.  Optional — not all backends
        support snapshot policies.  The default raises NotImplementedError
        so callers use ``hasattr()`` to check before calling.

        ``policy`` contains the ``StorageSnapshotPolicy`` fields:
        interval, retention_days, extra_config.
        """
        raise NotImplementedError(_("This backend does not support snapshot policies."))

    def remove_snapshot_policy(self, path: str) -> None:
        """Remove snapshot policy from a path.  Optional."""
        raise NotImplementedError(_("This backend does not support snapshot policies."))

    def get_snapshot_status(self, path: str) -> Optional[dict]:
        """Get current snapshot status for a path.  Optional.
        Returns None if not supported.
        """
        return None
