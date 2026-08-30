# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from django.contrib.contenttypes.models import ContentType

from coldfront.billing.choices import ChargeBasisChoices, DiscountTypeChoices, UnitFormatChoiceSet
from coldfront.billing.forms import (
    DiscountForm,
    FreeAllowanceForm,
    RateForm,
)
from coldfront.billing.models import Rate
from coldfront.registry import get_billing_sources, registry
from coldfront.storage.models import StorageResource
from coldfront.users.models import User


@pytest.mark.django_db
def test_rate_form_scope_type_limited_to_registered_sources():
    expected = {ContentType.objects.get_for_model(s["scope"]).pk for s in get_billing_sources()}
    form = RateForm()
    actual = set(form.fields["scope_object_type"].queryset.values_list("pk", flat=True))
    assert actual == expected


@pytest.mark.django_db
def test_rate_form_no_registered_sources_no_scope_types():
    saved = dict(registry["billing_sources"])
    registry["billing_sources"].clear()
    try:
        form = RateForm()
        assert list(form.fields["scope_object_type"].queryset) == []
    finally:
        registry["billing_sources"].update(saved)


@pytest.mark.django_db
def test_rate_form_edit_keeps_current_scope_type():
    admin = User.objects.create_superuser(username="admin", password="pw")
    resource = StorageResource.objects.create(name="Storage A")
    rate = Rate.objects.create(
        name="Rate A",
        scope_object_type=ContentType.objects.get_for_model(StorageResource),
        scope_object_id=resource.pk,
        unit=10**12,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        amount="10.00",
        charge_basis=ChargeBasisChoices.BASIS_MONTHLY,
    )

    # Simulate the source being unregistered: the edit form must still offer the
    # instance's current scope type so the existing rate remains editable.
    saved = dict(registry["billing_sources"])
    registry["billing_sources"].clear()
    try:
        form = RateForm(instance=rate, user=admin)
        assert list(form.fields["scope_object_type"].queryset.values_list("pk", flat=True)) == [
            rate.scope_object_type_id
        ]
    finally:
        registry["billing_sources"].update(saved)


@pytest.mark.django_db
def test_rate_form_scope_object_id_filtered_by_scope_type():
    admin = User.objects.create_superuser(username="admin", password="pw")
    resource_a = StorageResource.objects.create(name="Storage A")
    resource_b = StorageResource.objects.create(name="Storage B")
    ct = ContentType.objects.get_for_model(StorageResource)

    form = RateForm(initial={"scope_object_type": ct.pk}, user=admin)
    choices = dict(form.fields["scope_object_id"].choices)
    assert set(choices.values()) - {"---------"} == {str(resource_a), str(resource_b)}

    # No scope type selected -> no object choices
    form = RateForm(user=admin)
    assert form.fields["scope_object_id"].choices == [(None, "---------")]


@pytest.mark.django_db
def test_rate_form_scope_is_required():
    admin = User.objects.create_superuser(username="admin", password="pw")
    data = {
        "scope_object_type": "",
        "scope_object_id": "",
        "unit": "1 TB",
        "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
        "amount_0": "10.00",
        "amount_1": "USD",
        "charge_basis": ChargeBasisChoices.BASIS_MONTHLY,
        "description": "A new rate",
    }
    form = RateForm(data=data, user=admin)
    assert not form.is_valid()
    assert "scope_object_type" in form.errors
    assert "scope_object_id" in form.errors


@pytest.mark.django_db
def test_rate_form_saves_scope():
    admin = User.objects.create_superuser(username="admin", password="pw")
    resource = StorageResource.objects.create(name="Storage A")
    ct = ContentType.objects.get_for_model(StorageResource)

    data = {
        "scope_object_type": ct.pk,
        "scope_object_id": resource.pk,
        "name": "Test Rate",
        "unit": "1 TB",
        "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
        "amount_0": "10.00",
        "amount_1": "USD",
        "charge_basis": ChargeBasisChoices.BASIS_MONTHLY,
        "description": "A new rate",
    }
    form = RateForm(data=data, user=admin)
    assert form.is_valid(), form.errors
    rate = form.save()
    assert rate.scope_object == resource


