# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset, Layout
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from coldfront.billing.choices import (
    ChargeBasisChoices,
    DiscountTypeChoices,
    InvoiceLineTypeChoices,
    InvoiceStatusChoices,
    PaymentMethodChoices,
    UnitFormatChoiceSet,
)
from coldfront.billing.generation import generate_invoice
from coldfront.billing.models import (
    Discount,
    FreeAllowance,
    Invoice,
    InvoiceLineItem,
    Rate,
)
from coldfront.core.choices import CommentKindChoices
from coldfront.core.models import CommentEntry, ObjectType
from coldfront.forms import ColdFrontModelForm, ColdFrontModelImportForm, PrimaryModelForm, PrimaryModelImportForm
from coldfront.forms.fields import (
    CommentField,
    CSVContentTypeObjectField,
    CSVModelChoiceField,
    CSVModelMultipleChoiceField,
    CSVMoneyField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    MoneyField,
)
from coldfront.forms.fields.bytes import BytesField
from coldfront.forms.fields.content_types import ContentTypeChoiceField
from coldfront.forms.fields.csv import CSVChoiceField
from coldfront.forms.mixins import HorizontalFormMixin
from coldfront.forms.widgets import HTMXSelectWidget
from coldfront.ras.models import Project
from coldfront.registry import billing_scope_types, get_billing_sources
from coldfront.users.models import User
from coldfront.users.querysets import RestrictedQuerySet
from coldfront.utils.forms import add_blank_choice, get_field_value

__all__ = (
    "DiscountForm",
    "DiscountImportForm",
    "FreeAllowanceForm",
    "FreeAllowanceImportForm",
    "InvoiceFinalizeForm",
    "InvoiceForm",
    "InvoiceImportForm",
    "InvoiceLineItemForm",
    "InvoiceLineItemImportForm",
    "InvoiceTransitionForm",
    "PaymentForm",
    "RateForm",
    "RateImportForm",
)


class InvoiceForm(PrimaryModelForm):
    owner = DynamicModelChoiceField(
        label=_("Owner"),
        queryset=User.objects.all(),
        required=True,
        selector=True,
        context={
            "label": "username",
            "title": "Username,First Name,Last Name,Email",
            "extra-columns": "first_name,last_name,email",
        },
    )

    projects = DynamicModelMultipleChoiceField(
        label=_("Projects"),
        queryset=Project.objects.all(),
        required=False,
        null_option="All Projects",
        help_text=_("Restrict the invoice to specific projects. 'All Projects' bills all of the owner's projects."),
        query_params={"owner": "$owner"},
    )

    source_types = forms.ModelMultipleChoiceField(
        label=_("Source types"),
        queryset=ContentType.objects.none(),
        required=False,
        help_text=_("Restrict the invoice to specific registered billing source types. Leave empty to bill all."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        source_cts = [ContentType.objects.get_for_model(src["model"]).pk for src in get_billing_sources()]
        self.fields["source_types"].queryset = ContentType.objects.filter(pk__in=source_cts)

    def save(self, commit=True):
        """
        Save the invoice, then generate its line items and totals on creation so
        the whole invoicing step happens at once.
        """
        creating = self.instance.pk is None
        instance = super().save(commit=commit)
        if commit and creating:
            generate_invoice(instance)
        return instance

    class Meta:
        model = Invoice
        fields = [
            "slug",
            "owner",
            "projects",
            "source_types",
            "start_date",
            "end_date",
            "due_date",
            "description",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Invoice"),
                "slug",
                "owner",
                "projects",
                "source_types",
                "description",
            ),
            Fieldset(
                _("Period"),
                "start_date",
                "end_date",
                "due_date",
            ),
        ]


class InvoiceImportForm(PrimaryModelImportForm):
    owner = CSVModelChoiceField(
        queryset=User.objects.all(),
        to_field_name="username",
        label=_("Owner"),
    )

    projects = CSVModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        to_field_name="name",
        label=_("Projects"),
        help_text=_("Project names separated by commas. Leave empty for all of the owner's projects."),
    )

    status = forms.ChoiceField(
        label=_("Status"),
        choices=InvoiceStatusChoices,
    )

    payment_method = forms.ChoiceField(
        label=_("Payment method"),
        choices=PaymentMethodChoices,
        required=False,
    )

    payment_amount = CSVMoneyField(
        label=_("Payment amount"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "100.00" or "100.00 USD").'),
    )
    subtotal = CSVMoneyField(
        label=_("Subtotal"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "100.00" or "100.00 USD").'),
    )
    allowance_total = CSVMoneyField(
        label=_("Allowance total"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "100.00" or "100.00 USD").'),
    )
    discount_total = CSVMoneyField(
        label=_("Discount total"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "100.00" or "100.00 USD").'),
    )
    grand_total = CSVMoneyField(
        label=_("Grand total"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "100.00" or "100.00 USD").'),
    )

    class Meta:
        model = Invoice
        fields = [
            "slug",
            "owner",
            "projects",
            "start_date",
            "end_date",
            "due_date",
            "status",
            "payment_date",
            "payment_amount",
            "payment_method",
            "subtotal",
            "allowance_total",
            "discount_total",
            "grand_total",
            "description",
            "tags",
        ]


