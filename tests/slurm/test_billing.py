# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for usage-based Slurm billing helpers.

- ``TestSlurmAccountQuantity`` — ``_slurm_account_quantity`` period summing
- ``TestRemainingSus`` — ``SlurmAccount.remaining_sus()`` grant minus consumed
"""

from __future__ import annotations

from datetime import date

from django.test import TestCase
from django.utils import timezone

from coldfront.billing.models import Invoice
from coldfront.slurm.billing import _slurm_account_quantity
from coldfront.slurm.models import SlurmAccount, SlurmAccountUsage, SlurmCluster


def _invoice(owner, *, start=None, end=None):
    return Invoice.objects.create(owner=owner, status="draft", start_date=start, end_date=end)


class TestSlurmAccountQuantity(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = cls._make_user()
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.account = SlurmAccount.objects.create(name="acct-a", cluster=cls.cluster, service_units=10000)

    @staticmethod
    def _make_user():
        from coldfront.users.models import User

        return User.objects.create_user(username="pi")

    @staticmethod
    def _add_usage(account, cluster, day, consumed):
        SlurmAccountUsage.objects.create(
            cluster=cluster,
            account=account,
            period_start=day,
            period_end=day,
            billing_units_consumed=consumed,
            billing_units_completed=consumed,
        )

    def test_sums_consumed_within_invoice_period(self):
        self._add_usage(self.account, self.cluster, date(2024, 1, 10), 10.0)
        self._add_usage(self.account, self.cluster, date(2024, 1, 20), 5.0)
        self._add_usage(self.account, self.cluster, date(2024, 2, 10), 3.0)

        invoice = _invoice(
            self.owner,
            start=timezone.now().replace(year=2024, month=1, day=1),
            end=timezone.now().replace(year=2024, month=1, day=31),
        )
        assert _slurm_account_quantity(self.account, invoice) == 15.0

    def test_open_invoice_sums_all_usage(self):
        self._add_usage(self.account, self.cluster, date(2024, 1, 10), 10.0)
        self._add_usage(self.account, self.cluster, date(2024, 2, 10), 5.0)
        assert _slurm_account_quantity(self.account, _invoice(self.owner)) == 15.0

    def test_no_usage_returns_zero(self):
        invoice = _invoice(
            self.owner,
            start=timezone.now().replace(year=2024, month=1, day=1),
            end=timezone.now().replace(year=2024, month=1, day=31),
        )
        assert _slurm_account_quantity(self.account, invoice) == 0.0

    def test_scopes_to_account_and_cluster(self):
        other = SlurmAccount.objects.create(name="acct-b", cluster=self.cluster)
        self._add_usage(self.account, self.cluster, date(2024, 1, 10), 10.0)
        # other account has no usage -> 0, not the shared cluster's usage
        invoice = _invoice(self.owner)
        assert _slurm_account_quantity(other, invoice) == 0.0


class TestRemainingSus(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.account = SlurmAccount.objects.create(name="acct-a", cluster=cls.cluster, service_units=10000)

    def test_grant_minus_consumed(self):
        SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 10),
            period_end=date(2024, 1, 10),
            billing_units_consumed=4000.0,
            billing_units_completed=4000.0,
        )
        assert self.account.remaining_sus() == 6000.0

    def test_none_when_no_grant(self):
        account = SlurmAccount.objects.create(name="acct-b", cluster=self.cluster)
        assert account.remaining_sus() is None
