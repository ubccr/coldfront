# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django.core.validators
import djmoney.models.fields
from django.db import migrations, models

import coldfront.core.utils
import coldfront.lib.models.deletion
import coldfront.lib.models.fields
import coldfront.lib.models.utils


class Migration(migrations.Migration):
    initial = True

    dependencies = []

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
                ("name", models.CharField(default="", max_length=100, unique=True, verbose_name="name")),
                ("scope_object_id", models.PositiveBigIntegerField(blank=True, null=True, verbose_name="scope object")),
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
            ],
            options={
                "verbose_name": "discount",
                "verbose_name_plural": "discounts",
                "ordering": ["created"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
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
                ("name", models.CharField(default="", max_length=100, unique=True, verbose_name="name")),
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
            ],
            options={
                "verbose_name": "free allowance",
                "verbose_name_plural": "free allowances",
                "ordering": ["created"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
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
                    coldfront.lib.models.fields.AutoSlugField(
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
                        choices=coldfront.lib.models.utils.get_currency_choices,
                        default=coldfront.lib.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "payment_amount",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.lib.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.lib.models.utils.get_default_currency,
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
                        choices=coldfront.lib.models.utils.get_currency_choices,
                        default=coldfront.lib.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "subtotal",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.lib.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.lib.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="subtotal",
                    ),
                ),
                (
                    "allowance_total_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.lib.models.utils.get_currency_choices,
                        default=coldfront.lib.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "allowance_total",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.lib.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.lib.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="allowance total",
                    ),
                ),
                (
                    "discount_total_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.lib.models.utils.get_currency_choices,
                        default=coldfront.lib.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "discount_total",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.lib.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.lib.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="discount total",
                    ),
                ),
                (
                    "grand_total_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.lib.models.utils.get_currency_choices,
                        default=coldfront.lib.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "grand_total",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.lib.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.lib.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="grand total",
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
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
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
                        choices=coldfront.lib.models.utils.get_currency_choices,
                        default=coldfront.lib.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "unit_price",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.lib.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.lib.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="unit price",
                    ),
                ),
                (
                    "amount_currency",
                    djmoney.models.fields.CurrencyField(
                        choices=coldfront.lib.models.utils.get_currency_choices,
                        default=coldfront.lib.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                        null=True,
                    ),
                ),
                (
                    "amount",
                    djmoney.models.fields.MoneyField(
                        blank=True,
                        currency_choices=coldfront.lib.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.lib.models.utils.get_default_currency,
                        max_digits=14,
                        null=True,
                        verbose_name="amount",
                    ),
                ),
            ],
            options={
                "verbose_name": "invoice line item",
                "verbose_name_plural": "invoice line items",
                "ordering": ["invoice", "id"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
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
                ("name", models.CharField(default="", max_length=100, unique=True, verbose_name="name")),
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
                        choices=coldfront.lib.models.utils.get_currency_choices,
                        default=coldfront.lib.models.utils.get_default_currency,
                        editable=False,
                        max_length=3,
                    ),
                ),
                (
                    "amount",
                    djmoney.models.fields.MoneyField(
                        currency_choices=coldfront.lib.models.utils.get_currency_choices,
                        decimal_places=2,
                        default_currency=coldfront.lib.models.utils.get_default_currency,
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
            ],
            options={
                "verbose_name": "rate",
                "verbose_name_plural": "rates",
                "ordering": ["created"],
            },
            bases=(coldfront.lib.models.deletion.DeleteMixin, models.Model),
        ),
    ]