class InvoiceLineItemForm(ColdFrontModelForm):
    invoice = forms.ModelChoiceField(
        queryset=Invoice.objects.all(),
        label=_("Invoice"),
    )

    line_type = forms.ChoiceField(
        label=_("Line type"),
        choices=InvoiceLineTypeChoices,
    )

    source_object_type = ContentTypeChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
        label=_("Source type"),
        help_text=_("Content type of the billing source (e.g. a StorageQuota or SlurmAccount)."),
    )
    source_object_id = forms.IntegerField(
        required=False,
        label=_("Source object"),
    )

    unit = forms.CharField(
        max_length=50,
        required=False,
        label=_("Unit"),
        help_text=_("Snapshot of the human-readable unit label (e.g. '1.0 TB')."),
    )
    unit_format = forms.ChoiceField(
        choices=UnitFormatChoiceSet,
        required=False,
        label=_("Unit label"),
        help_text=_("Snapshot of the native unit dimension"),
    )

    unit_price = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Unit price"),
    )
    amount = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Amount"),
    )

    class Meta:
        model = InvoiceLineItem
        fields = [
            "invoice",
            "line_type",
            "source_object_type",
            "source_object_id",
            "description",
            "quantity",
            "unit",
            "unit_format",
            "unit_price",
            "amount",
        ]

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Invoice Line Item"),
                "invoice",
                "line_type",
                "description",
            ),
            Fieldset(
                _("Source"),
                "source_object_type",
                "source_object_id",
            ),
            Fieldset(
                _("Pricing"),
                "quantity",
                "unit",
                "unit_format",
                "unit_price",
                "amount",
            ),
        ]


class InvoiceLineItemImportForm(ColdFrontModelImportForm):
    invoice = CSVModelChoiceField(
        queryset=Invoice.objects.all(),
        to_field_name="slug",
        label=_("Invoice"),
    )

    source_object_type = CSVContentTypeObjectField(
        label=_("Source"),
        required=False,
        help_text=_('Content type and object, e.g. "storage.storagequota:12".'),
    )

    unit = forms.CharField(
        max_length=50,
        required=False,
        label=_("Unit"),
        help_text=_("Snapshot of the human-readable unit label (e.g. '1.0 TB')."),
    )
    unit_format = CSVChoiceField(
        choices=UnitFormatChoiceSet,
        required=False,
        label=_("Unit label"),
        help_text=_("Snapshot of the native unit dimension"),
    )

    unit_price = CSVMoneyField(
        label=_("Unit price"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "100.00" or "100.00 USD").'),
    )
    amount = CSVMoneyField(
        label=_("Amount"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "100.00" or "100.00 USD").'),
    )

    class Meta:
        model = InvoiceLineItem
        fields = [
            "invoice",
            "line_type",
            "source_object_type",
            "description",
            "quantity",
            "unit",
            "unit_format",
            "unit_price",
            "amount",
        ]


