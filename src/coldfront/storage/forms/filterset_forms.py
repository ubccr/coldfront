# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.constants import BOOLEAN_WITH_BLANK_CHOICES
from coldfront.forms import PrimaryModelFilterSetForm
from coldfront.forms.fields import (
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from coldfront.ras.models import Allocation
from coldfront.storage.choices import StorageShareTypeChoices, StorageSnapshotIntervalChoices
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource, StorageSnapshotPolicy
from coldfront.users.models import Group, User


class StorageResourceFilterSetForm(PrimaryModelFilterSetForm):
    model = StorageResource
    clusters = DynamicModelMultipleChoiceField(
        queryset=StorageCluster.objects.all(),
        required=False,
        label=_("Clusters"),
    )
    locked = forms.NullBooleanField(
        label=_("Locked"),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Storage Resource"),
            "clusters",
            "locked",
            "tag",
        ),
    )


class StorageClusterFilterSetForm(PrimaryModelFilterSetForm):
    model = StorageCluster
    backend_path = forms.CharField(
        required=False,
        label=_("Backend Path"),
    )
    auto_sync_enabled = forms.NullBooleanField(
        label=_("Auto Sync Enabled"),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Storage Cluster"),
            "backend_path",
            "auto_sync_enabled",
            "tag",
        ),
    )


class StorageQuotaFilterSetForm(PrimaryModelFilterSetForm):
    model = StorageQuota
    storage_id = forms.ModelChoiceField(
        queryset=StorageResource.objects.all(),
        required=False,
        label=_("Storage Resource"),
    )
    allocation_id = forms.ModelChoiceField(
        queryset=Allocation.objects.all(),
        required=False,
        label=_("Allocation"),
    )
    share_type = forms.MultipleChoiceField(
        label=_("Share Type"),
        choices=StorageShareTypeChoices,
        required=False,
    )
    snapshot_policy_id = forms.ModelChoiceField(
        queryset=StorageSnapshotPolicy.objects.all(),
        required=False,
        label=_("Snapshot Policy"),
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
    state = forms.CharField(
        required=False,
        label=_("State"),
    )
    path = forms.CharField(
        required=False,
        label=_("Path"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Storage Quota"),
            "storage_id",
            "allocation_id",
            "share_type",
            "snapshot_policy_id",
            "owning_user",
            "owning_group",
            "state",
            "path",
            "tag",
        ),
    )


class StorageSnapshotPolicyFilterSetForm(PrimaryModelFilterSetForm):
    model = StorageSnapshotPolicy
    cluster_id = forms.ModelChoiceField(
        queryset=StorageCluster.objects.all(),
        required=False,
        label=_("Cluster"),
    )
    interval = forms.MultipleChoiceField(
        label=_("Interval"),
        choices=StorageSnapshotIntervalChoices,
        required=False,
    )
    retention_days = forms.IntegerField(
        required=False,
        label=_("Retention Days"),
    )
    tag = TagFilterField(model)

    fieldsets = (
        Fieldset(
            _("Snapshot Policy"),
            "cluster_id",
            "interval",
            "retention_days",
            "tag",
        ),
    )
