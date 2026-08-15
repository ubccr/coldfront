# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Optional

from .base import StorageBackend, StoragePath, StorageQuotaDTO

logger = logging.getLogger(__name__)


class DummyBackend(StorageBackend):
    """Dummy storage backend that logs all operations and returns sensible
    default values.  No real API calls — enables sync engine and callback
    development without a real storage cluster.
    """

    def path_stat(self, path: str) -> StoragePath:
        logger.info("path_stat(path=%r)", path)
        return StoragePath(path=path, owning_user="dummy", owning_group="dummy", mode=2770)

    def create_path(self, path: str, user: str, group: str, mode: int) -> None:
        logger.info("create_path(path=%r, user=%r, group=%r, mode=%r)", path, user, group, mode)

    def delete_path(self, path: str) -> None:
        logger.info("delete_path(path=%r)", path)

    def get_quota(self, path: str) -> StorageQuotaDTO:
        logger.info("get_quota(path=%r)", path)
        return StorageQuotaDTO(id=0, path=path, used=0, hard_limit_bytes=None)

    def create_quota(
        self,
        path: str,
        share_type: str,
        hard_limit_bytes: Optional[int],
        files_limit: Optional[int],
        grace: Optional[str],
    ) -> dict:
        logger.info(
            "create_quota(path=%r, share_type=%r, hard_limit_bytes=%r, files_limit=%r, grace=%r)",
            path,
            share_type,
            hard_limit_bytes,
            files_limit,
            grace,
        )
        return {"id": 0, "path": path}

    def update_quota(self, quota_id: int, hard_limit_bytes: Optional[int], files_limit: Optional[int]) -> None:
        logger.info(
            "update_quota(quota_id=%r, hard_limit_bytes=%r, files_limit=%r)",
            quota_id,
            hard_limit_bytes,
            files_limit,
        )

    def delete_quota(self, path: str) -> None:
        logger.info("delete_quota(path=%r)", path)

    def lock_path(self, path: str) -> None:
        logger.info("lock_path(path=%r)", path)

    def get_all_quotas(self) -> list[StorageQuotaDTO]:
        logger.info("get_all_quotas()")
        return []

    # --- Optional snapshot methods ---

    def apply_snapshot_policy(self, path: str, policy: dict) -> None:
        logger.info("apply_snapshot_policy(path=%r, policy=%r)", path, policy)

    def remove_snapshot_policy(self, path: str) -> None:
        logger.info("remove_snapshot_policy(path=%r)", path)

    def get_snapshot_status(self, path: str) -> Optional[dict]:
        logger.info("get_snapshot_status(path=%r)", path)
        return None