@pytest.mark.django_db
def test_rate_add_view_filters_scope_objects_via_htmx(client):
    admin = User.objects.create_superuser(username="admin", password="pw")
    client.force_login(admin)
    StorageResource.objects.create(name="Storage A")
    StorageResource.objects.create(name="Storage B")
    ct = ContentType.objects.get_for_model(StorageResource)

    # Without a selected scope type, no scope objects are offered
    resp = client.get("/billing/rates/add/", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert "Storage A" not in resp.content.decode()

    # Selecting a scope type filters the scope_object_id options via HTMX
    resp = client.get(f"/billing/rates/add/?scope_object_type={ct.pk}", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Storage A" in body
    assert "Storage B" in body


@pytest.mark.django_db
def test_rate_add_view_warns_when_no_sources(client):
    admin = User.objects.create_superuser(username="admin", password="pw")
    client.force_login(admin)

    saved = dict(registry["billing_sources"])
    registry["billing_sources"].clear()
    try:
        resp = client.get("/billing/rates/add/")
        assert resp.status_code == 200
        assert "Before you can add a Rate" in resp.content.decode()
    finally:
        registry["billing_sources"].update(saved)


@pytest.mark.django_db
def test_rate_add_view_no_warning_when_sources_registered(client):
    admin = User.objects.create_superuser(username="admin", password="pw")
    client.force_login(admin)

    resp = client.get("/billing/rates/add/")
    assert resp.status_code == 200
    assert "Before you can add a Rate" not in resp.content.decode()
    assert "Registered billing sources" not in resp.content.decode()


@pytest.mark.django_db
def test_rate_form_edit_seeds_scope_initial():
    admin = User.objects.create_superuser(username="admin", password="pw")
    resource = StorageResource.objects.create(name="Storage A")
    rate = Rate.objects.create(
        name="Rate B",
        scope_object_type=ContentType.objects.get_for_model(StorageResource),
        scope_object_id=resource.pk,
        unit=10**12,
        unit_format=UnitFormatChoiceSet.UNIT_BYTES,
        amount="10.00",
        charge_basis=ChargeBasisChoices.BASIS_MONTHLY,
    )

    form = RateForm(instance=rate, user=admin)
    assert form["scope_object_type"].value() == rate.scope_object_type_id
    assert form["scope_object_id"].value() == resource.pk


@pytest.mark.django_db
def test_free_allowance_form_scope_is_required():
    admin = User.objects.create_superuser(username="admin", password="pw")
    owner = User.objects.create_user(username="pi")
    data = {
        "owner": owner.pk,
        "scope_object_type": "",
        "scope_object_id": "",
        "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
        "quantity_total": "100",
        "description": "A new allowance",
    }
    form = FreeAllowanceForm(data=data, user=admin)
    assert not form.is_valid()
    assert "scope_object_type" in form.errors
    assert "scope_object_id" in form.errors


@pytest.mark.django_db
def test_free_allowance_form_saves_scope():
    admin = User.objects.create_superuser(username="admin", password="pw")
    owner = User.objects.create_user(username="pi")
    resource = StorageResource.objects.create(name="Storage A")
    ct = ContentType.objects.get_for_model(StorageResource)

    data = {
        "owner": owner.pk,
        "scope_object_type": ct.pk,
        "scope_object_id": resource.pk,
        "name": "Test Allowance",
        "unit_format": UnitFormatChoiceSet.UNIT_BYTES,
        "quantity_total": "100",
        "used": 0,
        "description": "A new allowance",
    }
    form = FreeAllowanceForm(data=data, user=admin)
    assert form.is_valid(), form.errors
    allowance = form.save()
    assert allowance.scope_object == resource


@pytest.mark.django_db
def test_free_allowance_add_view_filters_scope_objects_via_htmx(client):
    admin = User.objects.create_superuser(username="admin", password="pw")
    client.force_login(admin)
    StorageResource.objects.create(name="Storage A")
    StorageResource.objects.create(name="Storage B")
    ct = ContentType.objects.get_for_model(StorageResource)

    resp = client.get("/billing/free-allowances/add/", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert "Storage A" not in resp.content.decode()

    resp = client.get(f"/billing/free-allowances/add/?scope_object_type={ct.pk}", HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Storage A" in body
    assert "Storage B" in body


@pytest.mark.django_db
def test_free_allowance_import_saves_scope():
    owner = User.objects.create_user(username="pi")
    resource = StorageResource.objects.create(name="Storage Resource 4")
    ct = ContentType.objects.get_for_model(StorageResource)

    from coldfront.billing.forms import FreeAllowanceImportForm

    # The CSV import maps scope_object onto the GenericFK fields (latent-bug
    # regression: previously the declared field was never applied to the instance).
    form = FreeAllowanceImportForm(
        data={
            "name": "Fourth allowance",
            "owner": owner.username,
            "unit_format": "bytes",
            "quantity_total": "100",
            "used": 0,
            "description": "Fourth allowance",
            "scope_object": "storage.storageresource:Storage Resource 4",
        }
    )
    assert form.is_valid(), form.errors
    instance = form.save()
    assert instance.scope_object_type_id == ct.pk
    assert instance.scope_object_id == resource.pk


@pytest.mark.django_db
def test_discount_form_accepts_global_discount():
    admin = User.objects.create_superuser(username="admin", password="pw")

    data = {
        "name": "Global discount",
        "owner": "",
        "type": DiscountTypeChoices.TYPE_PERCENTAGE,
        "value": "10",
    }
    form = DiscountForm(data=data, user=admin)
    assert form.is_valid(), form.errors
    discount = form.save()
    assert discount.owner is None
    assert discount.scope_object is None


@pytest.mark.django_db
def test_discount_form_accepts_owner_and_scope():
    admin = User.objects.create_superuser(username="admin", password="pw")
    owner = User.objects.create_user(username="pi")
    resource = StorageResource.objects.create(name="Storage A")
    ct = ContentType.objects.get_for_model(StorageResource)

    data = {
        "name": "Owner resource discount",
        "owner": owner.pk,
        "scope_object_type": ct.pk,
        "scope_object_id": resource.pk,
        "type": DiscountTypeChoices.TYPE_PERCENTAGE,
        "value": "10",
    }
    form = DiscountForm(data=data, user=admin)
    assert form.is_valid(), form.errors
    discount = form.save()
    assert discount.owner == owner
    assert discount.scope_object == resource
