# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from coldfront.forms import PrimaryModelForm, PrimaryModelImportForm, TenancyForm, TenancyImportForm
from coldfront.forms.fields import CSVModelChoiceField, CSVModelMultipleChoiceField, DynamicModelChoiceField, JSONField
from coldfront.forms.fields.bytes import BytesField
from coldfront.forms.layout import FieldSet
from coldfront.ras.models import Allocation
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource, StorageSnapshotPolicy
from coldfront.users.models import Group, User


class StorageResourceForm(TenancyForm, PrimaryModelForm):
    capacity_bytes = BytesField(
        label=_("Capacity"),
        required=False,
        help_text=_(
            "Maximum total allocation across all quotas on this resource. "
            "Leave empty for unlimited.  Accepts human-readable sizes (e.g. 10 TB)."
        ),
    )
    schema = JSONField(
        label=_("Schema"),
        required=False,
        help_text=_("Enter a valid JSON schema to define supported allocation attributes."),
    )

    class Meta:
        model = StorageResource
        fields = [
            "name",
            "tenant_group",
            "tenant",
            "description",
            "locked",
            "schema",
            "clusters",
            "path_template",
            "capacity_bytes",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "name",
                "description",
                "locked",
                "schema",
                name=_("Storage Resource"),
            ),
            FieldSet(
                "clusters",
                "path_template",
                name=_("Backend"),
            ),
            FieldSet(
                "capacity_bytes",
                name=_("Capacity"),
            ),
        ]

    def clean(self):
        super().clean()

        capacity = self.cleaned_data.get("capacity_bytes")
        clusters = self.cleaned_data.get("clusters")

        if capacity and clusters:
            total = clusters.aggregate(total=Sum("capacity_bytes"))["total"]
            if total and capacity > total:
                raise ValidationError(
                    _(f"Resource capacity ({capacity}) cannot exceed the total capacity of its clusters ({total}).")
                )


class StorageResourceImportForm(TenancyImportForm, PrimaryModelImportForm):
    clusters = CSVModelMultipleChoiceField(
        queryset=StorageCluster.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Clusters"),
    )
    capacity_bytes = BytesField(
        label=_("Capacity"),
        required=False,
        help_text=_(
            "Maximum total allocation across all quotas on this resource. "
            "Leave empty for unlimited.  Accepts human-readable sizes (e.g. 10 TB)."
        ),
    )

    class Meta:
        model = StorageResource
        fields = [
            "name",
            "tenant",
            "description",
            "locked",
            "schema",
            "path_template",
            "capacity_bytes",
            "tags",
        ]


class StorageClusterForm(PrimaryModelForm):
    capacity_bytes = BytesField(
        label=_("Capacity"),
        required=False,
        help_text=_(
            "Total storage capacity of this cluster in bytes. "
            "Leave empty for unlimited.  Accepts human-readable sizes (e.g. 10 TB)."
        ),
    )

    class Meta:
        model = StorageCluster
        fields = [
            "name",
            "description",
            "backend_path",
            "capacity_bytes",
            "tags",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from coldfront.storage.backends.registry import get_backend_choices

        choices = get_backend_choices()
        self.fields["backend_path"] = forms.ChoiceField(
            choices=choices,
            required=False,
            label=_("Backend"),
            help_text=_("Select the storage backend driver. Leave empty for clusters with no backend."),
        )

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "name",
                "description",
                "backend_path",
                name=_("Storage Cluster"),
            ),
            FieldSet(
                "capacity_bytes",
                name=_("Capacity"),
            ),
        ]


class StorageClusterImportForm(PrimaryModelImportForm):
    capacity_bytes = BytesField(
        label=_("Capacity"),
        required=False,
        help_text=_(
            "Total storage capacity of this cluster in bytes. "
            "Leave empty for unlimited.  Accepts human-readable sizes (e.g. 10 TB)."
        ),
    )

    class Meta:
        model = StorageCluster
        fields = [
            "name",
            "description",
            "backend_path",
            "capacity_bytes",
            "tags",
        ]


