from django.test import TestCase
from unittest.mock import patch, MagicMock

from coldfront.core.allocation.models import Allocation

from coldfront.plugins.qumulo.tests.utils.mock_data import build_models
from coldfront.plugins.qumulo.views.allocation_view import AllocationView


@patch("coldfront.plugins.qumulo.views.allocation_view.AclAllocations")
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
            "department_number": "Time Travel Services",
            "service_rate": "consumption",
        }

    def test_create_new_allocation_create_allocation(
        self,
        mock_AclAllocations: MagicMock,
        mock_ActiveDirectoryAPI: MagicMock,
    ):
        AllocationView.create_new_allocation(self.form_data, self.user)

        # verifying that a new Allocation object was created
        self.assertEqual(Allocation.objects.count(), 3)

        # Accessing the created Allocation object
        allocation = Allocation.objects.first()

        # verifying that Allocation attributes were set correctly
        self.assertEqual(allocation.project, self.project)

    def test_new_allocation_status_is_pending(
        self,
        mock_AclAllocations: MagicMock,
        mock_ActiveDirectoryAPI: MagicMock,
    ):
        AllocationView.create_new_allocation(self.form_data, self.user)
        allocation = Allocation.objects.first()
        self.assertEqual(allocation.status.name, "Pending")
