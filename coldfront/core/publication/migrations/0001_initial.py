# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

# Generated by Django 2.2.3 on 2019-07-18 18:51

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("project", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicationSource",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("url", models.URLField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="HistoricalPublication",
            fields=[
                ("id", models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name="ID")),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                ("title", models.CharField(max_length=1024)),
                ("author", models.CharField(max_length=1024)),
                ("year", models.PositiveIntegerField()),
                ("unique_id", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("Active", "Active"), ("Archived", "Archived")], default="Active", max_length=16
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField()),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="project.Project",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="publication.PublicationSource",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical publication",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Publication",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                ("title", models.CharField(max_length=1024)),
                ("author", models.CharField(max_length=1024)),
                ("year", models.PositiveIntegerField()),
                ("unique_id", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("Active", "Active"), ("Archived", "Archived")], default="Active", max_length=16
                    ),
                ),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="project.Project")),
                (
                    "source",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publication.PublicationSource"),
                ),
            ],
            options={
                "unique_together": {("project", "unique_id")},
            },
        ),
    ]
