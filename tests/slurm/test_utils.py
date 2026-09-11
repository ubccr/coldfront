# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the shared Slurm utility functions (``coldfront.slurm.utils``).

Organized by test class:

- ``TestBuildClient`` — client factory from settings (SLURMRESTD_CLUSTERS dict)
- ``TestSlurmrestdConfigured`` — per-cluster slurmrestd-configured gate
- ``TestGetActiveAssociations`` — active-association lookup
"""

import copy
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation
from coldfront.ras.models.projects import Project
from coldfront.slurm.client.versions import supported_slurm_versions
from coldfront.slurm.models import SlurmAccount, SlurmAssociation, SlurmCluster, SlurmPartition
from coldfront.slurm.utils import build_client, get_active_associations, slurmrestd_configured
from coldfront.users.models import User

_DEFAULT_CLUSTERS_CONFIG = {
    "default": {
        "url": "",
        "jwt_token": "",
        "version": "",
        "auth_type": "jwt",
        "timeout": 30,
        "retries": 3,
        "retry_backoff": 1.5,
    },
}

_LIVE_CLUSTERS_CONFIG = {
    "default": {
        "url": "http://mock:8080",
        "jwt_token": "token",
        "version": supported_slurm_versions()[1],
        "auth_type": "jwt",
        "timeout": 30,
        "retries": 3,
        "retry_backoff": 1.5,
    },
}


# ======================================================================
# 1. Build client
# ======================================================================


class TestBuildClient(TestCase):
    """Test build_client factory with SLURMRESTD_CLUSTERS dict."""

    def test_raises_when_url_empty(self):
        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _DEFAULT_CLUSTERS_CONFIG
            with self.assertRaises(ImproperlyConfigured):
                build_client()

    def test_raises_when_discovery_fails(self):
        config = copy.deepcopy(_LIVE_CLUSTERS_CONFIG)
        config["default"]["version"] = ""  # triggers version discovery

        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = config

        with mock.patch(
            "coldfront.slurm.utils.SlurmClient.discover_version",
            side_effect=RuntimeError("no compatible version"),
        ):
            with self.assertRaises(ImproperlyConfigured):
                build_client()

    def test_returns_client_when_version_set(self):
        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = _LIVE_CLUSTERS_CONFIG

            from coldfront.slurm.client import SlurmClient

            client = build_client()
            assert client is not None
            assert isinstance(client, SlurmClient)
            assert client.version == supported_slurm_versions()[1]

    def test_returns_client_for_named_cluster(self):
        """When cluster name matches a key in SLURMRESTD_CLUSTERS, use it."""
        clusters_config = {
            "default": {
                "url": "",
                "jwt_token": "",
                "version": "",
            },
            "hpc01": {
                "url": "http://hpc01-restd:8080",
                "jwt_token": "hpc01-token",
                "version": supported_slurm_versions()[1],
            },
        }

        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config

            from coldfront.slurm.client import SlurmClient

            client = build_client(cluster="hpc01")
            assert client is not None
            assert isinstance(client, SlurmClient)
            assert client.version == supported_slurm_versions()[1]

    def test_falls_back_to_default_when_cluster_not_listed(self):
        """Cluster name missing from dict falls back to 'default' entry."""
        clusters_config = {
            "default": {
                "url": "http://default-restd:8080",
                "jwt_token": "default-token",
                "version": supported_slurm_versions()[1],
            },
        }

        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = clusters_config

            from coldfront.slurm.client import SlurmClient

            client = build_client(cluster="unknown-cluster")
            assert client is not None
            assert isinstance(client, SlurmClient)
            # Should use default's URL
            assert client.base_url == "http://default-restd:8080"


# ======================================================================
# 2. slurmrestd-configured gate
# ======================================================================


class TestSlurmrestdConfigured(TestCase):
    """slurmrestd_configured checks per-cluster url, defaulting to 'default'."""

    def test_true_when_url_present(self):
        config = {"default": {"url": "http://mock:8080"}}
        cluster = SlurmCluster.objects.create(name="hpc01")
        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = config
            assert slurmrestd_configured(cluster) is True

    def test_false_when_url_empty(self):
        config = {"default": {"url": ""}}
        cluster = SlurmCluster.objects.create(name="hpc01")
        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = config
            assert slurmrestd_configured(cluster) is False

    def test_falls_back_to_default_when_cluster_not_listed(self):
        config = {"default": {"url": "http://mock:8080"}}
        cluster = SlurmCluster.objects.create(name="hpc99")
        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = config
            assert slurmrestd_configured(cluster) is True

    def test_cluster_specific_entry(self):
        config = {"default": {"url": ""}, "hpc01": {"url": "http://mock:8080"}}
        cluster = SlurmCluster.objects.create(name="hpc01")
        with mock.patch("coldfront.slurm.utils.settings") as mock_settings:
            mock_settings.SLURMRESTD_CLUSTERS = config
            assert slurmrestd_configured(cluster) is True


# ======================================================================
# 3. Active associations
# ======================================================================


class TestGetActiveAssociations(TestCase):
    """get_active_associations returns active, slurm-accounted associations."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="alice")
        cls.project = Project.objects.create(name="Lab", owner=cls.user)
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.partition = SlurmPartition.objects.create(name="gpu", cluster=cls.cluster)
        cls.cluster_ct = ContentType.objects.get_for_model(SlurmCluster)
        cls.partition_ct = ContentType.objects.get_for_model(SlurmPartition)
        cls.account = SlurmAccount.objects.create(name="acct-a", cluster=cls.cluster)

    def _active_allocation(self, resource, ct):
        return Allocation.objects.create(
            project=self.project,
            owner=self.user,
            resource_object_type=ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )

    def test_returns_cluster_and_partition_assocs_with_account(self):
        alloc1 = self._active_allocation(self.cluster, self.cluster_ct)
        SlurmAssociation.objects.create(allocation=alloc1, slurm_account=self.account)
        alloc2 = self._active_allocation(self.partition, self.partition_ct)
        SlurmAssociation.objects.create(allocation=alloc2, slurm_account=self.account)

        assocs = get_active_associations(self.cluster)
        assert len(assocs) == 2

    def test_excludes_null_account_and_inactive(self):
        # inactive allocation -> excluded
        alloc = Allocation.objects.create(
            project=self.project,
            owner=self.user,
            resource_object_type=self.cluster_ct,
            resource_object_id=self.cluster.pk,
            status=AllocationStatusChoices.STATUS_REQUESTED,
        )
        SlurmAssociation.objects.create(allocation=alloc, slurm_account=self.account)
        # active but null slurm_account -> excluded
        alloc2 = self._active_allocation(self.cluster, self.cluster_ct)
        SlurmAssociation.objects.create(allocation=alloc2)

        assert get_active_associations(self.cluster) == []

    def test_ignores_other_cluster_partitions(self):
        other = SlurmCluster.objects.create(name="hpc02")
        other_part = SlurmPartition.objects.create(name="gpu", cluster=other)
        alloc = self._active_allocation(other, self.cluster_ct)
        SlurmAssociation.objects.create(allocation=alloc, slurm_account=self.account)
        alloc2 = self._active_allocation(other_part, self.partition_ct)
        SlurmAssociation.objects.create(allocation=alloc2, slurm_account=self.account)

        assert get_active_associations(self.cluster) == []
