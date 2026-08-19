# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from django.contrib.auth.models import Permission

from coldfront.billing.choices import InvoiceLineTypeChoices, InvoiceStatusChoices, UnitFormatChoiceSet
from coldfront.billing.flows import InvoiceStatusFlow, get_permitted_transition_actions
from coldfront.billing.models import Invoice, Rate
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation, Project
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource
from coldfront.users.models import User


def _invoice_permission(action):
    return Permission.objects.get(codename=f"{action}_invoice", content_type__app_label="billing")


TB = 10**12


def _storage_quota(owner, project):
    cluster = StorageCluster.objects.create(name="Cluster")
    resource = StorageResource.objects.create(name="Storage")
    resource.clusters.add(cluster)
    allocation = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_ACTIVE,
        resource_object=resource,
    )
    quota = StorageQuota.objects.create(allocation=allocation, storage=resource, path="/a", hard_limit_bytes=2 * TB)
    from django.contrib.contenttypes.models import ContentType

    Rate.objects.create(
        scope_object_type=ContentType.objects.get_for_model(resource),
        scope_object_id=resource.pk,
        unit=TB,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        amount="10.00",
        charge_basis="monthly",
    )
    return quota, resource


def _invoice(owner, project):
    invoice = Invoice.objects.create(owner=owner, status=InvoiceStatusChoices.STATUS_DRAFT)
    invoice.projects.add(project)
    return invoice


@pytest.mark.django_db
def test_invoice_status_flow():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _storage_quota(owner, project)
    invoice = _invoice(owner, project)

    flow = InvoiceStatusFlow(invoice)

    # generate is a draft -> draft no-op that rebuilds lines
    flow.generate()
    assert invoice.status == InvoiceStatusChoices.STATUS_DRAFT
    assert invoice.line_items.filter(line_type=InvoiceLineTypeChoices.TYPE_CHARGE).count() == 1

    flow.finalize()
    assert invoice.status == InvoiceStatusChoices.STATUS_INVOICED

    flow.pay()
    assert invoice.status == InvoiceStatusChoices.STATUS_PAID


@pytest.mark.django_db
def test_void_from_draft():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _storage_quota(owner, project)
    invoice = _invoice(owner, project)

    flow = InvoiceStatusFlow(invoice)
    flow.generate()
    flow.void()
    assert invoice.status == InvoiceStatusChoices.STATUS_VOID


@pytest.mark.django_db
def test_no_permissions_returns_no_actions():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _storage_quota(owner, project)
    invoice = _invoice(owner, project)

    # Without billing ObjectPermissions the user sees no transition actions
    assert get_permitted_transition_actions(invoice, owner) == []


@pytest.mark.django_db
def test_action_mapping_per_state():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    _storage_quota(owner, project)
    invoice = _invoice(owner, project)

    outgoing = InvoiceStatusFlow.status.get_outgoing_transitions(invoice.status)
    actions = InvoiceStatusFlow.get_actions([t.slug for t in outgoing])
    assert sorted(a.name for a in actions) == ["generate", "invoice", "void"]

    # Once invoiced, pay becomes available instead of generate/finalize
    invoice.status = InvoiceStatusChoices.STATUS_INVOICED
    invoice.save()
    outgoing = InvoiceStatusFlow.status.get_outgoing_transitions(invoice.status)
    actions = InvoiceStatusFlow.get_actions([t.slug for t in outgoing])
    assert sorted(a.name for a in actions) == ["pay", "void"]