class BillingScopeFormMixin(forms.Form):
    """
    Shared HTMX-driven scope selection for Rate and FreeAllowance forms.

    ``scope_object_type`` is limited to registered billing sources and
    ``scope_object_id`` is a select filtered by the selected scope type.
    """

    scope_object_type = ContentTypeChoiceField(
        queryset=ObjectType.objects.none(),
        required=True,
        widget=HTMXSelectWidget(),
        label=_("Scope type"),
        help_text=_("Content type of the rate scope (e.g. a StorageResource or SlurmCluster)."),
    )
    scope_object_id = forms.ChoiceField(
        choices=[],
        required=True,
        widget=HTMXSelectWidget(),
        label=_("Scope object"),
        help_text=_("Select the object to scope this rate to. Options are filtered by the scope type."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit scope types to registered billing sources. On edit, always keep
        # the instance's current scope type selectable so existing records
        # remain editable even if a source was unregistered.
        scope_types = billing_scope_types()
        if self.instance and self.instance.pk and self.instance.scope_object_type_id:
            scope_types |= ObjectType.objects.filter(pk=self.instance.scope_object_type_id)
        self.fields["scope_object_type"].queryset = scope_types
        # Seed the scope fields from the instance when editing an existing record
        if self.instance and self.instance.pk:
            self.fields["scope_object_type"].initial = self.instance.scope_object_type_id
            self.fields["scope_object_id"].initial = self.instance.scope_object_id
        self._populate_scope_object_choices()

    def clean_scope_object_id(self):
        """
        Normalize the ChoiceField's empty string to None so the GenericFK
        validation (BaseModel.clean) sees no object ID when no scope type is
        selected.
        """
        value = self.cleaned_data.get("scope_object_id")
        if value in (None, ""):
            return None
        return value

    def _populate_scope_object_choices(self):
        """
        Filter the scope_object_id select by the selected scope_object_type.

        Reads the current scope type (from POST data or initial value) and builds
        a choice list from the objects of that model. Re-rendered by HTMX when
        the scope type selection changes.
        """
        scope_type_value = get_field_value(self, "scope_object_type")
        scope_type_id = getattr(scope_type_value, "pk", scope_type_value)
        choices = []
        if scope_type_id:
            ct = ContentType.objects.filter(pk=scope_type_id).first()
            if ct is not None and (model := ct.model_class()) is not None:
                qs = model.objects.all()
                if issubclass(qs.__class__, RestrictedQuerySet):
                    qs = qs.restrict(self.user, "view")
                choices = [(obj.pk, str(obj)) for obj in qs]
        self.fields["scope_object_id"].choices = add_blank_choice(choices) if choices else [(None, "---------")]


class RateForm(BillingScopeFormMixin, PrimaryModelForm):
    unit = BytesField(
        label=_("Unit"),
        help_text=_(
            "Native units per billed unit (the divisor). e.g. '1 TB' for per-TB pricing, or '1' for per-SU/per-item."
        ),
    )

    unit_format = forms.ChoiceField(
        label=_("Unit label"),
        choices=UnitFormatChoiceSet,
        help_text=_("The native unit dimension this rate prices"),
    )

    amount = MoneyField(
        required=True,
        max_digits=14,
        decimal_places=2,
        label=_("Amount"),
        help_text=_("Price per billing unit."),
    )

    charge_basis = forms.ChoiceField(
        label=_("Charge basis"),
        choices=ChargeBasisChoices,
    )

    def clean(self):
        super().clean()
        self.billing_sources_hint = None
        self.billing_sources_warning = None
        scope_type = self.cleaned_data.get("scope_object_type")
        scope_id = self.cleaned_data.get("scope_object_id")
        if scope_type and scope_id:
            scope_model = scope_type.model_class()
            sources = get_billing_sources(scope=scope_model)
            if not sources:
                self.billing_sources_warning = _(
                    "No registered billable sources for this resource — nothing will be billed until one is configured."
                )
            else:
                labels = [f"{s['model']._meta.app_label}.{s['model']._meta.model_name}" for s in sources]
                self.billing_sources_hint = _("This rate will bill: %(sources)s.") % {"sources": ", ".join(labels)}

    class Meta:
        model = Rate
        fields = [
            "scope_object_type",
            "scope_object_id",
            "unit",
            "unit_format",
            "amount",
            "charge_basis",
            "effective_start",
            "effective_end",
            "description",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Rate"),
                "scope_object_type",
                "scope_object_id",
                "unit",
                "unit_format",
                "amount",
                "charge_basis",
                "description",
            ),
            Fieldset(
                _("Effective Dates"),
                "effective_start",
                "effective_end",
            ),
        ]


class RateImportForm(PrimaryModelImportForm):
    unit = BytesField(
        label=_("Unit"),
        help_text=_(
            "Native units per billed unit (the divisor). e.g. '1 TB' for per-TB pricing, or '1' for per-SU/per-item."
        ),
    )

    unit_format = CSVChoiceField(
        choices=UnitFormatChoiceSet,
        label=_("Unit label"),
        help_text=_("The native unit dimension this rate prices"),
    )

    amount = CSVMoneyField(
        label=_("Amount"),
        required=False,
        help_text=_('Amount, optionally followed by a currency code (e.g. "100.00" or "100.00 USD").'),
    )

    charge_basis = forms.ChoiceField(
        label=_("Charge basis"),
        choices=ChargeBasisChoices,
    )

    scope_object = CSVContentTypeObjectField(
        label=_("Scope"),
        required=True,
        help_text=_('Content type and object, e.g. "storage.storageresource:3".'),
    )

    class Meta:
        model = Rate
        # scope_object is handled explicitly by CSVContentTypeObjectField
        fields = [
            "unit",
            "unit_format",
            "amount",
            "charge_basis",
            "effective_start",
            "effective_end",
            "description",
            "tags",
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Map the resolved scope_object to the GenericForeignKey fields
        scope_obj = self.cleaned_data.get("scope_object")
        if scope_obj:
            instance.scope_object_type = ContentType.objects.get_for_model(scope_obj)
            instance.scope_object_id = scope_obj.pk

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class FreeAllowanceForm(BillingScopeFormMixin, PrimaryModelForm):
    owner = DynamicModelChoiceField(
        label=_("Owner"),
        queryset=User.objects.all(),
        required=True,
        selector=True,
        context={
            "label": "username",
            "title": "Username,First Name,Last Name,Email",
            "extra-columns": "first_name,last_name,email",
        },
    )

    project = DynamicModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=False,
        null_option="None",
        help_text=_("Optional project scope. Leave empty to apply across all of the owner's projects."),
        query_params={"owner": "$owner"},
    )

    unit_format = forms.ChoiceField(
        label=_("Unit label"),
        choices=UnitFormatChoiceSet,
        help_text=_("The native unit dimension of the allowance"),
    )

    quantity_total = BytesField(
        label=_("Total quantity"),
        help_text=_("Total free units granted, in native units. e.g. '10 TB' or '100'."),
    )

    class Meta:
        model = FreeAllowance
        fields = [
            "owner",
            "project",
            "scope_object_type",
            "scope_object_id",
            "unit_format",
            "quantity_total",
            "used",
            "start_date",
            "end_date",
            "description",
            "tags",
        ]

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Free Allowance"),
                "owner",
                "project",
                "scope_object_type",
                "scope_object_id",
                "unit_format",
                "quantity_total",
                "used",
                "description",
            ),
            Fieldset(
                _("Period"),
                "start_date",
                "end_date",
            ),
        ]


