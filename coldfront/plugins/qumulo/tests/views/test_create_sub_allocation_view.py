from django.test import TestCase
from unittest.mock import patch, MagicMock

from coldfront.core.allocation.models import Allocation
from coldfront.core.resource.models import Resource
from coldfront.core.allocation.models import (
    AllocationLinkage,
    AllocationAttributeType,
    AllocationAttribute,
)

from coldfront.plugins.qumulo.tests.utils.mock_data import build_models
from coldfront.plugins.qumulo.services.allocation_service import AllocationService
from coldfront.plugins.qumulo.views.create_sub_allocation_view import (
    CreateSubAllocationView,
)

from coldfront.core.allocation.models import (
    AllocationLinkage,
    AllocationAttributeType,
    AllocationAttribute,
)

# TODO why isn't the CreateSubAllocationForm used?
from coldfront.plugins.qumulo.forms import CreateSubAllocationForm


@patch("coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI")
@patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
@patch("coldfront.plugins.qumulo.validators.ActiveDirectoryAPI")
class AllocationViewTests(TestCase):
    def setUp(self):
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        self.client.force_login(self.user)

        self.parent_form_data = {
            "project_pk": self.project.id,
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "CC-1234",
            "billing_exempt": "No",
            "department_number": "Time Travel Services",
            "billing_cycle": "monthly",
            "service_rate": "consumption",
        }

        self.sub_form_data = {
            "project_pk": self.project.id,
            "parent_allocation_name": self.parent_form_data["storage_name"],
            "storage_filesystem_path": "xyz",
            "storage_export_path": "abc",
            "storage_ticket": "ITSD-78910",
            "storage_name": "general_store",
            "storage_quota": 8,
            "protocols": ["nfs"],
            "rw_users": ["test2"],
            "ro_users": ["test3"],
            "cost_center": "CC-3232",
            "billing_exempt": "No",
            "department_number": "Whale-watching",
            "billing_cycle": "monthly",
            "service_rate": "consumption",
        }

    def test_create_sub_allocation(
        self,
        mock_ActiveDirectoryAPI_validator: MagicMock,
        mock_ActiveDirectoryAPI: MagicMock,
        mock_async_task: MagicMock,
    ):
        parent_result = AllocationService.create_new_allocation(
            self.parent_form_data, self.user
        )

        # verifying that a new Allocation object was created
        self.assertEqual(Allocation.objects.count(), 3)
        resource = Resource.objects.get(name="Storage2")
        storage_allocations = Allocation.objects.filter(resources=resource)
        self.assertEqual(len(storage_allocations), 1)

        self.assertEqual(AllocationLinkage.objects.count(), 0)

        # create a sub-allocation
        sub_result = AllocationService.create_new_allocation(
            self.sub_form_data, self.user, parent_allocation=parent_result["allocation"]
        )

        # verifying that a new sub-Allocation object was created
        self.assertEqual(Allocation.objects.count(), 6)
        storage_allocations = Allocation.objects.filter(resources=resource)
        self.assertEqual(len(storage_allocations), 2)

        # assert that an allocationlinkage was created
        self.assertEqual(AllocationLinkage.objects.count(), 1)

        linkage = AllocationLinkage.objects.first()

        self.assertEqual(linkage.parent, parent_result["allocation"])
        self.assertEqual(linkage.children.count(), 1)
        self.assertEqual(linkage.children.first(), sub_result["allocation"])

        storage_name_type = AllocationAttributeType.objects.get(name="storage_name")
        child_storage_name = AllocationAttribute.objects.get(
            allocation=sub_result["allocation"],
            allocation_attribute_type=storage_name_type,
        )

        self.assertEqual(child_storage_name.value, "baz-general_store")
