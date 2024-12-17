import json
from icecream import ic
from django.test import TestCase

from unittest import mock

from coldfront.core.allocation.models import Allocation, AllocationAttribute
from coldfront.core.project.models import Project, ProjectAttribute
from coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront import (
    MigrateToColdfront,
)

from coldfront.plugins.qumulo.tests.fixtures import create_allocation_assets


class TestMigrateToColdfront(TestCase):

    def setUp(self) -> None:
        self.migrate = MigrateToColdfront()
        create_allocation_assets()

    @mock.patch(
        "coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront.ItsmClient"
    )
    @mock.patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
    def test_migrate_to_coldfront_by_fileset_name(
        self,
        mock_async_task: mock.MagicMock,
        mock_itsm_client: mock.MagicMock,
    ) -> None:
        with open(
            "coldfront/plugins/qumulo/static/migration_mappings/mock_itsm_response_body_service_provision_found.json",
            "r",
        ) as file:
            mock_response = json.load(file)["data"]
            itsm_client = mock.MagicMock()
            itsm_client.get_fs1_allocation_by_fileset_name.return_value = mock_response
            mock_itsm_client.return_value = itsm_client

        name = "mocker"
        result = self.migrate.by_fileset_name(f"{name}_active")
        self.assertDictEqual(
            result, {"allocation_id": 1, "pi_user_id": 1, "project_id": 1}
        )
        allocation = Allocation.objects.get(id=result["allocation_id"])
        project = Project.objects.get(id=result["project_id"])
        allocation_attributes = AllocationAttribute.objects.filter(
            allocation=result["allocation_id"]
        )
        project_attributes = ProjectAttribute.objects.filter(
            project=result["project_id"]
        )
        self.assertEqual(len(allocation_attributes), 21)
        self.assertEqual(len(project_attributes), 3)
        self.assertEqual(allocation.id, result["allocation_id"])
        self.assertEqual(allocation.project, project)
        self.assertEqual(allocation.project.title, name)
