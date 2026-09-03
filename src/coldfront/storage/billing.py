# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.registry import register_billing_source
from coldfront.storage.models import StorageQuota, StorageResource


def _storage_quota_billable(user):
    qs = StorageQuota.objects.filter(allocation__status=AllocationStatusChoices.STATUS_ACTIVE)
    if user is not None:
        qs = qs.filter(allocation__project__owner=user)
    return qs


def _storage_quota_rate_scope(source):
    return source.storage


def _storage_quota_quantity(source, invoice):
    # Grant-based (additive): bill the hard limit regardless of the invoice
    # period. The invoice arg is accepted for the shared get_quantity contract.
    return source.hard_limit_bytes


register_billing_source(
    StorageResource,
    StorageQuota,
    get_billable=_storage_quota_billable,
    get_rate_scope=_storage_quota_rate_scope,
    get_quantity=_storage_quota_quantity,
)
