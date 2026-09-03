# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

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
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAccountUsage,
    SlurmAssociation,
    SlurmCluster,
)
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource
from coldfront.users.models import User

TB = 10**12


def _storage_quota(owner, project, hard_limit_bytes=2 * TB, path="/a"):
    """Build an active StorageQuota billable to ``project``."""
    # Names are derived from path so tests that build several quotas in one
    # database don't hit the unique-name constraints on cluster/resource.
    cluster = StorageCluster.objects.create(name=f"Cluster {path}")
    resource = StorageResource.objects.create(name=f"Storage {path}")
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
    return Rate.objects.create(
        name=f"Test Rate {resource.pk}",
        scope_object_type=ContentType.objects.get_for_model(resource),
        scope_object_id=resource.pk,
        unit=unit,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        amount=amount,
        charge_basis="monthly",
    )


def _invoice(owner, *, status=InvoiceStatusChoices.STATUS_DRAFT):
    return Invoice.objects.create(owner=owner, status=status)


def _slurm_account(
    owner,
    project,
    name,
    *,
    consumed,
    day="2024-01-10",
    service_units=10000,
    cluster=None,
):
    """Build a SlurmAccount billable to ``owner`` with a usage row for ``day``."""
    if cluster is None:
        cluster = SlurmCluster.objects.create(name=f"Cluster {name}")
    account = SlurmAccount.objects.create(name=name, cluster=cluster, service_units=service_units)
    allocation = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_ACTIVE,
        resource_object=cluster,
    )
    SlurmAssociation.objects.create(allocation=allocation, slurm_account=account)
    SlurmAccountUsage.objects.create(
        cluster=cluster,
        account=account,
        period_start=date.fromisoformat(day),
        period_end=date.fromisoformat(day),
        billing_units_consumed=consumed,
        billing_units_completed=consumed,
    )
    return account, cluster


def _slurm_rate(cluster, *, amount="10.00", unit=1):
    return Rate.objects.create(
        name=f"Test Rate {cluster.pk}",
        scope_object_type=ContentType.objects.get_for_model(cluster),
        scope_object_id=cluster.pk,
        unit=unit,
        unit_format=UnitFormatChoiceSet.UNIT_SERVICE_UNITS,
        amount=amount,
        charge_basis="monthly",
    )


def _scoped_discount(name, resource, *, owner=None, value="10", type=DiscountTypeChoices.TYPE_PERCENTAGE):
    return Discount.objects.create(
        name=name,
        owner=owner,
        scope_object_type=ContentType.objects.get_for_model(resource),
        scope_object_id=resource.pk,
        type=type,
        value=value,
    )


@pytest.mark.django_db
def test_generate_charges_allowance_and_discount():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _rate(resource)
    FreeAllowance.objects.create(
        name="Test Allowance",
        owner=owner,
        scope_object_type=ContentType.objects.get_for_model(resource),
        scope_object_id=resource.pk,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        quantity_total=1 * TB,
    )
    Discount.objects.create(
        name="Test Discount",
        owner=owner,
        type=DiscountTypeChoices.TYPE_PERCENTAGE,
        value="10",
    )
    invoice = _invoice(owner)

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
def test_generate_applies_global_discount_to_any_owner():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _rate(resource)
    # Global discount: owner=None, scope=None
    Discount.objects.create(
        name="Global Discount",
        owner=None,
        type=DiscountTypeChoices.TYPE_PERCENTAGE,
        value="10",
    )
    invoice = _invoice(owner)

    generate_invoice(invoice)

    discount_lines = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_DISCOUNT)
    assert discount_lines.count() == 1
    # charge 20, net 20, global 10% -> -2.00
    assert discount_lines.get().amount.amount == -2.00
    assert discount_lines.get().source_object_id == Discount.objects.get(name="Global Discount").pk
    assert invoice.discount_total.amount == -2.00


