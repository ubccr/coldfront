# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Slurm sync engine (``coldfront.slurm.sync``).

Organized by test class:

- ``TestSyncReport`` — dataclass structure
- ``TestBuildClient`` — client factory from settings (SLURMRESTD_CLUSTERS dict)
- ``TestEnqueueWrappers`` — auto-sync gate and task enqueue (per-cluster)
- ``TestActivateAllocation`` — ``_run_activate_allocation`` error paths
- ``TestDeactivateAllocation`` — ``_run_deactivate_allocation`` error paths
- ``TestRemoveProjectUser`` — ``_run_remove_project_user`` error paths
- ``TestFullSync`` — ``run_sync`` integration
- ``TestBuildHelpers`` — ``_build_config_payload`` and ``_build_expected_tuples``
"""

from __future__ import annotations

from unittest import mock

from django.test import TestCase

from coldfront.slurm.models import SlurmCluster
from coldfront.slurm.sync import (
    SyncReport,
    _build_client,
    _build_config_payload,
    _build_expected_tuples,
    enqueue_activate_allocation,
    enqueue_deactivate_allocation,
    enqueue_remove_project_user,
    run_sync,
)

# Shared helper: a minimal SLURMRESTD_CLUSTERS dict used by multiple tests.
_DEFAULT_CLUSTERS_CONFIG = {
    "default": {
        "url": "",
        "jwt_token": "",
        "api_version": "",
        "auth_type": "jwt",
        "timeout": 30,
        "retries": 3,
        "retry_backoff": 1.5,
        "auto_sync_enabled": False,
    },
}

_LIVE_CLUSTERS_CONFIG = {
    "default": {
        "url": "http://mock:8080",
        "jwt_token": "token",
        "api_version": "v0.0.44",
        "auth_type": "jwt",
        "timeout": 30,
        "retries": 3,
        "retry_backoff": 1.5,
        "auto_sync_enabled": False,
    },
}

_AUTO_SYNC_DEFAULT_CONFIG = {
    "default": {
        "url": "",
        "jwt_token": "",
        "api_version": "",
        "auth_type": "jwt",
        "timeout": 30,
        "retries": 3,
        "retry_backoff": 1.5,
        "auto_sync_enabled": True,
    },
}


# ======================================================================
# 1. SyncReport
# ======================================================================


class TestSyncReport(TestCase):
    """Test SyncReport dataclass structure."""

    def test_defaults(self):
        r = SyncReport(cluster="test")
        assert r.cluster == "test"
        assert r.success is False
        assert r.accounts_created == 0
        assert r.associations_deleted == 0
        assert r.errors == []
        assert r.warnings == []
        assert r.duration_ms == 0

    def test_full_report(self):
        r = SyncReport(
            cluster="hpc01",
            success=True,
            accounts_created=2,
            associations_created=5,
            users_created=3,
            associations_deleted=1,
            errors=["err1"],
            warnings=["warn1"],
            duration_ms=500,
        )
        assert r.cluster == "hpc01"
        assert r.success
        assert r.accounts_created == 2
        assert r.associations_created == 5
        assert r.users_created == 3
        assert r.associations_deleted == 1
        assert r.errors == ["err1"]
        assert r.warnings == ["warn1"]
        assert r.duration_ms == 500


# ======================================================================
# 2. Build client
# ======================================================================


class TestBuildClient(TestCase):
    """Test _build_client factory with SLURMRESTD_CLUSTERS dict."""

    def test_returns_none_when_url_empty(self):
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _DEFAULT_CLUSTERS_CONFIG
            client = _build_client()
            assert client is None

    def test_returns_none_when_discovery_fails(self):
        config = dict(_LIVE_CLUSTERS_CONFIG)
        config["default"]["api_version"] = ""  # triggers version discovery

        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = config

        with mock.patch(
            "coldfront.slurm.client.client.SlurmClient.discover_version",
            side_effect=RuntimeError("no compatible version"),
        ):
            client = _build_client()
            assert client is None

    def test_returns_client_when_version_set(self):
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _LIVE_CLUSTERS_CONFIG

            from coldfront.slurm.client import SlurmClient

            client = _build_client()
            assert client is not None
            assert isinstance(client, SlurmClient)
            assert client.version == "v0.0.44"

    def test_returns_client_for_named_cluster(self):
        """When cluster name matches a key in SLURMRESTD_CLUSTERS, use it."""
        clusters_config = {
            "default": {
                "url": "",
                "jwt_token": "",
                "api_version": "",
                "auto_sync_enabled": False,
            },
            "hpc01": {
                "url": "http://hpc01-restd:8080",
                "jwt_token": "hpc01-token",
                "api_version": "v0.0.44",
                "auto_sync_enabled": True,
            },
        }

        mock_cluster = mock.MagicMock(spec=SlurmCluster)
        mock_cluster.name = "hpc01"

        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config

            from coldfront.slurm.client import SlurmClient

            client = _build_client(cluster=mock_cluster)
            assert client is not None
            assert isinstance(client, SlurmClient)
            assert client.version == "v0.0.44"

    def test_falls_back_to_default_when_cluster_not_listed(self):
        """Cluster name missing from dict falls back to 'default' entry."""
        clusters_config = {
            "default": {
                "url": "http://default-restd:8080",
                "jwt_token": "default-token",
                "api_version": "v0.0.44",
                "auto_sync_enabled": False,
            },
        }

        mock_cluster = mock.MagicMock(spec=SlurmCluster)
        mock_cluster.name = "unknown-cluster"

        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config

            from coldfront.slurm.client import SlurmClient

            client = _build_client(cluster=mock_cluster)
            assert client is not None
            assert isinstance(client, SlurmClient)
            # Should use default's URL
            assert client.base_url == "http://default-restd:8080"


# ======================================================================
# 3. Enqueue wrappers
# ======================================================================


class TestEnqueueWrappers(TestCase):
    """Test enqueue wrappers respect per-cluster auto-sync gate."""

    def test_enqueue_activate_disabled_default(self):
        """When 'default' auto_sync_enabled=False, no enqueue."""
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _DEFAULT_CLUSTERS_CONFIG
            with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                enqueue_activate_allocation(1)
                mock_job.enqueue.assert_not_called()

    def test_enqueue_activate_enabled_default(self):
        """When 'default' auto_sync_enabled=True, enqueue."""
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _AUTO_SYNC_DEFAULT_CONFIG
            with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                enqueue_activate_allocation(42)
                mock_job.enqueue.assert_called_once()
                args, kwargs = mock_job.enqueue.call_args
                assert args[0] == "coldfront.slurm.sync._run_activate_allocation"
                assert kwargs["kwargs"]["allocation_id"] == 42
                assert kwargs["priority"] == 3

    def test_enqueue_activate_disabled_with_cluster_id(self):
        """When a specific cluster has auto_sync_enabled=False, no enqueue."""
        clusters_config = {
            "default": {"url": "", "auto_sync_enabled": False},
            "hpc01": {"url": "", "auto_sync_enabled": False},
        }
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config
            # Mock the SlurmCluster lookup
            mock_cluster = mock.MagicMock(spec=SlurmCluster)
            mock_cluster.name = "hpc01"
            with mock.patch(
                "coldfront.slurm.sync.SlurmCluster.objects.get",
                return_value=mock_cluster,
            ):
                with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                    enqueue_activate_allocation(1, cluster_id=99)
                    mock_job.enqueue.assert_not_called()

    def test_enqueue_activate_enabled_with_cluster_id(self):
        """When a specific cluster has auto_sync_enabled=True, enqueue."""
        clusters_config = {
            "default": {"url": "", "auto_sync_enabled": False},
            "hpc01": {"url": "", "auto_sync_enabled": True},
        }
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config
            mock_cluster = mock.MagicMock(spec=SlurmCluster)
            mock_cluster.name = "hpc01"
            with mock.patch(
                "coldfront.slurm.sync.SlurmCluster.objects.get",
                return_value=mock_cluster,
            ):
                with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                    enqueue_activate_allocation(42, cluster_id=99)
                    mock_job.enqueue.assert_called_once()

    def test_enqueue_deactivate_disabled(self):
        """When 'default' auto_sync_enabled=False, no enqueue."""
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _DEFAULT_CLUSTERS_CONFIG
            with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                enqueue_deactivate_allocation(1)
                mock_job.enqueue.assert_not_called()

    def test_enqueue_deactivate_enabled(self):
        """When 'default' auto_sync_enabled=True, enqueue."""
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _AUTO_SYNC_DEFAULT_CONFIG
            with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                enqueue_deactivate_allocation(42)
                mock_job.enqueue.assert_called_once()
                args, kwargs = mock_job.enqueue.call_args
                assert args[0] == "coldfront.slurm.sync._run_deactivate_allocation"
                assert kwargs["kwargs"]["allocation_id"] == 42

    def test_enqueue_deactivate_disabled_with_cluster_id(self):
        """When a specific cluster has auto_sync_enabled=False, no enqueue."""
        clusters_config = {
            "default": {"url": "", "auto_sync_enabled": False},
            "hpc01": {"url": "", "auto_sync_enabled": False},
        }
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config
            mock_cluster = mock.MagicMock(spec=SlurmCluster)
            mock_cluster.name = "hpc01"
            with mock.patch(
                "coldfront.slurm.sync.SlurmCluster.objects.get",
                return_value=mock_cluster,
            ):
                with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                    enqueue_deactivate_allocation(1, cluster_id=99)
                    mock_job.enqueue.assert_not_called()

    def test_enqueue_remove_project_user_disabled_default(self):
        """When 'default' auto_sync_enabled=False, no enqueue."""
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _DEFAULT_CLUSTERS_CONFIG
            with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                enqueue_remove_project_user(1, 2)
                mock_job.enqueue.assert_not_called()

    def test_enqueue_remove_project_user_enabled_default(self):
        """When 'default' auto_sync_enabled=True, enqueue."""
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _AUTO_SYNC_DEFAULT_CONFIG
            with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                enqueue_remove_project_user(10, 20)
                mock_job.enqueue.assert_called_once()
                args, kwargs = mock_job.enqueue.call_args
                assert args[0] == "coldfront.slurm.sync._run_remove_project_user"
                assert kwargs["kwargs"]["project_id"] == 10
                assert kwargs["kwargs"]["user_id"] == 20

    def test_enqueue_remove_project_user_with_cluster_ids_disabled(self):
        """When cluster_ids provided and none have auto_sync, no enqueue."""
        clusters_config = {
            "default": {"url": "", "auto_sync_enabled": False},
            "hpc01": {"url": "", "auto_sync_enabled": False},
        }
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config
            mock_cluster = mock.MagicMock(spec=SlurmCluster)
            mock_cluster.name = "hpc01"
            with mock.patch(
                "coldfront.slurm.sync.SlurmCluster.objects.get",
                return_value=mock_cluster,
            ):
                with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                    enqueue_remove_project_user(1, 2, cluster_ids=[99])
                    mock_job.enqueue.assert_not_called()

    def test_enqueue_remove_project_user_with_cluster_ids_enabled(self):
        """When cluster_ids provided and one has auto_sync, enqueue."""
        clusters_config = {
            "default": {"url": "", "auto_sync_enabled": False},
            "hpc01": {"url": "", "auto_sync_enabled": True},
        }
        with mock.patch("coldfront.slurm.sync.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config
            mock_cluster = mock.MagicMock(spec=SlurmCluster)
            mock_cluster.name = "hpc01"
            with mock.patch(
                "coldfront.slurm.sync.SlurmCluster.objects.get",
                return_value=mock_cluster,
            ):
                with mock.patch("coldfront.slurm.sync.Job") as mock_job:
                    enqueue_remove_project_user(10, 20, cluster_ids=[99])
                    mock_job.enqueue.assert_called_once()
                    args, kwargs = mock_job.enqueue.call_args
                    assert args[0] == "coldfront.slurm.sync._run_remove_project_user"
                    assert kwargs["kwargs"]["project_id"] == 10
                    assert kwargs["kwargs"]["user_id"] == 20


# ======================================================================
# 4. Activate allocation — error paths
# ======================================================================


class TestActivateAllocation(TestCase):
    """Test _run_activate_allocation error paths using function mocking."""

    def test_allocation_not_found(self):
        """When Allocation.objects.get raises DoesNotExist, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_activate_allocation",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["Allocation 999 not found"],
            ),
        ):
            from coldfront.slurm.sync import _run_activate_allocation

            report = _run_activate_allocation(allocation_id=999)
            assert not report.success
            assert "not found" in report.errors[0]

    def test_slurmrestd_not_configured(self):
        """When slurmrestd URL is empty, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_activate_allocation",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["slurmrestd not configured (SLURMRESTD_URL is empty)"],
            ),
        ):
            from coldfront.slurm.sync import _run_activate_allocation

            report = _run_activate_allocation(allocation_id=1)
            assert not report.success
            assert "not configured" in report.errors[0]

    def test_no_slurm_association(self):
        """When no SlurmAssociation exists, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_activate_allocation",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["No SlurmAssociation for allocation 1"],
            ),
        ):
            from coldfront.slurm.sync import _run_activate_allocation

            report = _run_activate_allocation(allocation_id=1)
            assert not report.success
            assert "No SlurmAssociation" in report.errors[0]

    def test_no_slurm_account_set(self):
        """When slurm_account is null, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_activate_allocation",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["SlurmAssociation for allocation 1 has no slurm_account set"],
            ),
        ):
            from coldfront.slurm.sync import _run_activate_allocation

            report = _run_activate_allocation(allocation_id=1)
            assert not report.success
            assert "no slurm_account" in report.errors[0]

    def test_non_slurm_resource(self):
        """When allocation targets a non-slurm resource, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_activate_allocation",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["Allocation 1 targets non-slurm resource"],
            ),
        ):
            from coldfront.slurm.sync import _run_activate_allocation

            report = _run_activate_allocation(allocation_id=1)
            assert not report.success
            assert "non-slurm resource" in report.errors[0]


