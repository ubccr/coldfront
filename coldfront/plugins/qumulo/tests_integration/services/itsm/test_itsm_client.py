import os

from django.test import TestCase, tag

from unittest import mock

from coldfront.plugins.qumulo.services.itsm.itsm_client import ItsmClient


class TestItsmClient(TestCase):

    def setUp(self) -> None:
        self.itsm_client = ItsmClient()

    @tag("integration")
    def test_itsm_client_when_service_provision_is_found_by_fileset_name(self):
        itsm_client = self.itsm_client
        empty_list = []
        fileset_name = "wexler_active"
        data = itsm_client.get_fs1_allocation_by_fileset_name(fileset_name)
        self.assertIsNot(data, empty_list)
        service_provision = data[0]
        self.assertIsInstance(service_provision, dict)
        self.assertIn("fileset_name", service_provision.keys())
        self.assertEqual(fileset_name, service_provision.get("fileset_name"))

    @tag("integration")
    def test_itsm_client_when_service_provision_is_not_found_by_fileset_name(self):
        itsm_client = self.itsm_client
        empty_list = []
        self.assertListEqual(
            itsm_client.get_fs1_allocation_by_fileset_name("not_going_to_be_found"),
            empty_list,
        )
        self.assertListEqual(
            itsm_client.get_fs1_allocation_by_fileset_name(None), empty_list
        )

    @tag("integration")
    def test_itsm_client_when_the_fileset_name_is_missing(self):
        itsm_client = self.itsm_client
        self.assertRaises(TypeError, itsm_client.get_fs1_allocation_by_fileset_name)
        # TypeError: get_fs1_allocation_by_fileset_name() missing 1 required positional argument: 'fileset_name'

    @tag("integration")
    def test_itsm_client_when_service_provision_is_found_by_fileset_alias(self):
        itsm_client = self.itsm_client
        empty_list = []
        fileset_alias = "wexler_active"
        data = itsm_client.get_fs1_allocation_by_fileset_alias(fileset_alias)
        self.assertIsNot(data, empty_list)
        service_provision = data[0]
        self.assertIsInstance(service_provision, dict)
        self.assertIn("fileset_alias", service_provision.keys())
        self.assertEqual(fileset_alias, service_provision.get("fileset_alias"))

    @tag("integration")
    def test_itsm_client_when_service_provision_is_not_found_by_fileset_alias(self):
        itsm_client = self.itsm_client
        empty_list = []
        self.assertListEqual(
            itsm_client.get_fs1_allocation_by_fileset_alias("not_going_to_be_found"),
            empty_list,
        )
        self.assertListEqual(
            itsm_client.get_fs1_allocation_by_fileset_alias(None), empty_list
        )

    @tag("integration")
    def test_itsm_client_when_the_fileset_alias_is_missing(self):
        itsm_client = self.itsm_client
        self.assertRaises(TypeError, itsm_client.get_fs1_allocation_by_fileset_alias)
        # TypeError: get_fs1_allocation_by_fileset_alias() missing 1 required positional argument: 'fileset_alias'

    @tag("integration")
    def test_itsm_client_when_service_provision_is_found_by_storage_provision_name(
        self,
    ):
        itsm_client = self.itsm_client
        empty_list = []
        storage_name = "/vol/rdcw-fs1/wexler"
        fileset_alias = "wexler_active"
        data = itsm_client.get_fs1_allocation_by_storage_provision_name(storage_name)
        self.assertIsNot(data, empty_list)
        service_provision = data[0]
        self.assertIsInstance(service_provision, dict)
        self.assertEqual(fileset_alias, service_provision.get("fileset_alias"))

    @tag("integration")
    def test_itsm_client_when_service_provision_is_not_found_by_storage_provision_name(
        self,
    ):
        itsm_client = self.itsm_client
        empty_list = []
        self.assertListEqual(
            itsm_client.get_fs1_allocation_by_storage_provision_name(
                "not_going_to_be_found"
            ),
            empty_list,
        )
        self.assertListEqual(
            itsm_client.get_fs1_allocation_by_storage_provision_name(None), empty_list
        )

    @tag("integration")
    def test_itsm_client_when_the_storage_provision_name_is_missing(self):
        itsm_client = self.itsm_client
        self.assertRaises(
            TypeError, itsm_client.get_fs1_allocation_by_storage_provision_name
        )
        # TypeError: get_fs1_allocation_by_fileset_name() missing 1 required positional argument: 'name'
