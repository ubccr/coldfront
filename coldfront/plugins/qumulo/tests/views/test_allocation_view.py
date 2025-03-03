from django.test import TestCase
from unittest.mock import patch, MagicMock

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttributeType,
    AllocationAttribute,
)

from coldfront.plugins.qumulo.tests.utils.mock_data import build_models
from coldfront.plugins.qumulo.services.allocation_service import AllocationService


@patch("coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI")
@patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
@patch("coldfront.plugins.qumulo.validators.ActiveDirectoryAPI")
class AllocationViewTests(TestCase):
    def setUp(self):
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        self.client.force_login(self.user)

        self.form_data = {
            "project_pk": self.project.id,
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "Uncle Pennybags",
            "billing_exempt": "No",
            "department_number": "Time Travel Services",
            "billing_cycle": "monthly",
            "service_rate": "consumption",
        }

    def test_create_new_allocation_create_allocation(
        self,
        mock_ActiveDirectoryValidator: MagicMock,
        mock_async_task: MagicMock,
        mock_ActiveDirectoryAPI: MagicMock,
    ):
        AllocationService.create_new_allocation(self.form_data, self.user)

        # verifying that a new Allocation object was created
        self.assertEqual(Allocation.objects.count(), 3)

        # Accessing the created Allocation object
        allocation = Allocation.objects.first()

        # verifying that Allocation attributes were set correctly
        self.assertEqual(allocation.project, self.project)

        # verify that the allocation has the right default attributes
        allocation_defaults = {
            "secure": "No",
            "audit": "No",
            "billing_exempt": "No",
            "subsidized": "No",
        }
        for attr, value in allocation_defaults.items():
            attribute_type = AllocationAttributeType.objects.get(name=attr)
            num_attrs = len(
                AllocationAttribute.objects.filter(
                    allocation_attribute_type=attribute_type,
                    allocation=allocation,
                )
            )
            self.assertEqual(num_attrs, 1)

    def test_new_allocation_status_is_pending(
        self,
        mock_ActiveDirectoryValidator: MagicMock,
        mock_async_task: MagicMock,
        mock_ActiveDirectoryAPI: MagicMock,
    ):
        AllocationService.create_new_allocation(self.form_data, self.user)
        allocation = Allocation.objects.first()
        self.assertEqual(allocation.status.name, "Pending")
