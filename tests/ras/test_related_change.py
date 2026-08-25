# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from rest_framework import serializers

from coldfront.ras.choices import AllocationChangeRequestStatusChoices
from coldfront.ras.flows.change_requests import AllocationChangeRequestFlow
from coldfront.ras.models import Allocation, AllocationChangeRequest, Project
from coldfront.slurm.models import SlurmAccount, SlurmAssociation, SlurmCluster
from coldfront.users.models import User


@pytest.mark.django_db
def test_related_service_units_change():
    user = User.objects.create(username="su_user")
    project = Project.objects.create(name="SU Project", owner=user)
    cluster = SlurmCluster.objects.create(name="SU Cluster")
    account = SlurmAccount.objects.create(name="su-acct", cluster=cluster, service_units=10000)

    ct = ContentType.objects.get_for_model(SlurmCluster)
    allocation = Allocation.objects.create(
        justification="need su",
        project=project,
        owner=user,
        resource_object_type=ct,
        resource_object_id=cluster.pk,
    )
    SlurmAssociation.objects.create(allocation=allocation, slurm_account=account)

    assert account.service_units == 10000

    cr = AllocationChangeRequest.objects.create(
        allocation=allocation,
        requested_by=user,
        slug="cr-su-1",
        extension_changes={"slurm.slurmassociation.slurm_account": {"service_units": 20000}},
    )
    flow = AllocationChangeRequestFlow(cr)
    flow.approve()
    flow.apply()

    assert cr.status == AllocationChangeRequestStatusChoices.STATUS_APPLIED
    account.refresh_from_db()
    assert account.service_units == 20000

    # Snapshot captured under the related key
    assert cr.snapshot_extension_values["slurm.slurmassociation.slurm_account"]["service_units"] == 10000


@pytest.mark.django_db
def test_changeable_fields_only_on_change():
    from coldfront.slurm.models import SlurmAssociation as SA

    fields = SA.fields_for_change()
    assert "$related:slurm_account.service_units" in fields
    # requestable must NOT contain the marker
    assert "$related:slurm_account.service_units" not in SA.requestable_fields()
    assert "$related:slurm_account.service_units" in SA.changeable_fields()


@pytest.mark.django_db
def test_change_request_form_builds_related_field():
    from coldfront.ras.forms.change_requests import AllocationChangeRequestForm

    user = User.objects.create(username="su_form_user")
    project = Project.objects.create(name="SU Form Project", owner=user)
    cluster = SlurmCluster.objects.create(name="SU Form Cluster")
    account = SlurmAccount.objects.create(name="su-form-acct", cluster=cluster, service_units=10000)

    ct = ContentType.objects.get_for_model(SlurmCluster)
    allocation = Allocation.objects.create(
        justification="need su",
        project=project,
        owner=user,
        resource_object_type=ct,
        resource_object_id=cluster.pk,
    )
    SlurmAssociation.objects.create(allocation=allocation, slurm_account=account)

    # Use a NEW (unsaved) form so clean() skips the "at least one change"
    # check (which runs before _post_clean populates extension_changes).
    form = AllocationChangeRequestForm(
        user=user,
        data={"allocation": allocation.pk, "justification": "more su", "rel_slurmaccount_service_units": 20000},
    )
    # The related-object field is built in change mode and prefilled from the account
    assert "rel_slurmaccount_service_units" in form.fields
    assert form.fields["rel_slurmaccount_service_units"].initial == 10000
    assert form.is_valid(), form.errors
    collected = form._collect_extension_data()
    assert collected["slurm.slurmassociation.slurm_account"]["service_units"] == 20000


@pytest.mark.django_db
def test_serializer_accepts_related_key():
    from coldfront.ras.api.serializers.change_requests import AllocationChangeRequestSerializer

    user = User.objects.create(username="su_api_user")
    project = Project.objects.create(name="SU API Project", owner=user)
    cluster = SlurmCluster.objects.create(name="SU API Cluster")
    account = SlurmAccount.objects.create(name="su-api-acct", cluster=cluster, service_units=10000)

    ct = ContentType.objects.get_for_model(SlurmCluster)
    allocation = Allocation.objects.create(
        justification="need su",
        project=project,
        owner=user,
        resource_object_type=ct,
        resource_object_id=cluster.pk,
    )
    SlurmAssociation.objects.create(allocation=allocation, slurm_account=account)

    serializer = AllocationChangeRequestSerializer()
    attrs = {
        "allocation": allocation,
        "extension_changes": {"slurm.slurmassociation.slurm_account": {"service_units": 20000}},
    }
    validated = serializer.validate(attrs)
    assert "slurm.slurmassociation.slurm_account" in validated["extension_changes"]


