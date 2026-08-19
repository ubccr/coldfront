# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django.core.validators
import django.db.models.deletion
import djmoney.models.fields
import taggit.managers
from django.conf import settings
from django.db import migrations, models

import coldfront.core.utils
import coldfront.models.deletion
import coldfront.models.fields
import coldfront.models.utils


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("core", "0002_initial"),
        ("ras", "0003_projectinvite"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Discount",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "type",
                    models.CharField(
                        choices=[("percentage", "Percentage"), ("flat", "Flat"), ("no_cost", "No cost")],
                        default="percentage",
                        max_length=50,
                        verbose_name="type",
                    ),
                ),
                (
                    "value",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Percentage (0-100) or flat amount depending on the type.",
                        max_digits=10,
                        null=True,
                        verbose_name="value",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="discounts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owner",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        help_text="Optional project scope. Leave empty for a user-level discount.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="discounts",
                        to="ras.project",
                        verbose_name="project",
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
                "verbose_name": "discount",
                "verbose_name_plural": "discounts",
                "ordering": ["created"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="FreeAllowance",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("scope_object_id", models.PositiveBigIntegerField(verbose_name="scope object")),
                (
                    "unit_format",
                    models.CharField(
                        choices=[
                            ("bytes", "Bytes"),
                            ("service_units", "Service Units"),
                            ("core_hours", "Core Hours"),
                            ("per_item", "Flat / per-item"),
                        ],
                        default="per_item",
                        help_text="The native unit dimension of the allowance",
                        max_length=50,
                        verbose_name="unit format",
                    ),
                ),
                (
                    "quantity_total",
                    models.PositiveBigIntegerField(
                        help_text="Total free units granted, in native units (e.g. bytes).",
                        verbose_name="total quantity",
                    ),
                ),
                (
                    "used",
                    models.PositiveBigIntegerField(
                        default=0, help_text="Free units already consumed against invoices.", verbose_name="used"
                    ),
                ),
                ("start_date", models.DateTimeField(blank=True, null=True, verbose_name="start date")),
                ("end_date", models.DateTimeField(blank=True, null=True, verbose_name="end date")),
                (
                    "owner",
                    models.ForeignKey(
                        help_text="The user granted this free allowance.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="free_allowances",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owner",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        help_text="Optional project scope. Leave empty to apply across all of the owner's projects.",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="free_allowances",
                        to="ras.project",
                        verbose_name="project",
                    ),
                ),
                (
                    "scope_object_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="billing_free_allowances",
                        to="contenttypes.contenttype",
                        verbose_name="scope type",
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
                "verbose_name": "free allowance",
                "verbose_name_plural": "free allowances",
                "ordering": ["created"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "slug",
                    coldfront.models.fields.AutoSlugField(
                        blank=True,
                        help_text="Unique slug. Leave blank and one will be auto generated.",
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
                ("start_date", models.DateTimeField(blank=True, null=True, verbose_name="start date")),
                ("end_date", models.DateTimeField(blank=True, null=True, verbose_name="end date")),
                ("due_date", models.DateTimeField(blank=True, null=True, verbose_name="due date")),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("invoiced", "Invoiced"), ("paid", "Paid"), ("void", "Void")],
                        default="draft",
                        max_length=50,
                        verbose_name="status",
                    ),
                ),
                ("payment_date", models.DateTimeField(blank=True, null=True, verbose_name="payment date")),
                (
                    "payment_amount_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "payment_amount",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="payment amount",
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("wire", "Wire transfer"),
                            ("check", "Check"),
                            ("po", "Purchase order"),
                            ("internal", "Internal transfer"),
                        ],
                        max_length=50,
                        verbose_name="payment method",
                    ),
                ),
                (
                    "subtotal_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "subtotal",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="subtotal",
                    ),
                ),
                (
                    "allowance_total_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "allowance_total",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="allowance total",
                    ),
                ),
                (
                    "discount_total_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "discount_total",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="discount total",
                    ),
                ),
                (
                    "grand_total_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "grand_total",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="grand total",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        help_text="The user responsible for paying this invoice.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="owned_invoices",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="owner",
                    ),
                ),
                (
                    "projects",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Restrict the invoice to specific projects. Leave empty to bill all of the owner's projects.",
                        related_name="invoices",
                        to="ras.project",
                        verbose_name="projects",
                    ),
                ),
                (
                    "source_types",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Restrict the invoice to specific registered billing source types. Leave empty to bill all.",
                        related_name="billing_invoices",
                        to="contenttypes.contenttype",
                        verbose_name="source types",
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
                "verbose_name": "invoice",
                "verbose_name_plural": "invoices",
                "ordering": ["created"],
                "permissions": (
                    ("generate_invoice", "Generate invoice"),
                    ("finalize_invoice", "Finalize invoice"),
                    ("pay_invoice", "Pay invoice"),
                    ("void_invoice", "Void invoice"),
                ),
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="InvoiceLineItem",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "line_type",
                    models.CharField(
                        choices=[
                            ("charge", "Charge"),
                            ("free_allowance", "Free allowance"),
                            ("discount", "Discount"),
                            ("credit", "Credit"),
                        ],
                        default="charge",
                        max_length=50,
                        verbose_name="line type",
                    ),
                ),
                (
                    "source_object_id",
                    models.PositiveBigIntegerField(blank=True, null=True, verbose_name="source object"),
                ),
                (
                    "is_valid",
                    models.BooleanField(
                        default=True,
                        help_text="False if the line could not be priced at generation time and needs fixing.",
                        verbose_name="valid",
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "quantity",
                    models.PositiveBigIntegerField(
                        blank=True,
                        help_text="Quantity in the source's native units (e.g. bytes).",
                        null=True,
                        verbose_name="quantity",
                    ),
                ),
                (
                    "unit",
                    models.CharField(
                        blank=True,
                        help_text="Snapshot of the human-readable unit label at generation time (e.g. '1.0 TB').",
                        max_length=50,
                        verbose_name="unit",
                    ),
                ),
                (
                    "unit_format",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("bytes", "Bytes"),
                            ("service_units", "Service Units"),
                            ("core_hours", "Core Hours"),
                            ("per_item", "Flat / per-item"),
                        ],
                        help_text="Snapshot of the native unit dimension at generation time",
                        max_length=50,
                        verbose_name="unit format",
                    ),
                ),
                (
                    "unit_price_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "unit_price",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="unit price",
                    ),
                ),
                (
                    "amount_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "amount",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="amount",
                    ),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="line_items",
                        to="billing.invoice",
                        verbose_name="invoice",
                    ),
                ),
                (
                    "source_object_type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="billing_line_items",
                        to="contenttypes.contenttype",
                        verbose_name="source type",
                    ),
                ),
            ],
            options={
                "verbose_name": "invoice line item",
                "verbose_name_plural": "invoice line items",
                "ordering": ["invoice", "id"],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Rate",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True, null=True, verbose_name="created")),
                ("last_updated", models.DateTimeField(auto_now=True, null=True, verbose_name="last updated")),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=coldfront.core.utils.CustomFieldJSONEncoder),
                ),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("scope_object_id", models.PositiveBigIntegerField(verbose_name="scope object")),
                (
                    "unit",
                    models.PositiveBigIntegerField(
                        help_text="Native units per billed unit (the divisor). e.g. 1.0 TB for per-TB pricing.",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="unit",
                    ),
                ),
                (
                    "unit_format",
                    models.CharField(
                        choices=[
                            ("bytes", "Bytes"),
                            ("service_units", "Service Units"),
                            ("core_hours", "Core Hours"),
                            ("per_item", "Flat / per-item"),
                        ],
                        help_text="The native unit dimension this rate prices",
                        max_length=50,
                        verbose_name="unit format",
                    ),
                ),
                (
                    "amount_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.models.utils.get_currency_choices,
                        default=coldfront.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                    ),
                ),
                (
                    "amount",
                    djmoney.models.fields.MoneyField(
                        currency_choices=coldfront.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.models.utils.get_default_currency,
                        help_text="Price per billing unit.",
                        max_digits=14,
                        verbose_name="amount",
                    ),
                ),
                (
                    "charge_basis",
                    models.CharField(
                        choices=[("one_time", "One time"), ("monthly", "Monthly"), ("yearly", "Yearly")],
                        default="one_time",
                        max_length=50,
                        verbose_name="charge basis",
                    ),
                ),
                ("effective_start", models.DateTimeField(blank=True, null=True, verbose_name="effective start")),
                ("effective_end", models.DateTimeField(blank=True, null=True, verbose_name="effective end")),
                (
                    "scope_object_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="billing_rates",
                        to="contenttypes.contenttype",
                        verbose_name="scope type",
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
                "verbose_name": "rate",
                "verbose_name_plural": "rates",
                "ordering": ["created"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("scope_object_type", "scope_object_id"), name="billing_rate_unique_scope"
                    ),
                    models.CheckConstraint(condition=models.Q(("unit__gt", 0)), name="billing_rate_unit_positive"),
                ],
            },
            bases=(coldfront.models.deletion.DeleteMixin, models.Model),
        ),
    ]
