# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import migrations, models

import coldfront.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ThirdPartyAccount",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                ("provider", models.CharField(max_length=50, verbose_name="provider")),
                (
                    "account_id",
                    models.CharField(
                        help_text="The identifier of the account at the provider (e.g. an ORCID iD).",
                        max_length=255,
                        verbose_name="account ID",
                    ),
                ),
                (
                    "is_verified",
                    models.BooleanField(
                        default=False,
                        help_text="Whether the account ownership was verified via OAuth.",
                        verbose_name="verified",
                    ),
                ),
                (
                    "scopes",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Scopes granted during the OAuth flow.",
                        verbose_name="scopes",
                    ),
                ),
                ("linked_at", models.DateTimeField(auto_now_add=True, null=True, verbose_name="linked at")),
                (
                    "last_synced_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the provider's data was last synchronized (unused in the link-only phase).",
                        null=True,
                        verbose_name="last synced",
                    ),
                ),
            ],
            options={
                "verbose_name": "third-party account",
                "verbose_name_plural": "third-party accounts",
                "ordering": ("provider",),
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
    ]
