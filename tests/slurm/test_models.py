# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for SU billing TRES model helpers."""

from django.test import TestCase

from coldfront.slurm.choices import (
    SlurmBillingModeChoices,
    SlurmSuEnforcementModeChoices,
)
from coldfront.slurm.models import SlurmCluster, SlurmPartition


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
    """SlurmPartition.effective_tres_billing_weights fallback chain."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc")
        cls.partition = SlurmPartition.objects.create(cluster=cls.cluster, name="normal")

    def test_partition_weights_win(self):
        self.partition.tres_billing_weights = {"node": 10}
        self.partition.save()
        self.assertEqual(self.partition.effective_tres_billing_weights(), {"node": 10})

    def test_falls_back_to_cluster_default(self):
        self.cluster.default_tres_billing_weights = {"CPU": 1.0, "gres/gpu": 2.0}
        self.cluster.save()
        self.assertEqual(self.partition.effective_tres_billing_weights(), {"CPU": 1.0, "gres/gpu": 2.0})

    def test_falls_back_to_cpu_one(self):
        self.assertEqual(self.partition.effective_tres_billing_weights(), {"CPU": 1.0})
