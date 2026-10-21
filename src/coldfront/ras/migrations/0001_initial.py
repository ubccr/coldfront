# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import migrations, models

import coldfront.core.utils
import coldfront.lib.models.deletion
import coldfront.lib.models.fields
import coldfront.lib.utils.jsonschema


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Allocation",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                (
                    "slug",
                    coldfront.lib.models.fields.AutoSlugField(
                        blank=True,
                        help_text="Unique slug. Leave blank and one will be auto generated.",
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
                ("resource_object_id", models.PositiveBigIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("active", "Active"),
                            ("denied", "Denied"),
                            ("expired", "Expired"),
                            ("approved", "Approved"),
                            ("revoked", "Revoked"),
                            ("renew", "Renew"),
                        ],
                        default="requested",
                        max_length=50,
                        verbose_name="status",
                    ),
                ),
                ("start_date", models.DateTimeField(blank=True, null=True, verbose_name="start date")),
                ("end_date", models.DateTimeField(blank=True, null=True, verbose_name="end date")),
                ("justification", models.TextField(blank=True, null=True, verbose_name="justification")),
                ("description", models.CharField(blank=True, max_length=200, null=True, verbose_name="description")),
                ("attribute_data", models.JSONField(blank=True, null=True, verbose_name="attributes")),
            ],
            options={
                "verbose_name": "allocation",
                "verbose_name_plural": "allocations",
                "ordering": ["start_date"],
                "permissions": (
                    ("request", "Request allocation"),
                    ("approve", "Approve allocation"),
                    ("deny", "Deny allocation"),
                    ("activate", "Activate allocation"),
                    ("expire", "Expire allocation"),
                    ("revoke", "Revoke allocation"),
                    ("renew", "Renew allocation"),
                ),
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="AllocationChangeRequest",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                (
                    "slug",
                    coldfront.lib.models.fields.AutoSlugField(
                        blank=True,
                        help_text="Unique slug. Leave blank and one will be auto generated.",
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("approved", "Approved"),
                            ("denied", "Denied"),
                            ("applied", "Applied"),
                        ],
                        default="requested",
                        max_length=50,
                        verbose_name="status",
                    ),
                ),
                ("justification", models.TextField(blank=True, verbose_name="justification")),
                (
                    "extension_days",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Number of days to extend the allocation end_date. On apply, the end_date is increased by this many days.",
                        null=True,
                        verbose_name="extension (days)",
                    ),
                ),
                (
                    "attribute_changes",
                    models.JSONField(
                        blank=True,
                        help_text="JSON object containing only the keys that should change. On apply, these are merged into the allocation's attribute_data and validated against the resource schema.",
                        null=True,
                        verbose_name="attribute changes",
                    ),
                ),
                (
                    "extension_changes",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="JSON object mapping extension model paths to dicts of proposed field values. On apply, each extension's apply_json_change() is called with its proposed values.",
                        verbose_name="extension changes",
                    ),
                ),
                (
                    "snapshot_extension_values",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Snapshot of extension field values at the time the change request was applied. Populated during the apply transition. Empty for unapplied requests.",
                        verbose_name="snapshot extension values",
                    ),
                ),
                (
                    "snapshot_attribute_values",
                    models.JSONField(
                        blank=True,
                        help_text="Snapshot of allocation attribute_data at the time the change request was applied. Populated during the apply transition. Null for unapplied requests.",
                        null=True,
                        verbose_name="snapshot attribute values",
                    ),
                ),
            ],
            options={
                "verbose_name": "allocation change request",
                "verbose_name_plural": "allocation change requests",
                "ordering": ["created"],
                "permissions": (
                    ("request", "Request change"),
                    ("approve", "Approve change"),
                    ("deny", "Deny change"),
                    ("apply", "Apply change"),
                ),
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="name")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "slug",
                    coldfront.lib.models.fields.AutoSlugField(
                        blank=True,
                        help_text="Unique slug. Leave blank and one will be auto generated.",
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
            ],
            options={
                "verbose_name": "project",
                "verbose_name_plural": "projects",
                "ordering": ["name"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="ProjectInvite",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                ("email", models.EmailField(max_length=254, verbose_name="email address")),
                (
                    "code_hash",
                    models.CharField(
                        blank=True,
                        help_text="SHA-256 digest of the one-time invite token. Auto-generated on creation.",
                        max_length=64,
                        unique=True,
                        verbose_name="invite code",
                    ),
                ),
                ("accepted_at", models.DateTimeField(blank=True, null=True, verbose_name="accepted")),
            ],
            options={
                "verbose_name": "project invite",
                "verbose_name_plural": "project invites",
                "ordering": ["created"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="ProjectUser",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
            ],
            options={
                "verbose_name": "project user",
                "verbose_name_plural": "project users",
                "ordering": ["id"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Resource",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                (
                    "schema",
                    models.JSONField(
                        blank=True,
                        null=True,
                        validators=[coldfront.lib.utils.jsonschema.validate_schema],
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
                ("slug", models.SlugField(max_length=100, verbose_name="slug")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="name")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("offline", "Offline"),
                            ("active", "Active"),
                            ("planned", "Planned"),
                            ("staged", "Staged"),
                            ("decommissioning", "Decommissioning"),
                        ],
                        default="active",
                        max_length=50,
                        verbose_name="status",
                    ),
                ),
                ("lft", models.PositiveIntegerField(editable=False)),
                ("rght", models.PositiveIntegerField(editable=False)),
                ("tree_id", models.PositiveIntegerField(db_index=True, editable=False)),
                ("level", models.PositiveIntegerField(editable=False)),
            ],
            options={
                "verbose_name": "generic resource",
                "verbose_name_plural": "generic resources",
                "ordering": ["name"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="ResourceType",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="name")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("slug", models.SlugField(max_length=100, unique=True, verbose_name="slug")),
                (
                    "color",
                    coldfront.lib.models.fields.ColorField(default="neutral", max_length=20, verbose_name="color"),
                ),
            ],
            options={
                "verbose_name": "resource type",
                "verbose_name_plural": "resource types",
                "ordering": ["name"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
        ),
    ]
