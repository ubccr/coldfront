# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from djmoney.money import Money

from coldfront.billing.choices import (
    ChargeBasisChoices,
    DiscountTypeChoices,
    InvoiceLineTypeChoices,
    InvoiceStatusChoices,
    UnitFormatChoiceSet,
)
from coldfront.billing.models import (
    Discount,
    FreeAllowance,
    Invoice,
    InvoiceLineItem,
    Rate,
)
from coldfront.ras.models import Project, Resource, ResourceType
from coldfront.users.models import User
from coldfront.utils.testing import APIViewTestCases


class InvoiceTest(APIViewTestCases.APIViewTestCase):
    model = Invoice
    brief_fields = ["display", "due_date", "id", "owner", "slug", "status", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    def model_to_dict(self, instance, fields, api=False):
        """Normalize django-money values to their numeric amount for comparison."""
        model_dict = super().model_to_dict(instance, fields, api=api)
        for key, value in list(model_dict.items()):
            if isinstance(value, Money):
                model_dict[key] = value.amount
        return model_dict

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")

        Invoice.objects.create(slug="INV-1", owner=owner, status=InvoiceStatusChoices.STATUS_DRAFT)
        Invoice.objects.create(slug="INV-2", owner=owner, status=InvoiceStatusChoices.STATUS_INVOICED)
        Invoice.objects.create(slug="INV-3", owner=owner, status=InvoiceStatusChoices.STATUS_PAID)

        cls.create_data = [
            {
                "slug": "INV-X1",
                "owner": owner.pk,
                "status": InvoiceStatusChoices.STATUS_DRAFT,
                "subtotal": Decimal("100.00"),
                "grand_total": Decimal("100.00"),
                "description": "A new invoice",
            },
            {
                "slug": "INV-X2",
                "owner": owner.pk,
                "status": InvoiceStatusChoices.STATUS_DRAFT,
                "description": "A new invoice",
            },
            {
                "slug": "INV-X3",
                "owner": owner.pk,
                "status": InvoiceStatusChoices.STATUS_DRAFT,
                "description": "A new invoice",
            },
        ]


class RateTest(APIViewTestCases.APIViewTestCase):
    model = Rate
    brief_fields = ["amount", "charge_basis", "display", "id", "unit", "unit_format", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    def model_to_dict(self, instance, fields, api=False):
        """Normalize django-money values to their numeric amount for comparison."""
        model_dict = super().model_to_dict(instance, fields, api=api)
        for key, value in list(model_dict.items()):
            if isinstance(value, Money):
                model_dict[key] = value.amount
        return model_dict

    @classmethod
    def setUpTestData(cls):
        resource_type = ResourceType.objects.create(name="Cluster")

        resources = (
            Resource(name="Resource 1", slug="r-1", resource_type=resource_type),
            Resource(name="Resource 2", slug="r-2", resource_type=resource_type),
            Resource(name="Resource 3", slug="r-3", resource_type=resource_type),
            Resource(name="Resource 4", slug="r-4", resource_type=resource_type),
            Resource(name="Resource 5", slug="r-5", resource_type=resource_type),
            Resource(name="Resource 6", slug="r-6", resource_type=resource_type),
        )
        for resource in resources:
            resource.save()

        resource_ct = ContentType.objects.get_for_model(Resource)
        Rate.objects.create(
            scope_object_type=resource_ct,
            scope_object_id=resources[0].pk,
            unit=10**12,
            unit_format=UnitFormatChoiceSet.UNIT_BYTES,
            amount="10.00",
            charge_basis=ChargeBasisChoices.BASIS_MONTHLY,
        )
        Rate.objects.create(
            scope_object_type=resource_ct,
            scope_object_id=resources[1].pk,
            unit=10**12,
            unit_format=UnitFormatChoiceSet.UNIT_BYTES,
            amount="20.00",
            charge_basis=ChargeBasisChoices.BASIS_MONTHLY,
        )
        Rate.objects.create(
            scope_object_type=resource_ct,
            scope_object_id=resources[2].pk,
            unit=10**12,
            unit_format=UnitFormatChoiceSet.UNIT_BYTES,
            amount="30.00",
            charge_basis=ChargeBasisChoices.BASIS_MONTHLY,
        )

        cls.create_data = [
            {
                "scope_object_type": "ras.resource",
                "scope_object_id": resources[3].pk,
                "unit": 10**12,
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "amount": Decimal("10.00"),
                "charge_basis": ChargeBasisChoices.BASIS_MONTHLY,
                "description": "A new rate",
            },
            {
                "scope_object_type": "ras.resource",
                "scope_object_id": resources[4].pk,
                "unit": 10**12,
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "amount": Decimal("20.00"),
                "charge_basis": ChargeBasisChoices.BASIS_MONTHLY,
                "description": "A new rate",
            },
            {
                "scope_object_type": "ras.resource",
                "scope_object_id": resources[5].pk,
                "unit": 10**12,
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "amount": Decimal("30.00"),
                "charge_basis": ChargeBasisChoices.BASIS_MONTHLY,
                "description": "A new rate",
            },
        ]


class FreeAllowanceTest(APIViewTestCases.APIViewTestCase):
    model = FreeAllowance
    brief_fields = ["display", "id", "owner", "project", "quantity_total", "unit_format", "url", "used"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")
        projects = (
            Project.objects.create(name="Project 1", owner=owner),
            Project.objects.create(name="Project 2", owner=owner),
            Project.objects.create(name="Project 3", owner=owner),
        )
        resource_type = ResourceType.objects.create(name="Cluster")

        resources = (
            Resource(name="Resource 1", slug="r-1", resource_type=resource_type),
            Resource(name="Resource 2", slug="r-2", resource_type=resource_type),
            Resource(name="Resource 3", slug="r-3", resource_type=resource_type),
        )
        for resource in resources:
            resource.save()

        resource_ct = ContentType.objects.get_for_model(Resource)
        allowances = (
            FreeAllowance.objects.create(
                owner=owner,
                scope_object_type=resource_ct,
                scope_object_id=resources[0].pk,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                quantity_total=100,
            ),
            FreeAllowance.objects.create(
                owner=owner,
                scope_object_type=resource_ct,
                scope_object_id=resources[1].pk,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                quantity_total=200,
            ),
            FreeAllowance.objects.create(
                owner=owner,
                scope_object_type=resource_ct,
                scope_object_id=resources[2].pk,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                quantity_total=300,
            ),
        )
        allowances[1].project = projects[1]

        cls.create_data = [
            {
                "owner": owner.pk,
                "project": projects[0].pk,
                "scope_object_type": "ras.resource",
                "scope_object_id": resources[0].pk,
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "quantity_total": Decimal("100"),
                "description": "A new allowance",
            },
            {
                "owner": owner.pk,
                "project": projects[1].pk,
                "scope_object_type": "ras.resource",
                "scope_object_id": resources[1].pk,
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "quantity_total": Decimal("200"),
                "description": "A new allowance",
            },
            {
                "owner": owner.pk,
                "project": projects[2].pk,
                "scope_object_type": "ras.resource",
                "scope_object_id": resources[2].pk,
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "quantity_total": Decimal("300"),
                "description": "A new allowance",
            },
        ]


class DiscountTest(APIViewTestCases.APIViewTestCase):
    model = Discount
    brief_fields = ["display", "id", "owner", "project", "type", "url", "value"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")
        projects = (
            Project.objects.create(name="Project 1", owner=owner),
            Project.objects.create(name="Project 2", owner=owner),
            Project.objects.create(name="Project 3", owner=owner),
        )

        Discount.objects.create(owner=owner, type=DiscountTypeChoices.TYPE_PERCENTAGE, value=10)
        Discount.objects.create(owner=owner, type=DiscountTypeChoices.TYPE_PERCENTAGE, value=20)
        Discount.objects.create(owner=owner, type=DiscountTypeChoices.TYPE_PERCENTAGE, value=30)

        cls.create_data = [
            {
                "owner": owner.pk,
                "project": projects[0].pk,
                "type": DiscountTypeChoices.TYPE_PERCENTAGE,
                "value": Decimal("10"),
                "description": "A new discount",
            },
            {
                "owner": owner.pk,
                "project": projects[1].pk,
                "type": DiscountTypeChoices.TYPE_PERCENTAGE,
                "value": Decimal("20"),
                "description": "A new discount",
            },
            {
                "owner": owner.pk,
                "project": projects[2].pk,
                "type": DiscountTypeChoices.TYPE_PERCENTAGE,
                "value": Decimal("30"),
                "description": "A new discount",
            },
        ]


class InvoiceLineItemTest(APIViewTestCases.APIViewTestCase):
    model = InvoiceLineItem
    brief_fields = ["display", "id", "invoice", "line_type", "quantity", "unit", "unit_format", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    def model_to_dict(self, instance, fields, api=False):
        """Normalize django-money values to their numeric amount for comparison."""
        model_dict = super().model_to_dict(instance, fields, api=api)
        for key, value in list(model_dict.items()):
            if isinstance(value, Money):
                model_dict[key] = value.amount
        return model_dict

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")
        resource_type = ResourceType.objects.create(name="Cluster")

        resource = Resource.objects.create(name="Resource 1", slug="r-1", resource_type=resource_type)

        invoice = Invoice.objects.create(
            slug="INV-1",
            owner=owner,
            status=InvoiceStatusChoices.STATUS_DRAFT,
        )

        resource_ct = ContentType.objects.get_for_model(Resource)
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_type=InvoiceLineTypeChoices.TYPE_CHARGE,
            source_object_type=resource_ct,
            source_object_id=resource.pk,
            unit="1.0 TB",
            unit_format=UnitFormatChoiceSet.UNIT_BYTES,
            quantity=1,
            amount="10.00",
        )
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_type=InvoiceLineTypeChoices.TYPE_CHARGE,
            source_object_type=resource_ct,
            source_object_id=resource.pk,
            unit="1.0 TB",
            unit_format=UnitFormatChoiceSet.UNIT_BYTES,
            quantity=2,
            amount="20.00",
        )
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_type=InvoiceLineTypeChoices.TYPE_CHARGE,
            source_object_type=resource_ct,
            source_object_id=resource.pk,
            unit="1.0 TB",
            unit_format=UnitFormatChoiceSet.UNIT_BYTES,
            quantity=3,
            amount="30.00",
        )

        cls.create_data = [
            {
                "invoice": invoice.pk,
                "line_type": InvoiceLineTypeChoices.TYPE_CHARGE,
                "source_object_type": "ras.resource",
                "source_object_id": resource.pk,
                "unit": "1.0 TB",
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "quantity": 1,
                "unit_price": Decimal("10.00"),
                "amount": Decimal("10.00"),
                "description": "A new line item",
            },
            {
                "invoice": invoice.pk,
                "line_type": InvoiceLineTypeChoices.TYPE_CHARGE,
                "source_object_type": "ras.resource",
                "source_object_id": resource.pk,
                "unit": "1.0 TB",
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "quantity": 2,
                "unit_price": Decimal("20.00"),
                "amount": Decimal("20.00"),
                "description": "A new line item",
            },
            {
                "invoice": invoice.pk,
                "line_type": InvoiceLineTypeChoices.TYPE_CHARGE,
                "source_object_type": "ras.resource",
                "source_object_id": resource.pk,
                "unit": "1.0 TB",
                "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
                "quantity": 3,
                "unit_price": Decimal("30.00"),
                "amount": Decimal("30.00"),
                "description": "A new line item",
            },
        ]