@pytest.mark.django_db
def test_generate_global_discount_is_fallback_after_owner_specific():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _rate(resource)
    owner_discount = Discount.objects.create(
        name="Owner Discount",
        owner=owner,
        type=DiscountTypeChoices.TYPE_PERCENTAGE,
        value="20",
    )
    Discount.objects.create(
        name="Global Discount",
        owner=None,
        type=DiscountTypeChoices.TYPE_PERCENTAGE,
        value="10",
    )
    invoice = _invoice(owner)

    generate_invoice(invoice)

    discount_lines = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_DISCOUNT)
    assert discount_lines.count() == 1
    # owner-specific 20% wins over global 10% -> -4.00 on net 20
    assert discount_lines.get().amount.amount == -4.00
    assert discount_lines.get().source_object_id == owner_discount.pk


@pytest.mark.django_db
def test_generate_applies_resource_discount_to_that_resource_only():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _, resource_b = _storage_quota(owner, project, hard_limit_bytes=1 * TB, path="/b")
    _rate(resource)
    _rate(resource_b, amount="20.00")
    _scoped_discount("Resource Discount", resource, value="50")
    invoice = _invoice(owner)

    generate_invoice(invoice)

    discount_lines = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_DISCOUNT)
    assert discount_lines.count() == 1
    # only resource's net (20.00) is discounted 50% -> -10.00; resource_b untouched
    assert discount_lines.get().amount.amount == -10.00
    assert invoice.discount_total.amount == -10.00
    assert invoice.grand_total.amount == 30.00  # resource_b 20 + resource 20 - 10


@pytest.mark.django_db
def test_generate_owner_resource_discount_beats_resource_global():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _rate(resource)
    _scoped_discount("Owner Resource Discount", resource, owner=owner, value="20")
    _scoped_discount("Resource Global Discount", resource, value="10")
    invoice = _invoice(owner)

    generate_invoice(invoice)

    discount_lines = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_DISCOUNT)
    assert discount_lines.count() == 1
    # owner+resource 20% wins over resource-only 10% -> -4.00 on net 20
    assert discount_lines.get().amount.amount == -4.00
    assert discount_lines.get().source_object_id == Discount.objects.get(name="Owner Resource Discount").pk


@pytest.mark.django_db
def test_generate_global_no_cost_discount_zeroes_invoice():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _rate(resource)
    Discount.objects.create(
        name="No Cost",
        owner=None,
        type=DiscountTypeChoices.TYPE_NO_COST,
    )
    invoice = _invoice(owner)

    generate_invoice(invoice)

    # charges still visible; no-cost discount zeroes the grand total
    assert invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 1
    assert invoice.subtotal.amount == 20.00
    assert invoice.discount_total.amount == -20.00
    assert invoice.grand_total.amount == 0.00


@pytest.mark.django_db
def test_generate_skips_source_without_rate():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _storage_quota(owner, project)
    # no Rate configured for this resource scope
    invoice = _invoice(owner)

    generate_invoice(invoice)

    assert invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 0
    assert invoice.grand_total.amount == 0.00


@pytest.mark.django_db
def test_generate_flags_invalid_line_when_quantity_missing():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project, hard_limit_bytes=None)
    _rate(resource)
    invoice = _invoice(owner)

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
    invoice = _invoice(owner)

    generate_invoice(invoice)

    assert invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 0


@pytest.mark.django_db
def test_finalize_consumes_pool_once_and_drops_invalid_lines():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project, hard_limit_bytes=2 * TB)
    _rate(resource)
    allowance = FreeAllowance.objects.create(
        name="Test Allowance",
        owner=owner,
        scope_object_type=ContentType.objects.get_for_model(resource),
        scope_object_id=resource.pk,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        quantity_total=1 * TB,
    )
    invoice = _invoice(owner)

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
    invoice = _invoice(owner)

    generate_invoice(invoice)

    with pytest.raises(ValueError):
        finalize_invoice(invoice)


