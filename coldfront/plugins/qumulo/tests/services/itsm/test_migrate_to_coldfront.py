import os
import json
from django.test import TestCase

from unittest import mock

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
)
from coldfront.core.project.models import Project, ProjectAttribute
from coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront import (
    MigrateToColdfront,
)

from coldfront.plugins.qumulo.tests.fixtures import create_allocation_assets

STORAGE2_PATH = os.environ.get("STORAGE2_PATH")


class TestMigrateToColdfront(TestCase):

    def setUp(self) -> None:
        self.migrate = MigrateToColdfront()
        create_allocation_assets()
        self.expected_allocation_attributes = [
            ("storage_name", "mocker"),
            ("storage_quota", "200"),
            ("storage_protocols", '["smb"]'),
            ("storage_filesystem_path", f"{STORAGE2_PATH}/mocker"),
            ("storage_export_path", f"{STORAGE2_PATH}/mocker"),
            ("cost_center", "CC0004259"),
            ("department_number", "CH00409"),
            ("service_rate", "subscription"),
            ("secure", "No"),
            ("audit", "No"),
            ("billing_exempt", "No"),
            ("subsidized", "Yes"),
            ("billing_contact", "jin810"),
            ("technical_contact", "jin810"),
            ("storage_ticket", "ITSD-2222"),
            ("billing_startdate", "2020-04-15T00: 00: 00.000Z"),
            ("fileset_name", "mocker_active"),
            ("fileset_alias", "mocker_active"),
            (
                "itsm_comment",
                '{"afm_cache_enable":true,"_jenkins":"https://systems-ci.gsc.wustl.edu/job/storage1_allocation/2652","add_archive":"true"}',
            ),
            ("billing_cycle", "monthly"),
            ("sla_name", ""),
        ]

        self.expected_allocation_attributes_missing_contacts = [
            ("storage_name", "mocker_missing_contacts"),
            ("storage_quota", "200"),
            ("storage_protocols", '["smb"]'),
            ("storage_filesystem_path", f"{STORAGE2_PATH}/mocker_missing_contacts"),
            ("storage_export_path", f"{STORAGE2_PATH}/mocker_missing_contacts"),
            ("cost_center", "CC0004259"),
            ("department_number", "CH00409"),
            ("service_rate", "subscription"),
            ("secure", "No"),
            ("audit", "No"),
            ("billing_exempt", "No"),
            ("subsidized", "Yes"),
            ("storage_ticket", "ITSD-2222"),
            ("billing_startdate", "2020-04-15T00: 00: 00.000Z"),
            ("fileset_name", "mocker_missing_contacts_active"),
            ("fileset_alias", "mocker_missing_contacts_active"),
            (
                "itsm_comment",
                '{"afm_cache_enable":true,"_jenkins":"https://systems-ci.gsc.wustl.edu/job/storage1_allocation/2652","add_archive":"true"}',
            ),
            ("billing_cycle", "monthly"),
            ("sla_name", ""),
        ]

        self.expected_allocation_attributes_billing_startdate_missing = [
            ("storage_name", "mocker"),
            ("storage_quota", "200"),
            ("storage_protocols", '["smb"]'),
            ("storage_filesystem_path", f"{STORAGE2_PATH}/mocker"),
            ("storage_export_path", f"{STORAGE2_PATH}/mocker"),
            ("cost_center", "CC0004259"),
            ("department_number", "CH00409"),
            ("service_rate", "subscription"),
            ("secure", "No"),
            ("audit", "No"),
            ("billing_exempt", "No"),
            ("subsidized", "Yes"),
            ("billing_contact", "jin810"),
            ("technical_contact", "jin810"),
            ("storage_ticket", "ITSD-2222"),
            ("fileset_name", "mocker_active"),
            ("fileset_alias", "mocker_active"),
            (
                "itsm_comment",
                '{"afm_cache_enable":true,"_jenkins":"https://systems-ci.gsc.wustl.edu/job/storage1_allocation/2652","add_archive":"true"}',
            ),
            ("billing_cycle", "monthly"),
            ("sla_name", ""),
        ]

    @mock.patch(
        "coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront.ItsmClient"
    )
    @mock.patch(
        "coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI"
    )
    @mock.patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
    def test_migrate_to_coldfront_by_fileset_name(
        self,
        mock_async_task: mock.MagicMock,
        mock_active_directory_api: mock.MagicMock,
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
        self.assertEqual(allocation.id, result["allocation_id"])
        self.assertEqual(allocation.project, project)
        self.assertEqual(allocation.project.title, name)

        allocation_attributes = AllocationAttribute.objects.filter(
            allocation=result["allocation_id"]
        )
        allocation_attribute_values = allocation_attributes.values_list(
            "allocation_attribute_type__name", "value"
        )

        for attribute_value in self.expected_allocation_attributes:
            self.assertIn(attribute_value, allocation_attribute_values)

        self.assertEqual(allocation_attributes.count(), 21)

        project_attributes = ProjectAttribute.objects.filter(
            project=result["project_id"]
        )
        self.assertEqual(len(project_attributes), 3)

    @mock.patch(
        "coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront.ItsmClient"
    )
    @mock.patch(
        "coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI"
    )
    @mock.patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
    def test_migrate_to_coldfront_by_service_provision_name(
        self,
        mock_async_task: mock.MagicMock,
        mock_active_directory_api: mock.MagicMock,
        mock_itsm_client: mock.MagicMock,
    ) -> None:
        with open(
            "coldfront/plugins/qumulo/static/migration_mappings/mock_itsm_response_body_service_provision_found.json",
            "r",
        ) as file:
            mock_response = json.load(file)["data"]
            itsm_client = mock.MagicMock()
            itsm_client.get_fs1_allocation_by_storage_provision_name.return_value = (
                mock_response
            )
            mock_itsm_client.return_value = itsm_client

        name = "mocker"
        result = self.migrate.by_storage_provision_name(f"{name}")
        self.assertDictEqual(
            result, {"allocation_id": 1, "pi_user_id": 1, "project_id": 1}
        )

        allocation = Allocation.objects.get(id=result["allocation_id"])
        project = Project.objects.get(id=result["project_id"])
        self.assertEqual(allocation.id, result["allocation_id"])
        self.assertEqual(allocation.project, project)
        self.assertEqual(allocation.project.title, name)

        allocation_attributes = AllocationAttribute.objects.filter(
            allocation=result["allocation_id"]
        )
        allocation_attribute_values = allocation_attributes.values_list(
            "allocation_attribute_type__name", "value"
        )

        for attribute_value in self.expected_allocation_attributes:
            self.assertIn(attribute_value, allocation_attribute_values)

        self.assertEqual(allocation_attributes.count(), 21)

        project_attributes = ProjectAttribute.objects.filter(
            project=result["project_id"]
        )
        self.assertEqual(len(project_attributes), 3)

    @mock.patch(
        "coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront.ItsmClient"
    )
    @mock.patch(
        "coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI"
    )
    @mock.patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
    def test_migrate_to_coldfront_by_fileset_alias(
        self,
        mock_async_task: mock.MagicMock,
        mock_active_directory_api: mock.MagicMock,
        mock_itsm_client: mock.MagicMock,
    ) -> None:
        with open(
            "coldfront/plugins/qumulo/static/migration_mappings/mock_itsm_response_body_service_provision_found.json",
            "r",
        ) as file:
            mock_response = json.load(file)["data"]
            itsm_client = mock.MagicMock()
            itsm_client.get_fs1_allocation_by_fileset_alias.return_value = mock_response
            mock_itsm_client.return_value = itsm_client

        fileset_alias = "mocker_active"
        name = "mocker"
        result = self.migrate.by_fileset_alias(f"{fileset_alias}")
        self.assertDictEqual(
            result, {"allocation_id": 1, "pi_user_id": 1, "project_id": 1}
        )

        allocation = Allocation.objects.get(id=result["allocation_id"])
        project = Project.objects.get(id=result["project_id"])
        self.assertEqual(allocation.id, result["allocation_id"])
        self.assertEqual(allocation.project, project)
        self.assertEqual(allocation.project.title, name)

        allocation_attributes = AllocationAttribute.objects.filter(
            allocation=result["allocation_id"]
        )
        allocation_attribute_values = allocation_attributes.values_list(
            "allocation_attribute_type__name", "value"
        )

        for attribute_value in self.expected_allocation_attributes:
            self.assertIn(attribute_value, allocation_attribute_values)

        self.assertEqual(allocation_attributes.count(), 21)

        project_attributes = ProjectAttribute.objects.filter(
            project=result["project_id"]
        )
        self.assertEqual(len(project_attributes), 3)

    @mock.patch(
        "coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront.ItsmClient"
    )
    @mock.patch(
        "coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI"
    )
    @mock.patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
    def test_migrate_to_coldfront_with_contacts_missing(
        self,
        mock_async_task: mock.MagicMock,
        mock_active_directory_api: mock.MagicMock,
        mock_itsm_client: mock.MagicMock,
    ) -> None:
        with open(
            "coldfront/plugins/qumulo/static/migration_mappings/mock_itsm_response_body_service_provision_found_missing_contacts.json",
            "r",
        ) as file:
            mock_response = json.load(file)["data"]
            itsm_client = mock.MagicMock()
            itsm_client.get_fs1_allocation_by_fileset_name.return_value = mock_response
            mock_itsm_client.return_value = itsm_client

        name = "mocker_missing_contacts"
        result = self.migrate.by_fileset_name(f"{name}_active")
        allocation = Allocation.objects.get(id=result["allocation_id"])
        self.assertEqual(allocation.id, result["allocation_id"])

        allocation_attributes = AllocationAttribute.objects.filter(
            allocation=result["allocation_id"]
        )
        allocation_attribute_values = allocation_attributes.values_list(
            "allocation_attribute_type__name", "value"
        )

        for attribute_value in self.expected_allocation_attributes_missing_contacts:
            self.assertIn(attribute_value, allocation_attribute_values)

        self.assertEqual(allocation_attributes.count(), 19)
        # optional fields with empty or missing values should not create
        # allocation_attributes on create allocation
        for value in [("billing_contact", ""), ("technical_contact", "")]:
            self.assertNotIn(value, allocation_attribute_values)

    @mock.patch(
        "coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront.ItsmClient"
    )
    @mock.patch(
        "coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI"
    )
    @mock.patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
    def test_migrate_to_coldfront_with_billing_startdate_missing(
        self,
        mock_async_task: mock.MagicMock,
        mock_active_directory_api: mock.MagicMock,
        mock_itsm_client: mock.MagicMock,
    ) -> None:
        with open(
            "coldfront/plugins/qumulo/static/migration_mappings/mock_itsm_response_body_billing_startdate_not_found.json",
            "r",
        ) as file:
            mock_response = json.load(file)["data"]
            itsm_client = mock.MagicMock()
            itsm_client.get_fs1_allocation_by_fileset_name.return_value = mock_response
            mock_itsm_client.return_value = itsm_client

        name = "mocker_missing_contacts"
        result = self.migrate.by_fileset_name(f"{name}_active")
        allocation = Allocation.objects.get(id=result["allocation_id"])
        self.assertEqual(allocation.id, result["allocation_id"])

        allocation_attributes = AllocationAttribute.objects.filter(
            allocation=result["allocation_id"]
        )
        allocation_attribute_values = allocation_attributes.values_list(
            "allocation_attribute_type__name", "value"
        )

        for (
            attribute_value
        ) in self.expected_allocation_attributes_billing_startdate_missing:
            self.assertIn(attribute_value, allocation_attribute_values)

        self.assertEqual(allocation_attributes.count(), 20)
        # optional fields with empty or missing values should not create
        # allocation_attributes on create allocation
        for value in [("billing_startdate", "")]:
            self.assertNotIn(value, allocation_attribute_values)