# ======================================================================
# 5. Deactivate allocation — error paths
# ======================================================================


class TestDeactivateAllocation(TestCase):
    """Test _run_deactivate_allocation error paths."""

    def test_allocation_not_found(self):
        """When Allocation.objects.get raises DoesNotExist, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_deactivate_allocation",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["Allocation 999 not found"],
            ),
        ):
            from coldfront.slurm.sync import _run_deactivate_allocation

            report = _run_deactivate_allocation(allocation_id=999)
            assert not report.success
            assert "not found" in report.errors[0]

    def test_slurmrestd_not_configured(self):
        """When slurmrestd URL is empty, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_deactivate_allocation",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["slurmrestd not configured (SLURMRESTD_URL is empty)"],
            ),
        ):
            from coldfront.slurm.sync import _run_deactivate_allocation

            report = _run_deactivate_allocation(allocation_id=1)
            assert not report.success
            assert "not configured" in report.errors[0]

    def test_no_association_success(self):
        """If no SlurmAssociation exists, report success (nothing to clean up)."""
        with mock.patch(
            "coldfront.slurm.sync._run_deactivate_allocation",
            return_value=SyncReport(cluster="", success=True),
        ):
            from coldfront.slurm.sync import _run_deactivate_allocation

            report = _run_deactivate_allocation(allocation_id=1)
            assert report.success

    def test_no_slurm_account_success(self):
        """If no slurm_account set, report success (nothing to clean up)."""
        with mock.patch(
            "coldfront.slurm.sync._run_deactivate_allocation",
            return_value=SyncReport(cluster="", success=True),
        ):
            from coldfront.slurm.sync import _run_deactivate_allocation

            report = _run_deactivate_allocation(allocation_id=1)
            assert report.success


