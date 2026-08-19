# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation, Project
from coldfront.registry import get_billing_source, register_billing_source, registry
from coldfront.slurm.models import SlurmAccount, SlurmAssociation, SlurmCluster, SlurmQOS
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource
from coldfront.users.models import User


@pytest.mark.django_db
def test_register_billing_source_rejects_invalid_scope():
    with pytest.raises(ValueError):
        register_billing_source("not-a-model", StorageQuota)
    with pytest.raises(ValueError):
        register_billing_source(StorageResource, "not-a-model")


@pytest.mark.django_db
def test_register_billing_source_rejects_non_callable_callbacks():
    with pytest.raises(ValueError):
        register_billing_source(StorageResource, StorageQuota, get_quantity=7)


@pytest.mark.django_db
def test_register_billing_source_last_wins():
    key = "slurm.slurmaccount"
    original = registry["billing_sources"].get(key)
    try:
        register_billing_source(
            SlurmCluster,
            SlurmAccount,
            get_quantity=lambda source: 7,
        )
        register_billing_source(
            SlurmCluster,
            SlurmAccount,
            get_quantity=lambda source: 9,
        )
        entry = get_billing_source(SlurmAccount)
        assert entry["scope"] is SlurmCluster
        assert entry["get_quantity"](None) == 9
    finally:
        if original is None:
            registry["billing_sources"].pop(key, None)
        else:
            registry["billing_sources"][key] = original


@pytest.mark.django_db
def test_get_billing_source_unregistered():
    assert get_billing_source("ras.project") is None
    assert get_billing_source(Project) is None


@pytest.mark.django_db
def test_builtin_sources_registered():
    storage = get_billing_source("storage.storagequota")
    assert storage["model"] is StorageQuota
    assert storage["scope"] is StorageResource
    assert storage["get_rate_scope"] is not None
    assert storage["get_quantity"] is not None

    account = get_billing_source("slurm.slurmaccount")
    assert account["model"] is SlurmAccount
    assert account["scope"] is SlurmCluster

    qos = get_billing_source("slurm.slurmqos")
    assert qos["model"] is SlurmQOS
    assert qos["scope"] is SlurmQOS


@pytest.mark.django_db
def test_builtin_rate_scope_and_quantity():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    cluster = StorageCluster.objects.create(name="Cluster")
    resource = StorageResource.objects.create(name="Storage")
    resource.clusters.add(cluster)
    allocation = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_ACTIVE,
        resource_object=resource,
    )
    quota = StorageQuota.objects.create(allocation=allocation, storage=resource, path="/active")

    entry = get_billing_source("storage.storagequota")
    assert entry["get_rate_scope"](quota) is resource
    assert entry["get_quantity"](quota) == quota.hard_limit_bytes

    slurm = SlurmCluster.objects.create(name="Cluster")
    account = SlurmAccount.objects.create(name="acct", cluster=slurm)
    account_entry = get_billing_source("slurm.slurmaccount")
    assert account_entry["get_rate_scope"](account) is slurm
    assert account_entry["get_quantity"](account) == account.service_units

    qos = SlurmQOS.objects.create(name="QOS A")
    qos_entry = get_billing_source("slurm.slurmqos")
    assert qos_entry["get_rate_scope"](qos) is qos
    assert qos_entry["get_quantity"](qos) == 1


@pytest.mark.django_db
def test_storage_quota_billable_requires_active_allocation():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    cluster = StorageCluster.objects.create(name="Cluster")
    resource = StorageResource.objects.create(name="Storage")
    resource.clusters.add(cluster)

    active = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_ACTIVE,
        resource_object=resource,
    )
    expired = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_EXPIRED,
        resource_object=resource,
    )

    quota_active = StorageQuota.objects.create(allocation=active, storage=resource, path="/active")
    StorageQuota.objects.create(allocation=expired, storage=resource, path="/expired")

    billable = get_billing_source("storage.storagequota")["get_billable"](project=project)
    assert list(billable) == [quota_active]


@pytest.mark.django_db
def test_slurm_account_billable_requires_active_allocation():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    cluster = SlurmCluster.objects.create(name="Cluster")
    account = SlurmAccount.objects.create(name="acct", cluster=cluster)

    active = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_ACTIVE,
        resource_object=cluster,
    )
    expired = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_EXPIRED,
        resource_object=cluster,
    )

    SlurmAssociation.objects.create(allocation=active, slurm_account=account)
    SlurmAssociation.objects.create(allocation=expired, slurm_account=account)

    billable = get_billing_source("slurm.slurmaccount")["get_billable"](project=project)
    assert list(billable) == [account]


@pytest.mark.django_db
def test_slurm_qos_billable_requires_active_allocation():
    owner = User.objects.create_user(username="pi")
    project = Project.objects.create(name="Project 1", owner=owner)
    cluster = SlurmCluster.objects.create(name="Cluster")

    account_active = SlurmAccount.objects.create(name="acct", cluster=cluster)
    account_inactive = SlurmAccount.objects.create(name="acct2", cluster=cluster)

    active = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_ACTIVE,
        resource_object=cluster,
    )
    expired = Allocation.objects.create(
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_EXPIRED,
        resource_object=cluster,
    )

    SlurmAssociation.objects.create(allocation=active, slurm_account=account_active)
    SlurmAssociation.objects.create(allocation=expired, slurm_account=account_inactive)

    qos_active = SlurmQOS.objects.create(name="QOS A")
    qos_inactive = SlurmQOS.objects.create(name="QOS B")
    account_active.qos_add.add(qos_active)
    account_inactive.qos_add.add(qos_inactive)

    billable = get_billing_source("slurm.slurmqos")["get_billable"](project=project)
    assert list(billable) == [qos_active]