class StorageQuotaForm(PrimaryModelForm):
    allocation = DynamicModelChoiceField(
        label=_("Allocation"),
        queryset=Allocation.objects.all(),
        required=True,
        selector=True,
    )

    storage = forms.ModelChoiceField(
        queryset=StorageResource.objects.all(),
        label=_("Storage Resource"),
    )

    snapshot_policy = forms.ModelChoiceField(
        queryset=StorageSnapshotPolicy.objects.all(),
        required=False,
        label=_("Snapshot Policy"),
    )

    owning_user = DynamicModelChoiceField(
        label=_("Owning User"),
        queryset=User.objects.all(),
        required=True,
        selector=True,
        context={
            "label": "username",
            "title": "Username,First Name,Last Name,Email",
            "extra-columns": "first_name,last_name,email",
        },
    )

    owning_group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label=_("Owning Group"),
    )

    hard_limit_bytes = BytesField(
        label=_("Hard Limit"),
        required=False,
        help_text=_("Quota limit in bytes. Accepts human-readable sizes (e.g. 10 TB)."),
    )
    soft_limit_bytes = BytesField(
        label=_("Soft Limit"),
        required=False,
        help_text=_("Soft quota limit in bytes. Accepts human-readable sizes (e.g. 10 TB)."),
    )

    class Meta:
        model = StorageQuota
        fields = [
            "allocation",
            "storage",
            "clusters",
            "path",
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
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "allocation",
                "storage",
                "clusters",
                "path",
                "owning_user",
                "owning_group",
                "path_mode",
                name=_("Storage Quota"),
            ),
            FieldSet(
                "hard_limit_bytes",
                "soft_limit_bytes",
                "hard_limit_files",
                "soft_limit_files",
                "grace_period",
                "share_type",
                name=_("Limits"),
            ),
            FieldSet(
                "snapshot_policy",
                name=_("Snapshot Policy"),
            ),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if instance and instance.storage_id:
            self.fields["clusters"].queryset = StorageCluster.objects.filter(
                pk__in=instance.storage.clusters.values("pk")
            )
            self.fields["snapshot_policy"].queryset = StorageSnapshotPolicy.objects.filter(
                cluster__in=instance.storage.clusters.values("pk")
            )

        # Pre-fill owning_group from the allocation's project group
        if instance and instance.pk is None and instance.allocation_id:
            group = instance.allocation.project.group
            if group:
                self.fields["owning_group"].initial = group.pk
                self.fields["owning_group"].disabled = True


class StorageQuotaImportForm(PrimaryModelImportForm):
    storage = CSVModelChoiceField(
        queryset=StorageResource.objects.all(),
        to_field_name="name",
        label=_("Storage Resource"),
    )

    snapshot_policy = CSVModelChoiceField(
        queryset=StorageSnapshotPolicy.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Snapshot Policy"),
    )

    owning_user = CSVModelChoiceField(
        queryset=User.objects.all(),
        to_field_name="username",
        label=_("Owning User"),
    )

    owning_group = CSVModelChoiceField(
        queryset=Group.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Owning Group"),
    )

    hard_limit_bytes = BytesField(
        label=_("Hard Limit"),
        required=False,
        help_text=_("Quota limit in bytes. Accepts human-readable sizes (e.g. 10 TB)."),
    )
    soft_limit_bytes = BytesField(
        label=_("Soft Limit"),
        required=False,
        help_text=_("Soft quota limit in bytes. Accepts human-readable sizes (e.g. 10 TB)."),
    )

    class Meta:
        model = StorageQuota
        fields = [
            "allocation",
            "storage",
            "path",
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
            "tags",
        ]


class StorageSnapshotPolicyForm(PrimaryModelForm):
    cluster = forms.ModelChoiceField(
        queryset=StorageCluster.objects.all(),
        label=_("Cluster"),
    )

    class Meta:
        model = StorageSnapshotPolicy
        fields = [
            "cluster",
            "name",
            "description",
            "interval",
            "retention_days",
            "extra_config",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "cluster",
                "name",
                "description",
                "interval",
                "retention_days",
                "extra_config",
                name=_("Snapshot Policy"),
            ),
        ]


class StorageSnapshotPolicyImportForm(PrimaryModelImportForm):
    cluster = CSVModelChoiceField(
        queryset=StorageCluster.objects.all(),
        to_field_name="name",
        label=_("Cluster"),
    )

    class Meta:
        model = StorageSnapshotPolicy
        fields = [
            "cluster",
            "name",
            "description",
            "interval",
            "retention_days",
            "extra_config",
            "tags",
        ]