class FreeAllowanceImportForm(PrimaryModelImportForm):
    owner = CSVModelChoiceField(
        queryset=User.objects.all(),
        to_field_name="username",
        label=_("Owner"),
    )

    project = CSVModelChoiceField(
        queryset=Project.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Project"),
    )

    unit_format = CSVChoiceField(
        choices=UnitFormatChoiceSet,
        label=_("Unit label"),
        help_text=_("The native unit dimension of the allowance"),
    )

    quantity_total = BytesField(
        label=_("Total quantity"),
        help_text=_("Total free units granted, in native units. e.g. '10 TB' or '100'."),
    )

    scope_object = CSVContentTypeObjectField(
        label=_("Scope"),
        required=True,
        help_text=_('Content type and object, e.g. "storage.storageresource:3".'),
    )

    class Meta:
        model = FreeAllowance
        # scope_object is handled explicitly by CSVContentTypeObjectField
        fields = [
            "owner",
            "project",
            "unit_format",
            "quantity_total",
            "used",
            "start_date",
            "end_date",
            "description",
            "tags",
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Map the resolved scope_object to the GenericForeignKey fields
        scope_obj = self.cleaned_data.get("scope_object")
        if scope_obj:
            instance.scope_object_type = ContentType.objects.get_for_model(scope_obj)
            instance.scope_object_id = scope_obj.pk

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class DiscountForm(PrimaryModelForm):
    owner = DynamicModelChoiceField(
        label=_("Owner"),
        queryset=User.objects.all(),
        required=True,
        selector=True,
        context={
            "label": "username",
            "title": "Username,First Name,Last Name,Email",
            "extra-columns": "first_name,last_name,email",
        },
    )

    project = DynamicModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=False,
        null_option="None",
        help_text=_("Optional project scope. Leave empty for a user-level discount."),
        query_params={"owner": "$owner"},
    )

    type = forms.ChoiceField(
        label=_("Type"),
        choices=DiscountTypeChoices,
    )

    class Meta:
        model = Discount
        fields = ["owner", "project", "type", "value", "description", "tags"]

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Discount"),
                "owner",
                "project",
                "type",
                "value",
                "description",
                "tags",
            ),
        ]


