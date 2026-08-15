# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import (
    AllocatableResourceBulkEditForm,
    PrimaryModelBulkEditForm,
)
from coldfront.forms.fields import JSONField
from coldfront.forms.fields.bytes import BytesField
from coldfront.forms.widgets import BulkEditNullBooleanSelect
from coldfront.storage.choices import StorageShareTypeChoices
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource, StorageSnapshotPolicy
from coldfront.users.models import Group, User
from coldfront.utils.forms import add_blank_choice

#
# Storage Resources
#


class StorageResourceBulkEditForm(AllocatableResourceBulkEditForm, PrimaryModelBulkEditForm):
    clusters = forms.ModelMultipleChoiceField(
        queryset=StorageCluster.objects.all(),
        required=False,
        label=_("Clusters"),
    )
    path_template = forms.CharField(
        max_length=500,
        required=False,
        label=_("Path Template"),
    )
    capacity_bytes = BytesField(
        label=_("Capacity"),
        required=False,
        help_text=_(
            "Maximum total allocation across all quotas on this resource. "
            "Leave empty for unlimited.  Accepts human-readable sizes (e.g. 10 TB)."
        ),
    )

    model = StorageResource
    nullable_fields = (
        "tenant_group",
        "tenant",
        "description",
        "locked",
        "schema",
        "clusters",
        "path_template",
        "capacity_bytes",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Storage Resource"),
                "description",
                "locked",
                "schema",
            ),
            Fieldset(
                _("Backend"),
                "clusters",
                "path_template",
            ),
            Fieldset(
                _("Capacity"),
                "capacity_bytes",
            ),
        ]


#
# Storage Clusters
#


class StorageClusterBulkEditForm(PrimaryModelBulkEditForm):
    backend_path = forms.ChoiceField(
        choices=[],
        required=False,
        label=_("Backend"),
        help_text=_("Select the storage backend driver."),
    )
    auto_sync_enabled = forms.NullBooleanField(
        label=_("Auto Sync Enabled"),
        widget=BulkEditNullBooleanSelect,
        required=False,
    )
    sync_interval = forms.IntegerField(
        required=False,
        label=_("Sync Interval"),
        help_text=_("Minutes between automatic syncs."),
    )
    capacity_bytes = BytesField(
        label=_("Capacity"),
        required=False,
        help_text=_("Total storage capacity of this cluster in bytes. Accepts human-readable sizes (e.g. 10 TB)."),
    )

    model = StorageCluster
    nullable_fields = (
        "description",
        "backend_path",
        "auto_sync_enabled",
        "sync_interval",
        "capacity_bytes",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Storage Cluster"),
                "description",
                "backend_path",
            ),
            Fieldset(
                _("Sync"),
                "auto_sync_enabled",
                "sync_interval",
            ),
            Fieldset(
                _("Capacity"),
                "capacity_bytes",
            ),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from coldfront.storage.backends.registry import get_backend_choices

        choices = get_backend_choices()
        self.fields["backend_path"] = forms.ChoiceField(
            choices=choices,
            required=False,
            label=_("Backend"),
            help_text=_("Select the storage backend driver."),
        )


#
# Storage Quotas
#


class StorageQuotaBulkEditForm(PrimaryModelBulkEditForm):
    clusters = forms.ModelMultipleChoiceField(
        queryset=StorageCluster.objects.all(),
        required=False,
        label=_("Clusters"),
    )
    owning_user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("Owning User"),
    )
    owning_group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label=_("Owning Group"),
    )
    path_mode = forms.IntegerField(
        required=False,
        label=_("Path Mode"),
    )
    hard_limit_bytes = BytesField(
        label=_("Hard Limit"),
        required=False,
        help_text=_("Approved quota limit in bytes. Accepts human-readable sizes (e.g. 10 TB)."),
    )
    soft_limit_bytes = BytesField(
        label=_("Soft Limit"),
        required=False,
        help_text=_("Soft quota limit in bytes. Accepts human-readable sizes (e.g. 10 TB)."),
    )
    hard_limit_files = forms.IntegerField(
        required=False,
        label=_("Hard Limit Files"),
        help_text=_("Hard limit on number of files."),
    )
    soft_limit_files = forms.IntegerField(
        required=False,
        label=_("Soft Limit Files"),
        help_text=_("Soft limit on number of files."),
    )
    grace_period = forms.IntegerField(
        required=False,
        label=_("Grace Period (minutes)"),
        help_text=_("Duration in minutes"),
    )
    share_type = forms.ChoiceField(
        choices=add_blank_choice(StorageShareTypeChoices),
        required=False,
        label=_("Share Type"),
    )
    snapshot_policy = forms.ModelChoiceField(
        queryset=StorageSnapshotPolicy.objects.all(),
        required=False,
        label=_("Snapshot Policy"),
    )

    model = StorageQuota
    nullable_fields = (
        "description",
        "clusters",
        "owning_user",
        "owning_group",
        "path_mode",
        "hard_limit_bytes",
        "soft_limit_bytes",
        "hard_limit_files",
        "soft_limit_files",
        "grace_period",
        "share_type",
        "snapshot_policy",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Storage Quota"),
                "clusters",
                "owning_user",
                "owning_group",
                "path_mode",
            ),
            Fieldset(
                _("Limits"),
                "hard_limit_bytes",
                "soft_limit_bytes",
                "hard_limit_files",
                "soft_limit_files",
                "grace_period",
                "share_type",
            ),
            Fieldset(
                _("Snapshot Policy"),
                "snapshot_policy",
            ),
        ]


#
# Storage Snapshot Policies
#


class StorageSnapshotPolicyBulkEditForm(PrimaryModelBulkEditForm):
    cluster = forms.ModelChoiceField(
        queryset=StorageCluster.objects.all(),
        required=False,
        label=_("Cluster"),
    )
    interval = forms.ChoiceField(
        choices=[
            ("", _("---------")),
            ("hourly", _("Hourly")),
            ("daily", _("Daily")),
            ("weekly", _("Weekly")),
            ("monthly", _("Monthly")),
        ],
        required=False,
        label=_("Interval"),
    )
    retention_days = forms.IntegerField(
        required=False,
        label=_("Retention Days"),
        help_text=_("Number of days to retain snapshots."),
    )
    extra_config = JSONField(
        label=_("Extra Configuration"),
        required=False,
        help_text=_("Enter valid JSON."),
    )

    model = StorageSnapshotPolicy
    nullable_fields = (
        "description",
        "cluster",
        "interval",
        "retention_days",
        "extra_config",
    )

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Snapshot Policy"),
                "cluster",
                "description",
                "interval",
                "retention_days",
                "extra_config",
            ),
        ]
