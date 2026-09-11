# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for SU billing TRES model helpers."""

from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from coldfront.ras.models import Allocation
from coldfront.ras.models.projects import Project
from coldfront.slurm.choices import (
    SlurmBillingModeChoices,
    SlurmSuEnforcementModeChoices,
)
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAccountUsage,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
)
from coldfront.users.models import User


class BillingModeHelperTestCase(TestCase):
    """SlurmCluster.billing_mode derives from priority_flags."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc")

    def test_default_is_sum(self):
        self.assertEqual(self.cluster.billing_mode(), SlurmBillingModeChoices.MODE_SUM)

    def test_max_tres(self):
        self.cluster.priority_flags = ["MAX_TRES"]
        self.cluster.save()
        self.assertEqual(self.cluster.billing_mode(), SlurmBillingModeChoices.MODE_MAX_TRES)

    def test_max_tres_gres(self):
        self.cluster.priority_flags = ["MAX_TRES_GRES"]
        self.cluster.save()
        self.assertEqual(self.cluster.billing_mode(), SlurmBillingModeChoices.MODE_MAX_TRES_GRES)

    def test_max_tres_takes_precedence(self):
        self.cluster.priority_flags = ["MAX_TRES", "MAX_TRES_GRES"]
        self.cluster.save()
        self.assertEqual(self.cluster.billing_mode(), SlurmBillingModeChoices.MODE_MAX_TRES)

    def test_non_billing_flags_still_sum(self):
        self.cluster.priority_flags = ["NO_NORMAL_TRES", "ACCRUE_ALWAYS"]
        self.cluster.save()
        self.assertEqual(self.cluster.billing_mode(), SlurmBillingModeChoices.MODE_SUM)


class SuEnforcementModeHelperTestCase(TestCase):
    """SlurmCluster.su_enforcement_mode derives from the raw priority settings."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc")

    def test_non_multifactor_is_none(self):
        self.cluster.priority_type = "priority/basic"
        self.cluster.save()
        self.assertEqual(self.cluster.su_enforcement_mode(), SlurmSuEnforcementModeChoices.MODE_NONE)

    def test_multifactor_with_decay(self):
        self.cluster.priority_type = "priority/multifactor"
        self.cluster.priority_decay_half_life = "30-0"
        self.cluster.save()
        self.assertEqual(self.cluster.su_enforcement_mode(), SlurmSuEnforcementModeChoices.MODE_DECAY)

    def test_multifactor_no_decay_no_reset_is_decay(self):
        self.cluster.priority_type = "priority/multifactor"
        self.cluster.priority_decay_half_life = "0-0"
        self.cluster.save()
        self.assertEqual(self.cluster.su_enforcement_mode(), SlurmSuEnforcementModeChoices.MODE_DECAY)

    def test_multifactor_no_decay_with_reset_is_hard(self):
        self.cluster.priority_type = "priority/multifactor"
        self.cluster.priority_decay_half_life = "0-0"
        self.cluster.priority_usage_reset_period = "MONTHLY"
        self.cluster.save()
        self.assertEqual(self.cluster.su_enforcement_mode(), SlurmSuEnforcementModeChoices.MODE_HARD)

    def test_default_multifactor_is_decay(self):
        self.assertEqual(self.cluster.su_enforcement_mode(), SlurmSuEnforcementModeChoices.MODE_DECAY)


class EffectiveTresBillingWeightsTestCase(TestCase):
    """SlurmPartition.effective_tres_billing_weights resolution.

    DEFAULT is absorbed into each partition at parse time, so the cluster
    default fallback is gone: a partition either carries its own weights or
    falls back to {"CPU": 1.0}.
    """

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc")
        cls.partition = SlurmPartition.objects.create(cluster=cls.cluster, name="normal")

    def test_partition_weights_win(self):
        self.partition.tres_billing_weights = {"node": 10}
        self.partition.save()
        self.assertEqual(self.partition.effective_tres_billing_weights(), {"node": 10})

    def test_empty_falls_back_to_cpu_one(self):
        self.assertEqual(self.partition.effective_tres_billing_weights(), {"CPU": 1.0})


