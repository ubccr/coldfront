# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.registry import register_billing_source
from coldfront.storage.models import StorageQuota, StorageResource


def _storage_quota_billable(user=None, project=None):
    qs = StorageQuota.objects.filter(allocation__status=AllocationStatusChoices.STATUS_ACTIVE)
    if project is not None:
        qs = qs.filter(allocation__project=project)
    elif user is not None:
        qs = qs.filter(allocation__project__owner=user)
    return qs


def _storage_quota_rate_scope(source):
    return source.storage


def _storage_quota_quantity(source):
    return source.hard_limit_bytes


register_billing_source(
    StorageResource,
    StorageQuota,
    get_billable=_storage_quota_billable,
    get_rate_scope=_storage_quota_rate_scope,
    get_quantity=_storage_quota_quantity,
)