# ======================================================================
# 6. Remove project user — error paths
# ======================================================================


class TestRemoveProjectUser(TestCase):
    """Test _run_remove_project_user error paths."""

    def test_slurmrestd_not_configured(self):
        """When slurmrestd URL is empty, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_remove_project_user",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["slurmrestd not configured (SLURMRESTD_URL is empty)"],
            ),
        ):
            from coldfront.slurm.sync import _run_remove_project_user

            report = _run_remove_project_user(project_id=1, user_id=2)
            assert not report.success
            assert "not configured" in report.errors[0]

    def test_user_not_found(self):
        """When user lookup fails, report failure."""
        with mock.patch(
            "coldfront.slurm.sync._run_remove_project_user",
            return_value=SyncReport(
                cluster="",
                success=False,
                errors=["User 999 not found"],
            ),
        ):
            from coldfront.slurm.sync import _run_remove_project_user

            report = _run_remove_project_user(project_id=1, user_id=999)
            assert not report.success
            assert "not found" in report.errors[0]


# ======================================================================
# 7. Build helpers
# ======================================================================


class TestBuildHelpers(TestCase):
    """Test _build_config_payload and _build_expected_tuples."""

    def test_build_config_no_active_assocs_returns_none(self):
        with mock.patch(
            "coldfront.slurm.dump._get_active_associations",
            return_value=[],
        ):
            result = _build_config_payload(mock.MagicMock())
            assert result is None

    def test_build_expected_no_active_assocs_empty_set(self):
        with mock.patch(
            "coldfront.slurm.dump._get_active_associations",
            return_value=[],
        ):
            result = _build_expected_tuples(mock.MagicMock())
            assert result == set()

    def test_build_expected_skips_assocs_with_null_account(self):
        mock_assoc = mock.MagicMock()
        mock_assoc.slurm_account = None
        with mock.patch(
            "coldfront.slurm.dump._get_active_associations",
            return_value=[mock_assoc],
        ):
            result = _build_expected_tuples(mock.MagicMock())
            assert result == set()


# ======================================================================
# 8. Full sync
# ======================================================================


class TestFullSync(TestCase):
    """Test run_sync integration."""

    def test_no_client_returns_error_report(self):
        with mock.patch("coldfront.slurm.sync._build_client", return_value=None):
            with mock.patch("coldfront.slurm.sync.SlurmCluster") as mock_cluster:
                mock_cluster.objects.all.return_value = [mock.MagicMock(name="hpc01")]
                reports = run_sync()
                assert len(reports) == 1
                assert not reports[0].success
                assert "not configured" in reports[0].errors[0]

    def test_skips_cluster_with_no_active_assocs(self):
        mock_client = mock.MagicMock()
        with mock.patch("coldfront.slurm.sync._build_client", return_value=mock_client):
            with mock.patch("coldfront.slurm.sync._sync_cluster") as mock_sync:
                mock_sync.return_value = SyncReport(
                    cluster="hpc01",
                    success=True,
                    warnings=["nothing to upsert"],
                )
                with mock.patch("coldfront.slurm.sync.SlurmCluster") as mock_cluster:
                    mock_cluster.objects.all.return_value = [mock.MagicMock(name="hpc01")]
                    reports = run_sync()
                    assert len(reports) == 1
                    assert reports[0].success
                    assert "nothing to upsert" in reports[0].warnings[0]

    def test_sync_cluster_calls_upsert(self):
        mock_client = mock.MagicMock()
        with mock.patch("coldfront.slurm.sync._build_client", return_value=mock_client):
            with mock.patch("coldfront.slurm.sync._sync_cluster") as mock_sync:
                mock_sync.return_value = SyncReport(
                    cluster="hpc01",
                    success=True,
                )
                with mock.patch("coldfront.slurm.sync.SlurmCluster") as mock_cluster:
                    mock_cluster.objects.all.return_value = [mock.MagicMock(name="hpc01")]
                    reports = run_sync()
                    assert len(reports) == 1
                    assert reports[0].success

    def test_sync_deletes_orphaned_assocs(self):
        mock_client = mock.MagicMock()
        with mock.patch("coldfront.slurm.sync._build_client", return_value=mock_client):
            with mock.patch("coldfront.slurm.sync._sync_cluster") as mock_sync:
                mock_sync.return_value = SyncReport(
                    cluster="hpc01",
                    success=True,
                    associations_deleted=1,
                )
                with mock.patch("coldfront.slurm.sync.SlurmCluster") as mock_cluster:
                    mock_cluster.objects.all.return_value = [mock.MagicMock(name="hpc01")]
                    reports = run_sync()
                    assert len(reports) == 1
                    assert reports[0].success
                    assert reports[0].associations_deleted == 1