class DiscountImportForm(PrimaryModelImportForm):
    owner = CSVModelChoiceField(
        queryset=User.objects.all(),
        to_field_name="username",
        label=_("Owner"),
    )

    project = CSVModelChoiceField(
        queryset=Project.objects.all(),
        to_field_name="name",
        required=False,
        label=_("Project"),
    )

    type = forms.ChoiceField(
        label=_("Type"),
        choices=DiscountTypeChoices,
    )

    class Meta:
        model = Discount
        fields = ["owner", "project", "type", "value", "description", "tags"]


class InvoiceTransitionFormMixin(forms.Form):
    """
    Base mixin for invoice workflow transition forms (generate, invoice, pay, void).

    Provides a single optional comments field and records any comment as a
    CommentEntry on the invoice, mirroring the Allocation review forms. Unlike
    ``ColdFrontModelForm`` it carries no tags or changelog-message fields.
    """

    comments = CommentField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    @property
    def fieldsets(self):
        return Layout("comments")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self._create_comment_entry()
        return instance

    def _create_comment_entry(self):
        comments = self.cleaned_data.get("comments")
        if comments:
            CommentEntry.objects.create(
                assigned_object=self.instance,
                created_by=self.user,
                kind=CommentKindChoices.KIND_INFO,
                comments=comments,
            )


class InvoiceTransitionForm(InvoiceTransitionFormMixin, HorizontalFormMixin, forms.ModelForm):
    """
    Empty form used by status transitions that need no user input (e.g. void).
    """

    owner = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("Owner"),
        required=False,
        disabled=True,
    )

    class Meta:
        model = Invoice
        fields = [
            "slug",
            "owner",
        ]

    @property
    def fieldsets(self):
        return [
            Layout(
                "owner",
                "comments",
            ),
        ]


class InvoiceFinalizeForm(InvoiceTransitionFormMixin, HorizontalFormMixin, forms.ModelForm):
    """
    Finalize transition: block if the invoice has no valid charge lines.
    """

    class Meta:
        model = Invoice
        fields = []

    def clean(self):
        super().clean()
        invoice = self.instance
        if (
            invoice.pk
            and not invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE, is_valid=True).exists()
        ):
            self.add_error(
                None,
                _("This invoice has no valid line items; fix invalid lines or generate first."),
            )


class PaymentForm(InvoiceTransitionFormMixin, HorizontalFormMixin, forms.ModelForm):
    payment_date = forms.DateTimeField(
        label=_("Payment date"),
        required=False,
    )
    payment_amount = MoneyField(
        required=False,
        max_digits=14,
        decimal_places=2,
        label=_("Payment amount"),
    )
    payment_method = forms.ChoiceField(
        label=_("Payment method"),
        choices=PaymentMethodChoices,
        required=False,
    )

    class Meta:
        model = Invoice
        fields = ["payment_date", "payment_amount", "payment_method"]

    @property
    def fieldsets(self):
        return Layout("payment_date", "payment_amount", "payment_method", "comments")
