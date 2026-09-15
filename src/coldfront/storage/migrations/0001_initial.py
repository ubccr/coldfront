# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django.db.models.deletion
import taggit.managers
from django.conf import settings
from django.db import migrations, models

import coldfront.core.utils
import coldfront.models.deletion
import coldfront.utils.jsonschema


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0003_job_cron_schedule"),
        ("ras", "0003_projectinvite"),
        ("tenancy", "0001_initial"),
        ("users", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StorageCluster",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="name")),
                ("description", models.TextField(blank=True, verbose_name="description")),
                (
                    "backend_path",
                    models.CharField(
                        blank=True,
                        default=None,
                        help_text="Dotted Python path to a StorageBackend subclass, e.g. 'coldfront.storage.backends.vast.VastBackend'. Leave empty for clusters with no backend (sync jobs will skip them).",
                        max_length=500,
                        null=True,
                        verbose_name="backend path",
                    ),
                ),
                (
                    "capacity_bytes",
                    models.PositiveBigIntegerField(
                        blank=True,
                        default=None,
                        help_text="Total storage capacity of this cluster in bytes. Leave empty for unlimited.",
                        null=True,
                        verbose_name="capacity",
                    ),
                ),
                (
                    "allocated_bytes",
                    models.PositiveBigIntegerField(
                        default=0,
                        editable=False,
                        help_text="Sum of hard_limit_bytes for all active quotas on this cluster. Updated automatically.",
                        verbose_name="allocated",
                    ),
                ),
                (
                    "used_bytes",
                    models.PositiveBigIntegerField(
                        default=0,
                        editable=False,
                        help_text="Sum of actual usage from all active quotas on this cluster. Updated by sync.",
                        verbose_name="used",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
            ],
            options={
                "verbose_name": "storage cluster",
                "verbose_name_plural": "storage clusters",
                "ordering": ["name"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="StorageResource",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "schema",
                    models.JSONField(
                        blank=True,
                        null=True,
                        validators=[coldfront.utils.jsonschema.validate_schema],
                        verbose_name="schema",
                    ),
                ),
                (
                    "locked",
                    models.BooleanField(
                        default=False,
                        help_text="Prevent users from submitting allocations for this resource.",
                        verbose_name="locked",
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "path_template",
                    models.CharField(
                        default="/mnt/{{project.slug}}/{{allocation.slug}}",
                        help_text="Template for auto-generating storage paths. Supports {project.<attr>}, {resource.<attr>}, and {allocation.id}.",
                        max_length=500,
                        verbose_name="path template",
                    ),
                ),
                (
                    "capacity_bytes",
                    models.PositiveBigIntegerField(
                        blank=True,
                        default=None,
                        help_text="Maximum total allocation across all quotas on this resource. Leave empty for unlimited.",
                        null=True,
                        verbose_name="capacity",
                    ),
                ),
                (
                    "allocated_bytes",
                    models.PositiveBigIntegerField(
                        default=0,
                        editable=False,
                        help_text="Sum of hard_limit_bytes for all active quotas. Updated automatically.",
                        verbose_name="allocated",
                    ),
                ),
                (
                    "used_bytes",
                    models.PositiveBigIntegerField(
                        default=0,
                        editable=False,
                        help_text="Sum of actual usage from all active quotas. Updated by sync.",
                        verbose_name="used",
                    ),
                ),
                (
                    "clusters",
                    models.ManyToManyField(
                        related_name="storage_resources", to="storage.storagecluster", verbose_name="clusters"
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="storage_resources",
                        to="tenancy.tenant",
                        verbose_name="tenant",
                    ),
                ),
            ],
            options={
                "verbose_name": "storage resource",
                "verbose_name_plural": "storage resources",
                "ordering": ["name"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="StorageSnapshotPolicy",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "interval",
                    models.CharField(
                        choices=[
                            ("hourly", "Hourly"),
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                        ],
                        max_length=50,
                        verbose_name="interval",
                    ),
                ),
                (
                    "retention_days",
                    models.PositiveIntegerField(
                        help_text="Number of days to retain snapshots.", verbose_name="retention days"
                    ),
                ),
                ("extra_config", models.JSONField(blank=True, default=dict, verbose_name="extra configuration")),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="snapshot_policies",
                        to="storage.storagecluster",
                        verbose_name="cluster",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
            ],
            options={
                "verbose_name": "storage snapshot policy",
                "verbose_name_plural": "storage snapshot policies",
                "ordering": ["cluster__name", "name"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="StorageQuota",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("path", models.CharField(max_length=500, verbose_name="path")),
                ("path_mode", models.PositiveSmallIntegerField(default=2770, verbose_name="path mode")),
                (
                    "hard_limit_bytes",
                    models.PositiveBigIntegerField(
                        blank=True, help_text="Quota limit in bytes.", null=True, verbose_name="hard limit"
                    ),
                ),
                (
                    "soft_limit_bytes",
                    models.PositiveBigIntegerField(
                        blank=True, help_text="Soft quota limit in bytes.", null=True, verbose_name="soft limit"
                    ),
                ),
                (
                    "hard_limit_files",
                    models.PositiveBigIntegerField(
                        blank=True,
                        help_text="Hard limit on number of files.",
                        null=True,
                        verbose_name="hard limit files",
                    ),
                ),
                (
                    "soft_limit_files",
                    models.PositiveBigIntegerField(
                        blank=True,
                        help_text="Soft limit on number of files.",
                        null=True,
                        verbose_name="soft limit files",
                    ),
                ),
                ("grace_period", models.DurationField(blank=True, null=True, verbose_name="grace period")),
                (
                    "share_type",
                    models.CharField(
                        choices=[("posix", "POSIX"), ("smb", "SMB"), ("nfs", "NFS")],
                        default="posix",
                        max_length=20,
                        verbose_name="share type",
                    ),
                ),
                (
                    "used_bytes",
                    models.PositiveBigIntegerField(
                        blank=True,
                        help_text="Current usage in bytes. Populated by sync.",
                        null=True,
                        verbose_name="used",
                    ),
                ),
                (
                    "used_files",
                    models.PositiveBigIntegerField(
                        blank=True,
                        help_text="Current number of files. Populated by sync.",
                        null=True,
                        verbose_name="used files",
                    ),
                ),
                ("state", models.CharField(blank=True, max_length=50, verbose_name="state")),
                (
                    "allocation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_extensions",
                        to="ras.allocation",
                        unique=True,
                    ),
                ),
                (
                    "clusters",
                    models.ManyToManyField(
                        blank=True, related_name="quotas", to="storage.storagecluster", verbose_name="clusters"
                    ),
                ),
                (
                    "owning_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="storage_quotas",
                        to="users.group",
                        verbose_name="owning group",
                    ),
                ),
                (
                    "owning_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="storage_quotas_as_owner",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owning user",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        help_text="A comma-separated list of tags.",
                        through="core.TaggedItem",
                        to="core.Tag",
                        verbose_name="Tags",
                    ),
                ),
                (
                    "storage",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quotas",
                        to="storage.storageresource",
                        verbose_name="storage resource",
                    ),
                ),
                (
                    "snapshot_policy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="quotas",
                        to="storage.storagesnapshotpolicy",
                        verbose_name="snapshot policy",
                    ),
                ),
            ],
            options={
                "verbose_name": "storage quota",
                "verbose_name_plural": "storage quotas",
                "ordering": ["allocation__slug"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.AddConstraint(
            model_name="storagecluster",
            constraint=models.CheckConstraint(
                condition=models.Q(("capacity_bytes", None), ("capacity_bytes__gt", 0), _connector="OR"),
                name="storage_storagecluster_capacity_must_be_null_or_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="storageresource",
            constraint=models.CheckConstraint(
                condition=models.Q(("capacity_bytes", None), ("capacity_bytes__gt", 0), _connector="OR"),
                name="storage_storageresource_capacity_must_be_null_or_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="storagesnapshotpolicy",
            constraint=models.UniqueConstraint(
                fields=("cluster", "name"), name="storage_storagesnapshotpolicy_unique_cluster_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="storagequota",
            constraint=models.UniqueConstraint(
                fields=("path", "storage"), name="storage_storagequota_unique_path_per_storage"
            ),
        ),
    ]
