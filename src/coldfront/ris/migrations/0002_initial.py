# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django.db.models.deletion
import taggit.managers
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_initial"),
        ("ras", "0001_initial"),
        ("ris", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="funding",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_funding",
                to=settings.AUTH_USER_MODEL,
                verbose_name="created by",
            ),
        ),
        migrations.AddField(
            model_name="funding",
            name="projects",
            field=models.ManyToManyField(blank=True, related_name="funding", to="ras.project", verbose_name="projects"),
        ),
        migrations.AddField(
            model_name="funding",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="core.TaggedItem",
                to="core.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="publication",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_publications",
                to=settings.AUTH_USER_MODEL,
                verbose_name="created by",
            ),
        ),
        migrations.AddField(
            model_name="publication",
            name="projects",
            field=models.ManyToManyField(
                blank=True, related_name="publications", to="ras.project", verbose_name="projects"
            ),
        ),
        migrations.AddField(
            model_name="publication",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="core.TaggedItem",
                to="core.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="funding",
            unique_together={("award_number", "funding_agency")},
        ),
    ]
