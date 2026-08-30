# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.contrib.contenttypes.models import ContentType

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
from coldfront.storage.models import StorageResource
from coldfront.users.models import User
from coldfront.utils.testing import ViewTestCases


class InvoiceTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Invoice

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")

        invoices = (
            Invoice.objects.create(
                slug="INV-1",
                owner=owner,
                status=InvoiceStatusChoices.STATUS_DRAFT,
            ),
            Invoice.objects.create(
                slug="INV-2",
                owner=owner,
                status=InvoiceStatusChoices.STATUS_INVOICED,
            ),
            Invoice.objects.create(
                slug="INV-3",
                owner=owner,
                status=InvoiceStatusChoices.STATUS_PAID,
            ),
        )

        cls.form_data = {
            "slug": "INV-X",
            "owner": owner.pk,
            "description": "A new invoice",
        }

        cls.csv_data = (
            "slug,owner,status,description",
            "INV-4,pi,draft,Fourth invoice",
            "INV-5,pi,invoiced,Fifth invoice",
            "INV-6,pi,paid,Sixth invoice",
        )

        cls.csv_update_data = (
            "id,description",
            f"{invoices[0].pk},Fourth invoice7",
            f"{invoices[1].pk},Fifth invoice8",
            f"{invoices[2].pk},Sixth invoice9",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated invoice",
        }


class RateTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Rate
    validation_excluded_fields = ("scope_object", "unit")

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")
        project = Project.objects.create(name="Project 1", owner=owner)

        resources = tuple(StorageResource(name=f"Storage Resource {i}") for i in range(1, 7))
        for resource in resources:
            resource.save()

        resource_ct = ContentType.objects.get_for_model(StorageResource)
        rates = (
            Rate.objects.create(
                name="Rate 1",
                scope_object_type=resource_ct,
                scope_object_id=resources[0].pk,
                unit=10**12,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                amount="10.00",
                charge_basis=ChargeBasisChoices.BASIS_MONTHLY,
            ),
            Rate.objects.create(
                name="Rate 2",
                scope_object_type=resource_ct,
                scope_object_id=resources[1].pk,
                unit=10**12,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                amount="20.00",
                charge_basis=ChargeBasisChoices.BASIS_MONTHLY,
            ),
            Rate.objects.create(
                name="Rate 3",
                scope_object_type=resource_ct,
                scope_object_id=resources[2].pk,
                unit=10**12,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                amount="30.00",
                charge_basis=ChargeBasisChoices.BASIS_MONTHLY,
            ),
        )

        cls.form_data = {
            "name": "Fourth rate",
            "scope_object_type": resource_ct.pk,
            "scope_object_id": resources[3].pk,
            "unit": "1 TB",
            "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
            "amount_0": "10.00",
            "amount_1": "USD",
            "charge_basis": ChargeBasisChoices.BASIS_MONTHLY,
            "project": project.pk,
            "description": "A new rate",
        }

        cls.csv_data = (
            "name,unit,unit_format,amount,charge_basis,description,scope_object",
            "Fourth rate,1 TB,bytes,10.00,monthly,Fourth rate,storage.storageresource:Storage Resource 4",
            "Fifth rate,1 TB,bytes,20.00,monthly,Fifth rate,storage.storageresource:Storage Resource 5",
            "Sixth rate,1 TB,bytes,30.00,monthly,Sixth rate,storage.storageresource:Storage Resource 6",
        )

        cls.csv_update_data = (
            "id,description",
            f"{rates[0].pk},Fourth rate7",
            f"{rates[1].pk},Fifth rate8",
            f"{rates[2].pk},Sixth rate9",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated rate",
        }


class FreeAllowanceTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = FreeAllowance
    validation_excluded_fields = ("scope_object", "quantity_total")

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")

        resources = tuple(StorageResource(name=f"Storage Resource {i}") for i in range(1, 7))
        for resource in resources:
            resource.save()

        resource_ct = ContentType.objects.get_for_model(StorageResource)
        allowances = (
            FreeAllowance.objects.create(
                name="Allowance 1",
                owner=owner,
                scope_object_type=resource_ct,
                scope_object_id=resources[0].pk,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                quantity_total=100,
            ),
            FreeAllowance.objects.create(
                name="Allowance 2",
                owner=owner,
                scope_object_type=resource_ct,
                scope_object_id=resources[1].pk,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                quantity_total=200,
            ),
            FreeAllowance.objects.create(
                name="Allowance 3",
                owner=owner,
                scope_object_type=resource_ct,
                scope_object_id=resources[2].pk,
                unit_format=UnitFormatChoiceSet.UNIT_BYTES,
                quantity_total=300,
            ),
        )

        cls.form_data = {
            "name": "Fourth allowance",
            "owner": owner.pk,
            "scope_object_type": resource_ct.pk,
            "scope_object_id": resources[3].pk,
            "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
            "quantity_total": "100",
            "used": 0,
            "description": "A new allowance",
        }

        cls.csv_data = (
            "name,owner,unit_format,quantity_total,used,description,scope_object",
            "Fourth allowance,pi,bytes,100,0,Fourth allowance,storage.storageresource:Storage Resource 4",
            "Fifth allowance,pi,bytes,200,0,Fifth allowance,storage.storageresource:Storage Resource 5",
            "Sixth allowance,pi,bytes,300,0,Sixth allowance,storage.storageresource:Storage Resource 6",
        )

        cls.csv_update_data = (
            "id,description",
            f"{allowances[0].pk},Fourth allowance7",
            f"{allowances[1].pk},Fifth allowance8",
            f"{allowances[2].pk},Sixth allowance9",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated allowance",
        }


class DiscountTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Discount

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user(username="pi")

        resources = tuple(StorageResource(name=f"Storage Resource {i}") for i in range(1, 4))
        for resource in resources:
            resource.save()
        resource_ct = ContentType.objects.get_for_model(StorageResource)

        discounts = (
            Discount.objects.create(
                name="Discount 1",
                owner=owner,
                type=DiscountTypeChoices.TYPE_PERCENTAGE,
                value=10,
            ),
            Discount.objects.create(
                name="Discount 2",
                owner=owner,
                type=DiscountTypeChoices.TYPE_PERCENTAGE,
                value=20,
            ),
            Discount.objects.create(
                name="Discount 3",
                owner=owner,
                type=DiscountTypeChoices.TYPE_PERCENTAGE,
                value=30,
            ),
        )

        cls.form_data = {
            "name": "Fourth discount",
            "owner": owner.pk,
            "scope_object_type": resource_ct.pk,
            "scope_object_id": resources[0].pk,
            "type": DiscountTypeChoices.TYPE_PERCENTAGE,
            "value": 10,
            "description": "A new discount",
        }

        cls.csv_data = (
            "name,owner,type,value,description,scope_object",
            "Fourth discount,pi,percentage,10,Fourth discount,storage.storageresource:Storage Resource 1",
            "Fifth discount,pi,percentage,20,Fifth discount,storage.storageresource:Storage Resource 2",
            "Sixth discount,pi,percentage,30,Sixth discount,storage.storageresource:Storage Resource 3",
        )

        cls.csv_update_data = (
            "id,description",
            f"{discounts[0].pk},Fourth discount7",
            f"{discounts[1].pk},Fifth discount8",
            f"{discounts[2].pk},Sixth discount9",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated discount",
        }


class InvoiceLineItemTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = InvoiceLineItem
    validation_excluded_fields = ("source_object",)

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

        cls.form_data = {
            "invoice": invoice.pk,
            "line_type": InvoiceLineTypeChoices.TYPE_CHARGE,
            "source_object": f"{resource_ct.pk}:{resource.pk}",
            "unit": "1.0 TB",
            "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
            "quantity": 1,
            "unit_price_0": "10.00",
            "unit_price_1": "USD",
            "amount_0": "10.00",
            "amount_1": "USD",
            "description": "A new line item",
        }

        cls.bulk_edit_form_data = {
            "description": "Updated line item",
        }
