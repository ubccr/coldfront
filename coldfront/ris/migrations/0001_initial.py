# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django.db.models.deletion
import djmoney.models.fields
import taggit.managers
from django.conf import settings
from django.db import migrations, models

import coldfront.core.utils
import coldfront.models.deletion
import coldfront.models.utils


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0002_initial"),
        ("ras", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Publication",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                (
                    "doi",
                    models.CharField(
                        help_text="Digital Object Identifier (e.g. 10.1000/xyz). Required.",
                        max_length=255,
                        unique=True,
                        verbose_name="DOI",
                    ),
                ),
                ("title", models.CharField(max_length=500, verbose_name="title")),
                (
                    "authors",
                    models.JSONField(
                        blank=True, default=list, help_text='List of {"name", "orcid"} objects.', verbose_name="authors"
                    ),
                ),
                ("year", models.IntegerField(blank=True, null=True, verbose_name="year")),
                ("journal", models.CharField(blank=True, max_length=255, verbose_name="journal")),
                (
                    "source",
                    models.CharField(
                        help_text="Provider registry key the record was imported from.",
                        max_length=50,
                        verbose_name="source",
                    ),
                ),
                (
                    "external_id",
                    models.CharField(
                        blank=True,
                        help_text="Provider-specific identifier (e.g. an ORCID put code or a Crossref DOI) used to re-fetch metadata.",
                        max_length=255,
                        verbose_name="external ID",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_publications",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="created by",
                    ),
                ),
                (
                    "projects",
                    models.ManyToManyField(
                        blank=True, related_name="publications", to="ras.project", verbose_name="projects"
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
                "verbose_name": "publication",
                "verbose_name_plural": "publications",
                "ordering": ("doi",),
                "permissions": (("unlink", "Can unlink publications from projects"),),
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Funding",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("award_number", models.CharField(max_length=100, verbose_name="award number")),
                ("funding_agency", models.CharField(max_length=100, verbose_name="funding agency")),
                ("title", models.CharField(max_length=500, verbose_name="title")),
                (
                    "amount_awarded_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "amount_awarded",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True, verbose_name="start date")),
                ("end_date", models.DateField(blank=True, null=True, verbose_name="end date")),
                ("status", models.CharField(blank=True, max_length=50, verbose_name="status")),
                (
                    "source",
                    models.CharField(
                        help_text="Provider registry key the record was imported from.",
                        max_length=50,
                        verbose_name="source",
                    ),
                ),
                (
                    "external_id",
                    models.CharField(
                        blank=True,
                        help_text="Provider-specific identifier (e.g. an ORCID put code or an NSF award id) used to re-fetch metadata.",
                        max_length=255,
                        verbose_name="external ID",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_funding",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="created by",
                    ),
                ),
                (
                    "projects",
                    models.ManyToManyField(
                        blank=True, related_name="funding", to="ras.project", verbose_name="projects"
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
                "verbose_name": "funding",
                "verbose_name_plural": "funding",
                "ordering": ("award_number",),
                "permissions": (("unlink", "Can unlink funding from projects"),),
                "unique_together": {("award_number", "funding_agency")},
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
    ]
