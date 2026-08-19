# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from django.contrib.contenttypes.models import ContentType

from coldfront.billing.choices import (
    DiscountTypeChoices,
    InvoiceLineTypeChoices,
    InvoiceStatusChoices,
    UnitFormatChoiceSet,
)
from coldfront.billing.generation import finalize_invoice, generate_invoice
from coldfront.billing.models import Discount, FreeAllowance, Invoice, Rate
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation, Project
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource
from coldfront.users.models import User

TB = 10**12


def _storage_quota(owner, project, hard_limit_bytes=2 * TB, path="/a"):
    """Build an active StorageQuota billable to ``project``."""
    cluster = StorageCluster.objects.create(name="Cluster")
    resource = StorageResource.objects.create(name="Storage")
    resource.clusters.add(cluster)
    allocation = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_ACTIVE,
        resource_object=resource,
    )
    return StorageQuota.objects.create(
        allocation=allocation, storage=resource, path=path, hard_limit_bytes=hard_limit_bytes
    ), resource


def _rate(resource, *, amount="10.00", unit=TB):
    from django.contrib.contenttypes.models import ContentType

    return Rate.objects.create(
        scope_object_type=ContentType.objects.get_for_model(resource),
        scope_object_id=resource.pk,
        unit=unit,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        amount=amount,
        charge_basis="monthly",
    )


def _invoice(owner, project, *, status=InvoiceStatusChoices.STATUS_DRAFT):
    invoice = Invoice.objects.create(owner=owner, status=status)
    invoice.projects.add(project)
    return invoice


@pytest.mark.django_db
def test_generate_charges_allowance_and_discount():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _rate(resource)
    FreeAllowance.objects.create(
        owner=owner,
        project=project,
        scope_object_type=ContentType.objects.get_for_model(resource),
        scope_object_id=resource.pk,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        quantity_total=1 * TB,
    )
    Discount.objects.create(owner=owner, project=project, type=DiscountTypeChoices.TYPE_PERCENTAGE, value="10")
    invoice = _invoice(owner, project)

    generate_invoice(invoice)

    charges = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE)
    free = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_FREE_ALLOWANCE)
    discount_lines = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_DISCOUNT)

    assert charges.count() == 1
    charge = charges.get()
    assert charge.source_object == quota
    assert charge.quantity == 2 * TB
    assert charge.is_valid
    assert charge.amount.amount == 20.00

    assert free.count() == 1
    assert free.get().amount.amount == -10.00

    assert discount_lines.count() == 1
    assert discount_lines.get().amount.amount == -1.00

    # subtotal 20, allowance -10 -> net 10, discount 10% -> -1, grand total 9
    assert invoice.subtotal.amount == 20.00
    assert invoice.allowance_total.amount == -10.00
    assert invoice.discount_total.amount == -1.00
    assert invoice.grand_total.amount == 9.00


@pytest.mark.django_db
def test_generate_skips_source_without_rate():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _storage_quota(owner, project)
    # no Rate configured for this resource scope
    invoice = _invoice(owner, project)

    generate_invoice(invoice)

    assert invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 0
    assert invoice.grand_total.amount == 0.00


@pytest.mark.django_db
def test_generate_flags_invalid_line_when_quantity_missing():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project, hard_limit_bytes=None)
    _rate(resource)
    invoice = _invoice(owner, project)

    generate_invoice(invoice)

    invalid = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE)
    assert invalid.count() == 1
    line = invalid.get()
    assert not line.is_valid
    assert line.amount is None
    assert "Needs fixing" in line.description


@pytest.mark.django_db
def test_generate_skips_zero_quantity_source():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project, hard_limit_bytes=0)
    _rate(resource)
    invoice = _invoice(owner, project)

    generate_invoice(invoice)

    assert invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 0


@pytest.mark.django_db
def test_finalize_consumes_pool_once_and_drops_invalid_lines():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _rate(resource)
    allowance = FreeAllowance.objects.create(
        owner=owner,
        project=project,
        scope_object_type=ContentType.objects.get_for_model(resource),
        scope_object_id=resource.pk,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        quantity_total=1 * TB,
    )
    invoice = _invoice(owner, project)

    generate_invoice(invoice)
    finalize_invoice(invoice)

    allowance.refresh_from_db()
    assert allowance.used == 1 * TB

    # Re-running finalize does not double-consume the pool
    finalize_invoice(invoice)
    allowance.refresh_from_db()
    assert allowance.used == 1 * TB

    # Invalid lines dropped on finalize
    assert invoice.line_items.filter(is_valid=False).count() == 0


@pytest.mark.django_db
def test_finalize_blocks_invoice_without_valid_charge_lines():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _storage_quota(owner, project)  # no rate -> no charge lines
    invoice = _invoice(owner, project)

    generate_invoice(invoice)

    with pytest.raises(ValueError):
        finalize_invoice(invoice)


@pytest.mark.django_db
def test_generation_period_overlap_guard():
    from django.utils import timezone

    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project)
    _rate(resource)

    # Invoice A bills this source for January 2024 and is invoiced
    invoice_a = _invoice(owner, project)
    invoice_a.start_date = timezone.now().replace(year=2024, month=1, day=1)
    invoice_a.end_date = timezone.now().replace(year=2024, month=1, day=31)
    invoice_a.save()
    generate_invoice(invoice_a)
    assert invoice_a.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 1
    invoice_a.status = InvoiceStatusChoices.STATUS_INVOICED
    invoice_a.save()

    # Invoice B overlaps January 2024 -> source skipped
    invoice_b = _invoice(owner, project)
    invoice_b.start_date = timezone.now().replace(year=2024, month=1, day=15)
    invoice_b.end_date = timezone.now().replace(year=2024, month=2, day=15)
    invoice_b.save()
    generate_invoice(invoice_b)
    assert invoice_b.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 0

    # Invoice C covers a disjoint February 2024 period -> source re-billed
    invoice_c = _invoice(owner, project)
    invoice_c.start_date = timezone.now().replace(year=2024, month=2, day=15)
    invoice_c.end_date = timezone.now().replace(year=2024, month=2, day=28)
    invoice_c.save()
    generate_invoice(invoice_c)
    assert invoice_c.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 1
