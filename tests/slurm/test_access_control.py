# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Slurm access-control sync engine (``coldfront.slurm.sync.access_control``).

Organized by test class:

- ``TestSyncReport`` — dataclass structure
- ``TestBuildHelpers`` — ``_build_config_payload`` and ``_build_expected_tuples``
- ``TestBuildGrpTresMins`` — GrpTresMins SU-grant emission
- ``TestOrphanSweep`` — user/account/QOS orphan cleanup (scoped to ColdFront)
- ``TestSyncClusters`` — ``sync_slurm_clusters`` integration
- ``TestQosSync`` — QOS-definition serialization + upsert

``_sync_cluster`` create-order/orphan-sweep orchestration is covered by the
live e2e suite (``tests/e2e/slurm/test_sync.py``), not mocked here.
"""

from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from coldfront.slurm.models import SlurmAccount, SlurmCluster, SlurmQOS
from coldfront.slurm.sync.access_control import (
    SyncReport,
    _build_account_assoc_payload,
    _build_config_payload,
    _build_expected_tuples,
    _serialize_qos_record,
    _sweep_orphan_accounts,
    _sweep_orphan_associations,
    _sweep_orphan_qos,
    _sweep_orphan_users,
    _sync_cluster,
    _sync_qos_definitions,
    sync_slurm_clusters,
)
from coldfront.users.models import User

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
        assert r.users_deleted == 0
        assert r.qos_deleted == 0
        assert r.jobs_killed == 0
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
            users_deleted=1,
            accounts_deleted=1,
            qos_deleted=2,
            jobs_killed=1,
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
        assert r.users_deleted == 1
        assert r.accounts_deleted == 1
        assert r.qos_deleted == 2
        assert r.jobs_killed == 1
        assert r.errors == ["err1"]
        assert r.warnings == ["warn1"]
        assert r.duration_ms == 500


# ======================================================================
# 2. Build helpers
# ======================================================================


class TestBuildHelpers(TestCase):
    """Test _build_config_payload and _build_expected_tuples."""

    def test_build_config_no_active_assocs_returns_none(self):
        with mock.patch(
            "coldfront.slurm.sync.access_control.get_active_associations",
            return_value=[],
        ):
            result = _build_config_payload(mock.MagicMock())
            assert result is None

    def test_build_expected_no_active_assocs_empty_set(self):
        with mock.patch(
            "coldfront.slurm.sync.access_control.get_active_associations",
            return_value=[],
        ):
            result = _build_expected_tuples(mock.MagicMock())
            assert result == set()

    def test_build_expected_skips_assocs_with_null_account(self):
        mock_assoc = mock.MagicMock()
        mock_assoc.slurm_account = None
        with mock.patch(
            "coldfront.slurm.sync.access_control.get_active_associations",
            return_value=[mock_assoc],
        ):
            result = _build_expected_tuples(mock.MagicMock())
            assert result == set()


class TestBuildGrpTresMins(TestCase):
    """GrpTresMins SU-grant emission: account payload + config integration."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.account = SlurmAccount.objects.create(
            name="acct-a",
            cluster=cls.cluster,
            service_units=10000,
        )

    def test_emits_grptresmins_when_enforced(self):
        self.cluster.enforce_su_limits = True
        self.cluster.save()
        # tres_list array form — the live API rejects the dict form (9208)
        assert _build_account_assoc_payload(self.account, self.cluster) == {
            "grptresmins": [{"type": "billing", "count": 600000}]
        }

    def test_none_when_not_enforced_or_no_grant(self):
        # not enforced -> None
        assert _build_account_assoc_payload(self.account, self.cluster) is None
        # enforced but no service_units grant -> None
        self.cluster.enforce_su_limits = True
        self.cluster.save()
        grantless = SlurmAccount.objects.create(name="acct-b", cluster=self.cluster)
        assert _build_account_assoc_payload(grantless, self.cluster) is None

    def _mock_active_assoc(self):
        """A mock active association carrying self.account but no project users."""
        mock_assoc = mock.MagicMock()
        mock_assoc.slurm_account_id = self.account.pk
        mock_allocation = mock.MagicMock()
        mock_allocation.project = mock.MagicMock()
        mock_allocation.project.users.all.return_value = []
        mock_assoc.allocation = mock_allocation
        mock_assoc.allocation.resource_object = None
        return mock_assoc

    def test_config_includes_grant_when_enforced_else_parent_only(self):
        self.cluster.enforce_su_limits = True
        self.cluster.save()
        with mock.patch(
            "coldfront.slurm.sync.access_control.get_active_associations",
            return_value=[self._mock_active_assoc()],
        ):
            payload = _build_config_payload(self.cluster)
        assert payload is not None
        # grant attached to the account-level parent
        assert any(
            a.get("user") == "" and a.get("grptresmins") == [{"type": "billing", "count": 600000}]
            for a in payload["associations"]
        )

        # Not enforced: parent always emitted, grant conditional -> absent
        self.cluster.enforce_su_limits = False
        self.cluster.save()
        with mock.patch(
            "coldfront.slurm.sync.access_control.get_active_associations",
            return_value=[self._mock_active_assoc()],
        ):
            payload = _build_config_payload(self.cluster)
        assert payload is not None
        assert any(a.get("user") == "" for a in payload["associations"])
        assert not any(a.get("user") == "" and a.get("grptresmins") for a in payload["associations"])


