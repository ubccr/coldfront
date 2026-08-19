# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.registry import register_billing_source
from coldfront.slurm.models import SlurmAccount, SlurmCluster, SlurmQOS


def _slurm_account_billable(user=None, project=None):
    qs = SlurmAccount.objects.filter(associations__allocation__status=AllocationStatusChoices.STATUS_ACTIVE)
    if project is not None:
        qs = qs.filter(associations__allocation__project=project)
    elif user is not None:
        qs = qs.filter(associations__allocation__project__owner=user)
    return qs.distinct()


def _slurm_account_rate_scope(source):
    return source.cluster


def _slurm_account_quantity(source):
    return source.service_units


def _slurm_qos_billable(user=None, project=None):
    qs = SlurmQOS.objects.filter(
        added_to_account__associations__allocation__status=AllocationStatusChoices.STATUS_ACTIVE
    )
    if project is not None:
        qs = qs.filter(added_to_account__associations__allocation__project=project)
    elif user is not None:
        qs = qs.filter(added_to_account__associations__allocation__project__owner=user)
    return qs.distinct()


def _slurm_qos_rate_scope(source):
    return source


def _slurm_qos_quantity(source):
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
