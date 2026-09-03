# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db.models import Sum

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.registry import register_billing_source
from coldfront.slurm.models import SlurmAccount, SlurmAccountUsage, SlurmCluster, SlurmQOS


def _slurm_account_billable(user):
    qs = SlurmAccount.objects.filter(associations__allocation__status=AllocationStatusChoices.STATUS_ACTIVE)
    if user is not None:
        qs = qs.filter(associations__allocation__project__owner=user)
    return qs.distinct()


def _slurm_account_rate_scope(source):
    return source.cluster


def _slurm_account_quantity(source, invoice):
    """Usage-based: bill the SU consumed by ``source`` within ``invoice``'s period.

    Sums ``SlurmAccountUsage.billing_units_consumed`` for the account over the
    daily rows overlapping the invoice period. An open invoice (no start/end)
    sums all rows for the account. Returns 0 when there is no synced usage,
    which skips the charge entirely.
    """
    qs = SlurmAccountUsage.objects.filter(account=source, cluster=source.cluster)
    # Daily rows (period_start == period_end == day) overlap the invoice period
    # when the day falls within [invoice.start_date, invoice.end_date].
    if invoice.start_date is not None:
        qs = qs.filter(period_start__gte=invoice.start_date.date())
    if invoice.end_date is not None:
        qs = qs.filter(period_start__lte=invoice.end_date.date())
    return qs.aggregate(total=Sum("billing_units_consumed"))["total"] or 0.0


def _slurm_qos_billable(user):
    qs = SlurmQOS.objects.filter(
        added_to_account__associations__allocation__status=AllocationStatusChoices.STATUS_ACTIVE
    )
    if user is not None:
        qs = qs.filter(added_to_account__associations__allocation__project__owner=user)
    return qs.distinct()


def _slurm_qos_rate_scope(source):
    return source


def _slurm_qos_quantity(source, invoice):
    return 1


register_billing_source(
    SlurmCluster,
    SlurmAccount,
    get_billable=_slurm_account_billable,
    get_rate_scope=_slurm_account_rate_scope,
    get_quantity=_slurm_account_quantity,
)
register_billing_source(
    SlurmQOS,
    SlurmQOS,
    get_billable=_slurm_qos_billable,
    get_rate_scope=_slurm_qos_rate_scope,
    get_quantity=_slurm_qos_quantity,
)