@pytest.mark.django_db
def test_change_view_diff_handles_related_key():
    from coldfront.ras.views.change_requests import AllocationChangeRequestView

    user = User.objects.create(username="su_view_user")
    project = Project.objects.create(name="SU View Project", owner=user)
    cluster = SlurmCluster.objects.create(name="SU View Cluster")
    account = SlurmAccount.objects.create(name="su-view-acct", cluster=cluster, service_units=10000)

    ct = ContentType.objects.get_for_model(SlurmCluster)
    allocation = Allocation.objects.create(
        justification="need su",
        project=project,
        owner=user,
        resource_object_type=ct,
        resource_object_id=cluster.pk,
    )
    SlurmAssociation.objects.create(allocation=allocation, slurm_account=account)

    cr = AllocationChangeRequest.objects.create(
        allocation=allocation,
        requested_by=user,
        slug="cr-view-1",
        extension_changes={"slurm.slurmassociation.slurm_account": {"service_units": 20000}},
    )
    view = AllocationChangeRequestView()
    request = RequestFactory().get("/")
    request.user = user
    ctx = view.get_extra_context(request=request, instance=cr)
    assert "slurm.slurmassociation.slurm_account.service_units" in ctx["post_change_data"]
    assert ctx["post_change_data"]["slurm.slurmassociation.slurm_account.service_units"] == 20000
    assert ctx["pre_change_data"]["slurm.slurmassociation.slurm_account.service_units"] == 10000


@pytest.mark.django_db
def test_change_request_form_disables_related_field_when_target_unset():
    from coldfront.ras.forms.change_requests import AllocationChangeRequestForm

    user = User.objects.create(username="su_form_none_user")
    project = Project.objects.create(name="SU Form None Project", owner=user)
    cluster = SlurmCluster.objects.create(name="SU Form None Cluster")

    ct = ContentType.objects.get_for_model(SlurmCluster)
    allocation = Allocation.objects.create(
        justification="need su",
        project=project,
        owner=user,
        resource_object_type=ct,
        resource_object_id=cluster.pk,
    )
    # Association exists but slurm_account is NOT set
    SlurmAssociation.objects.create(allocation=allocation)

    form = AllocationChangeRequestForm(
        user=user,
        data={"allocation": allocation.pk, "justification": "more su", "rel_slurmaccount_service_units": 20000},
    )
    assert "rel_slurmaccount_service_units" in form.fields
    field = form.fields["rel_slurmaccount_service_units"]
    assert field.disabled is True
    assert field.help_text
    # Disabled field value is not collected into extension_changes
    assert form.is_valid(), form.errors
    assert form._collect_extension_data() == {}


@pytest.mark.django_db
def test_serializer_rejects_related_key_when_target_unset():
    from coldfront.ras.api.serializers.change_requests import AllocationChangeRequestSerializer

    user = User.objects.create(username="su_api_none_user")
    project = Project.objects.create(name="SU API None Project", owner=user)
    cluster = SlurmCluster.objects.create(name="SU API None Cluster")

    ct = ContentType.objects.get_for_model(SlurmCluster)
    allocation = Allocation.objects.create(
        justification="need su",
        project=project,
        owner=user,
        resource_object_type=ct,
        resource_object_id=cluster.pk,
    )
    SlurmAssociation.objects.create(allocation=allocation)

    serializer = AllocationChangeRequestSerializer()
    attrs = {
        "allocation": allocation,
        "extension_changes": {"slurm.slurmassociation.slurm_account": {"service_units": 20000}},
    }
    with pytest.raises(serializers.ValidationError):
        serializer.validate(attrs)


@pytest.mark.django_db
def test_apply_aborts_when_related_target_unset():
    from coldfront.exceptions import AbortRequest

    user = User.objects.create(username="su_apply_none_user")
    project = Project.objects.create(name="SU Apply None Project", owner=user)
    cluster = SlurmCluster.objects.create(name="SU Apply None Cluster")

    ct = ContentType.objects.get_for_model(SlurmCluster)
    allocation = Allocation.objects.create(
        justification="need su",
        project=project,
        owner=user,
        resource_object_type=ct,
        resource_object_id=cluster.pk,
    )
    SlurmAssociation.objects.create(allocation=allocation)

    cr = AllocationChangeRequest.objects.create(
        allocation=allocation,
        requested_by=user,
        slug="cr-apply-none",
        extension_changes={"slurm.slurmassociation.slurm_account": {"service_units": 20000}},
    )
    flow = AllocationChangeRequestFlow(cr)
    flow.approve()
    with pytest.raises(AbortRequest):
        flow.apply()
    # Apply was aborted — status stays approved, not marked applied
    assert cr.status == AllocationChangeRequestStatusChoices.STATUS_APPROVED