class SlurmAccountUsageModelTestCase(TestCase):
    """SlurmAccountUsage model fields + unique constraint."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.account = SlurmAccount.objects.create(
            name="acct-a",
            cluster=cls.cluster,
            service_units=10000,
        )

    def test_row_fields(self):
        row = SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 1),
            billing_units_consumed=10.5,
            billing_units_completed=12.0,
            walltime_sec_consumed=3600,
            walltime_sec_completed=7200,
            node_hours_consumed=4.0,
            node_hours_by_partition={"gpu": 4.0},
            billing_by_qos={"normal": 10.5},
            job_count_consumed=2,
            job_count_completed=1,
        )
        assert row.billing_units_consumed == 10.5
        assert row.node_hours_by_partition == {"gpu": 4.0}
        assert str(row) == "acct-a @ hpc01 2024-01-01"

    def test_unique_per_account_day(self):
        SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 1),
        )
        # Same cluster/account/day must violate the unique constraint
        with self.assertRaises(Exception):
            SlurmAccountUsage.objects.create(
                cluster=self.cluster,
                account=self.account,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 1),
            )

    def test_allows_same_account_different_day(self):
        SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 1),
        )
        row2 = SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 2),
            period_end=date(2024, 1, 2),
        )
        assert row2.pk is not None


class SlurmAccountValidationTestCase(TestCase):
    """SlurmAssociation.clean() account conflict validation."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create(username="Alice")
        cls.project = Project.objects.create(name="Research Lab", owner=cls.user1)

        cls.cluster_a = SlurmCluster.objects.create(name="hpc01")
        cls.cluster_b = SlurmCluster.objects.create(name="hpc02")
        cls.partition_gpu = SlurmPartition.objects.create(name="gpu", cluster=cls.cluster_a)

        cls.account_x = SlurmAccount.objects.create(name="acct-x", cluster=cls.cluster_a)
        cls.account_y = SlurmAccount.objects.create(name="acct-y", cluster=cls.cluster_a)

        cls.cluster_ct = ContentType.objects.get_for_model(SlurmCluster)
        cls.partition_ct = ContentType.objects.get_for_model(SlurmPartition)

    def _make_association(self, resource, resource_ct, account=None):
        """Create an allocation and its SlurmAssociation for a given resource."""
        allocation = Allocation.objects.create(
            justification="test",
            project=self.project,
            owner=self.user1,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
        )
        assoc = SlurmAssociation.objects.create(allocation=allocation)
        if account is not None:
            assoc.slurm_account = account
            assoc.save()
        return assoc

    def test_same_cluster_same_account_raises(self):
        """Same cluster (direct or partition) with the same account raises."""
        self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        assoc2 = self._make_association(self.cluster_a, self.cluster_ct)
        assoc2.slurm_account = self.account_x
        with self.assertRaises(ValidationError):
            assoc2.full_clean()

        # same partition, same account -> also raises
        self._make_association(self.partition_gpu, self.partition_ct, self.account_x)
        assoc3 = self._make_association(self.partition_gpu, self.partition_ct)
        assoc3.slurm_account = self.account_x
        with self.assertRaises(ValidationError):
            assoc3.full_clean()

    def test_same_cluster_different_account_ok(self):
        """Same cluster with a different account is allowed."""
        self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        assoc2 = self._make_association(self.cluster_a, self.cluster_ct)
        assoc2.slurm_account = self.account_y
        assoc2.full_clean()  # should not raise

    def test_different_cluster_or_partition_same_account_ok(self):
        """Different cluster (or a different partition) with the same account
        is allowed."""
        self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        # different cluster
        assoc2 = self._make_association(self.cluster_b, self.cluster_ct)
        assoc2.slurm_account = self.account_x
        assoc2.full_clean()
        # same account on a direct-vs-partition mix -> allowed
        assoc3 = self._make_association(self.partition_gpu, self.partition_ct)
        assoc3.slurm_account = self.account_x
        assoc3.full_clean()

    def test_null_account_and_self_update_skip_conflict(self):
        """Null slurm_account skips validation; re-saving an association never
        flags itself."""
        assoc1 = self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        # a second association with null account -> no raise
        assoc2 = self._make_association(self.cluster_a, self.cluster_ct)
        assoc2.full_clean()

        # re-saving assoc1 (self) -> no self-conflict
        assoc1.full_clean()
        assoc1.slurm_account = self.account_y
        assoc1.full_clean()