@pytest.mark.django_db
def test_generation_period_overlap_guard():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    quota, resource = _storage_quota(owner, project)
    _rate(resource)

    # Invoice A bills this source for January 2024 and is invoiced
    invoice_a = _invoice(owner)
    invoice_a.start_date = timezone.now().replace(year=2024, month=1, day=1)
    invoice_a.end_date = timezone.now().replace(year=2024, month=1, day=31)
    invoice_a.save()
    generate_invoice(invoice_a)
    assert invoice_a.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 1
    invoice_a.status = InvoiceStatusChoices.STATUS_INVOICED
    invoice_a.save()

    # Invoice B overlaps January 2024 -> source skipped
    invoice_b = _invoice(owner)
    invoice_b.start_date = timezone.now().replace(year=2024, month=1, day=15)
    invoice_b.end_date = timezone.now().replace(year=2024, month=2, day=15)
    invoice_b.save()
    generate_invoice(invoice_b)
    assert invoice_b.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 0

    # Invoice C covers a disjoint February 2024 period -> source re-billed
    invoice_c = _invoice(owner)
    invoice_c.start_date = timezone.now().replace(year=2024, month=2, day=15)
    invoice_c.end_date = timezone.now().replace(year=2024, month=2, day=28)
    invoice_c.save()
    generate_invoice(invoice_c)
    assert invoice_c.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 1


# ======================================================================
# Slurm usage-based billing
# ======================================================================


@pytest.mark.django_db
def test_generate_slurm_usage_based_charge():
    """An invoice bills consumed SU in its period, not the grant."""
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    account, cluster = _slurm_account(owner, project, "acct-a", consumed=10.0)

    invoice = _invoice(owner)
    invoice.start_date = timezone.now().replace(year=2024, month=1, day=1)
    invoice.end_date = timezone.now().replace(year=2024, month=1, day=31)
    invoice.save()
    _slurm_rate(cluster)

    generate_invoice(invoice)

    charges = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE)
    assert charges.count() == 1
    line = charges.first()
    assert line.quantity == 10  # consumed SU, not grant (10000)
    assert line.amount.amount == Decimal("100.00")  # 10 SU x 10.00
    assert line.unit_format == UnitFormatChoiceSet.UNIT_SERVICE_UNITS


@pytest.mark.django_db
def test_generate_slurm_skips_zero_usage():
    """No synced usage in the invoice period -> no charge (usage-based default)."""
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    # usage row outside the invoice period
    account, cluster = _slurm_account(owner, project, "acct-a", consumed=10.0, day="2023-01-10")

    invoice = _invoice(owner)
    invoice.start_date = timezone.now().replace(year=2024, month=1, day=1)
    invoice.end_date = timezone.now().replace(year=2024, month=1, day=31)
    invoice.save()
    _slurm_rate(cluster)

    generate_invoice(invoice)
    assert invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 0


@pytest.mark.django_db
def test_generate_slurm_open_period_sums_all_usage():
    """An open invoice (null dates) sums all usage rows for the account."""
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    account, cluster = _slurm_account(owner, project, "acct-a", consumed=10.0, day="2024-01-10")
    SlurmAccountUsage.objects.create(
        cluster=cluster,
        account=account,
        period_start=date(2024, 2, 15),
        period_end=date(2024, 2, 15),
        billing_units_consumed=5.0,
        billing_units_completed=5.0,
    )

    invoice = _invoice(owner)
    _slurm_rate(cluster)

    generate_invoice(invoice)
    charges = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE)
    assert charges.count() == 1
    assert charges.first().quantity == 15  # 10 + 5


@pytest.mark.django_db
def test_generate_slurm_cluster_allowance_covers_all_accounts():
    """A cluster-scoped free allowance draws across all of the owner's accounts."""
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    # Two accounts on the same cluster
    cluster = SlurmCluster.objects.create(name="Cluster HPC")
    acct_a, _ = _slurm_account(owner, project, "acct-a", consumed=8.0, cluster=cluster)
    acct_b, _ = _slurm_account(owner, project, "acct-b", consumed=6.0, cluster=cluster)
    _slurm_rate(cluster)
    FreeAllowance.objects.create(
        name="HPC Free",
        owner=owner,
        scope_object_type=ContentType.objects.get_for_model(cluster),
        scope_object_id=cluster.pk,
        unit_format=UnitFormatChoiceSet.UNIT_SERVICE_UNITS,
        quantity_total=10,
    )

    invoice = _invoice(owner)
    invoice.start_date = timezone.now().replace(year=2024, month=1, day=1)
    invoice.end_date = timezone.now().replace(year=2024, month=1, day=31)
    invoice.save()

    generate_invoice(invoice)

    free = invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_FREE_ALLOWANCE)
    # allowance covers 10 SU across the two accounts (8 + 6 = 14 -> 10 covered)
    assert sum((line.quantity or 0) for line in free) == 10