# ======================================================================
# 4. Orphan sweep
# ======================================================================


class TestOrphanSweep(TestCase):
    """Test the orphan sweep: association kill+delete, and the scoped
    user/account/QOS cleanup."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_association_sweep_kills_jobs_and_deletes(self):
        mock_client = mock.MagicMock()
        mock_client.get_associations.return_value = {
            "associations": [
                {"account": "acct-a", "user": "alice", "cluster": "hpc01", "partition": "gpu"},
                {"account": "acct-a", "user": "alice", "cluster": "hpc01", "partition": "cpu"},
            ]
        }
        report = SyncReport(cluster="hpc01")
        with mock.patch(
            "coldfront.slurm.sync.access_control._build_expected_tuples",
            return_value={("acct-a", "alice", "cpu")},
        ):
            kept_users, kept_accounts = _sweep_orphan_associations(mock_client, self.cluster, report)
        assert report.associations_deleted == 1
        assert report.jobs_killed == 1
        assert kept_users == {"alice"}
        assert kept_accounts == {"acct-a"}
        mock_client.kill_jobs.assert_called_once()
        # the orphaned (gpu) assoc deleted; the kept (cpu) assoc kept
        mock_client.delete_associations.assert_called_once_with("acct-a", "alice", "hpc01", "gpu")

    def test_association_sweep_keeps_parents(self):
        mock_client = mock.MagicMock()
        mock_client.get_associations.return_value = {
            "associations": [
                {"account": "acct-a", "user": "", "cluster": "hpc01", "partition": ""},
            ]
        }
        report = SyncReport(cluster="hpc01")
        with mock.patch(
            "coldfront.slurm.sync.access_control._build_expected_tuples",
            return_value=set(),
        ):
            kept_users, kept_accounts = _sweep_orphan_associations(mock_client, self.cluster, report)
        assert report.associations_deleted == 0
        assert kept_users == set()
        assert kept_accounts == set()
        mock_client.delete_associations.assert_not_called()

    def test_association_sweep_query_failure_records_error(self):
        mock_client = mock.MagicMock()
        mock_client.get_associations.side_effect = Exception("boom")
        report = SyncReport(cluster="hpc01")
        kept_users, kept_accounts = _sweep_orphan_associations(mock_client, self.cluster, report)
        assert report.errors == ["Failed to query existing associations: boom"]
        assert kept_users == set()

    def test_user_sweep_deletes_coldfront_user_keeps_system(self):
        User.objects.create(username="alice")
        mock_client = mock.MagicMock()
        mock_client.get_users.return_value = {"users": [{"name": "alice"}, {"name": "root"}]}
        report = SyncReport(cluster="hpc01")
        _sweep_orphan_users(mock_client, self.cluster, report, kept_users=set())
        assert report.users_deleted == 1
        mock_client.delete_user.assert_called_once_with("alice", "hpc01")

    def test_user_sweep_keeps_users_with_expected_assoc(self):
        User.objects.create(username="alice")
        mock_client = mock.MagicMock()
        mock_client.get_users.return_value = {"users": [{"name": "alice"}]}
        report = SyncReport(cluster="hpc01")
        _sweep_orphan_users(mock_client, self.cluster, report, kept_users={"alice"})
        assert report.users_deleted == 0
        mock_client.delete_user.assert_not_called()

    def test_account_sweep_deletes_coldfront_account_keeps_other(self):
        SlurmAccount.objects.create(name="acct-a", cluster=self.cluster)
        mock_client = mock.MagicMock()
        mock_client.get_accounts.return_value = {"accounts": [{"name": "acct-a"}, {"name": "root"}]}
        report = SyncReport(cluster="hpc01")
        _sweep_orphan_accounts(mock_client, self.cluster, report, kept_accounts=set())
        assert report.accounts_deleted == 1
        mock_client.delete_account.assert_called_once_with("acct-a", "hpc01")

    def test_account_sweep_keeps_accounts_with_expected_assoc(self):
        SlurmAccount.objects.create(name="acct-a", cluster=self.cluster)
        mock_client = mock.MagicMock()
        mock_client.get_accounts.return_value = {"accounts": [{"name": "acct-a"}]}
        report = SyncReport(cluster="hpc01")
        _sweep_orphan_accounts(mock_client, self.cluster, report, kept_accounts={"acct-a"})
        assert report.accounts_deleted == 0
        mock_client.delete_account.assert_not_called()

    def test_qos_sweep_deletes_orphan(self):
        SlurmQOS.objects.create(name="keep")
        mock_client = mock.MagicMock()
        mock_client.get_qos.return_value = {"qos": [{"name": "keep"}, {"name": "orphan"}]}
        # No live association references the orphan QOS.
        mock_client.get_associations.return_value = {"associations": []}
        report = SyncReport(cluster="hpc01")
        _sweep_orphan_qos(mock_client, self.cluster, report)
        assert report.qos_deleted == 1
        mock_client.delete_qos.assert_called_once_with("orphan")

    def test_qos_sweep_keeps_referenced_orphan(self):
        """A QOS referenced by a live association (e.g. a stock system QOS on
        a root assoc) is never deleted — removing it destabilizes slurmdbd."""
        mock_client = mock.MagicMock()
        mock_client.get_qos.return_value = {"qos": [{"name": "normal"}, {"name": "orphan"}]}
        mock_client.get_associations.return_value = {
            "associations": [{"account": "root", "user": "", "qos": ["normal"]}]
        }
        report = SyncReport(cluster="hpc01")
        _sweep_orphan_qos(mock_client, self.cluster, report)
        assert report.qos_deleted == 1  # only the unreferenced orphan is deleted
        mock_client.delete_qos.assert_called_once_with("orphan")

    def test_orphan_sweep_skips_users_accounts_qos_when_errors(self):
        """When association cleanup reports errors, user/account/QOS sweeps are
        skipped (creation may be incomplete)."""
        mock_client = mock.MagicMock()
        mock_client.get_associations.side_effect = Exception("boom")
        report = SyncReport(cluster="hpc01")
        with mock.patch(
            "coldfront.slurm.sync.access_control._build_expected_tuples",
            return_value=set(),
        ):
            _sweep_orphan_associations(mock_client, self.cluster, report)
        # _orphan_sweep is the orchestrator; verify the guard skips downstream
        from coldfront.slurm.sync.access_control import _orphan_sweep

        mock_client.get_users.side_effect = Exception("should not be called")
        _orphan_sweep(mock_client, self.cluster, report)
        assert report.users_deleted == 0
        assert report.accounts_deleted == 0
        assert report.qos_deleted == 0


# ======================================================================
# 5. sync_slurm_clusters integration
# ======================================================================


class TestSyncClusters(TestCase):
    """Test sync_slurm_clusters integration."""

    def test_db_ensure_always_runs_and_report_passed_through(self):
        """DB catch-up runs, then each cluster's _sync_cluster report is passed
        through to the caller."""
        cluster = mock.MagicMock(spec=SlurmCluster)
        cluster.name = "hpc01"
        with mock.patch("coldfront.slurm.sync.access_control.SlurmCluster") as mock_cluster:
            mock_cluster.objects.all.return_value = [cluster]
            with mock.patch("coldfront.slurm.sync.access_control._ensure_slurm_users_for_cluster") as mock_db:
                with mock.patch("coldfront.slurm.sync.access_control._sync_cluster") as mock_sync:
                    mock_sync.return_value = SyncReport(
                        cluster="hpc01",
                        success=True,
                        warnings=["nothing to upsert"],
                        associations_deleted=1,
                    )
                    reports = sync_slurm_clusters()
        assert len(reports) == 1
        assert reports[0].success
        assert "nothing to upsert" in reports[0].warnings[0]
        assert reports[0].associations_deleted == 1
        mock_db.assert_called_once()  # (1) DB reconcile always runs

    def test_filters_by_cluster_names(self):
        """Only clusters in cluster_names are synced."""
        c1 = SlurmCluster.objects.create(name="hpc01")
        SlurmCluster.objects.create(name="hpc02")
        with mock.patch("coldfront.slurm.sync.access_control._ensure_slurm_users_for_cluster"):
            with mock.patch("coldfront.slurm.sync.access_control._sync_cluster") as mock_sync:
                mock_sync.return_value = SyncReport(cluster="hpc01", success=True)
                reports = sync_slurm_clusters(["hpc01"])
        assert len(reports) == 1
        assert mock_sync.call_args[0][0] == c1
        mock_sync.assert_called_once()

    def test_unconfigured_cluster_yields_error_report(self):
        """_sync_cluster surfaces ImproperlyConfigured as a failed report."""
        cluster = mock.MagicMock(spec=SlurmCluster)
        cluster.name = "hpc01"
        with mock.patch(
            "coldfront.slurm.sync.access_control.build_client",
            side_effect=ImproperlyConfigured("no url"),
        ):
            with mock.patch("coldfront.slurm.sync.access_control._ensure_slurm_users_for_cluster"):
                report = _sync_cluster(cluster)
        assert not report.success
        assert "not configured" in report.errors[0]


# ======================================================================
# 6. QOS sync
# ======================================================================


class TestQosSync(TestCase):
    """Test the QOS-definition sync: serialization + full-sync upsert step."""

    def test_serialize_qos_record_nested_schema(self):
        """_serialize_qos_record maps a SlurmQOS to the nested qos_rec wire format."""
        qos = SlurmQOS.objects.create(
            name="normal",
            description="test",
            priority=10,
            limit_factor=0.5,
            max_submit_jobs_per_user=5,
            max_jobs_per_user=7,
            max_submit_jobs_per_account=6,
            max_jobs_per_account=8,
            grace_time=60,
        )
        body = _serialize_qos_record(qos)
        assert body["name"] == "normal"
        assert body["description"] == "test"
        assert body["priority"] == 10
        limits = body["limits"]
        assert limits["grace_time"] == 60
        assert limits["factor"] == 0.5
        assert limits["max"]["jobs"]["per"]["user"] == 5
        assert limits["max"]["jobs"]["active_jobs"]["per"]["user"] == 7
        assert limits["max"]["jobs"]["per"]["account"] == 6
        assert limits["max"]["jobs"]["active_jobs"]["per"]["account"] == 8
        # no max wall time set -> no wall_clock path
        assert "wall_clock" not in limits["max"]

    def test_serialize_qos_record_skips_unset_and_unlimited(self):
        """Unset fields are omitted; UNLIMITED wall time is skipped."""
        qos = SlurmQOS.objects.create(name="bare")
        body = _serialize_qos_record(qos)
        assert "description" not in body
        assert "limits" not in body

        qos.max_wall_duration_per_job = None  # UNLIMITED (empty SlurmTime)
        qos.save()
        body = _serialize_qos_record(qos)
        assert "limits" not in body

    def test_sync_qos_definitions_upserts_all(self):
        """_sync_qos_definitions serializes every record and calls upsert_qos."""
        SlurmQOS.objects.create(name="a")
        SlurmQOS.objects.create(name="b")
        mock_client = mock.MagicMock()
        _sync_qos_definitions(mock_client)
        mock_client.upsert_qos.assert_called_once()
        payload = mock_client.upsert_qos.call_args.args[0]
        assert [p["name"] for p in payload] == ["a", "b"]

    def test_sync_qos_definitions_empty(self):
        """No records -> upsert_qos is not called."""
        mock_client = mock.MagicMock()
        _sync_qos_definitions(mock_client)
