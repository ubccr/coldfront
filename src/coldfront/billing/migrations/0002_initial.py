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
        ("billing", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="discount",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                help_text="The user this discount applies to. Leave empty for a global or resource-scoped discount.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="discounts",
                to=settings.AUTH_USER_MODEL,
                verbose_name="owner",
            ),
        ),
        migrations.AddField(
            model_name="discount",
            name="scope_object_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="billing_discounts",
                to="contenttypes.contenttype",
                verbose_name="scope type",
            ),
        ),
        migrations.AddField(
            model_name="discount",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="core.TaggedItem",
                to="core.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="freeallowance",
            name="owner",
            field=models.ForeignKey(
                help_text="The user granted this free allowance.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="free_allowances",
                to=settings.AUTH_USER_MODEL,
                verbose_name="owner",
            ),
        ),
        migrations.AddField(
            model_name="freeallowance",
            name="scope_object_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="billing_free_allowances",
                to="contenttypes.contenttype",
                verbose_name="scope type",
            ),
        ),
        migrations.AddField(
            model_name="freeallowance",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="core.TaggedItem",
                to="core.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="owner",
            field=models.ForeignKey(
                help_text="The user responsible for paying this invoice.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="owned_invoices",
                to=settings.AUTH_USER_MODEL,
                verbose_name="owner",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="source_types",
            field=models.ManyToManyField(
                blank=True,
                help_text="Restrict the invoice to specific registered billing source types. Leave empty to bill all.",
                related_name="billing_invoices",
                to="contenttypes.contenttype",
                verbose_name="source types",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="core.TaggedItem",
                to="core.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="invoicelineitem",
            name="invoice",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="line_items",
                to="billing.invoice",
                verbose_name="invoice",
            ),
        ),
        migrations.AddField(
            model_name="invoicelineitem",
            name="source_object_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="billing_line_items",
                to="contenttypes.contenttype",
                verbose_name="source type",
            ),
        ),
        migrations.AddField(
            model_name="rate",
            name="scope_object_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="billing_rates",
                to="contenttypes.contenttype",
                verbose_name="scope type",
            ),
        ),
        migrations.AddField(
            model_name="rate",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="core.TaggedItem",
                to="core.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddConstraint(
            model_name="rate",
            constraint=models.UniqueConstraint(
                fields=("scope_object_type", "scope_object_id"), name="billing_rate_unique_scope"
            ),
        ),
        migrations.AddConstraint(
            model_name="rate",
            constraint=models.CheckConstraint(condition=models.Q(("unit__gt", 0)), name="billing_rate_unit_positive"),
        ),
    ]
