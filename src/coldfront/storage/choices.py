# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.utils.translation import gettext_lazy as _

from coldfront.choices import ChoiceSet


class StorageShareTypeChoices(ChoiceSet):
    key = "StorageQuota.share_type"

    SHARE_TYPE_POSIX = "posix"
    SHARE_TYPE_SMB = "smb"
    SHARE_TYPE_NFS = "nfs"

    CHOICES = [
        (SHARE_TYPE_POSIX, _("POSIX"), "info"),
        (SHARE_TYPE_SMB, _("SMB"), "primary"),
        (SHARE_TYPE_NFS, _("NFS"), "success"),
    ]


class StorageSnapshotIntervalChoices(ChoiceSet):
    key = "StorageSnapshotPolicy.interval"

    INTERVAL_HOURLY = "hourly"
    INTERVAL_DAILY = "daily"
    INTERVAL_WEEKLY = "weekly"
    INTERVAL_MONTHLY = "monthly"

    CHOICES = [
        (INTERVAL_HOURLY, _("Hourly"), "info"),
        (INTERVAL_DAILY, _("Daily"), "success"),
        (INTERVAL_WEEKLY, _("Weekly"), "warning"),
        (INTERVAL_MONTHLY, _("Monthly"), "primary"),
    ]
