import json

from django.test import TestCase


class TestImportDataFromItsm(TestCase):

    def mock_itsm_response_body(self) -> str:
        with open(
            "coldfront/plugins/qumulo/static/migration_mappings/mock_itsm_response_body_service_provision_found.json",
            "r",
        ) as file:
            return json.load(file)

    def mock_itsm_response_body_not_found(self) -> str:
        with open(
            "coldfront/plugins/qumulo/static/migration_mappings/mock_itsm_response_body_service_provision_not_found.json",
            "r",
        ) as file:
            return json.load(file)

    def test_service_provision_found(self) -> None:
        response_body = self.mock_itsm_response_body()
        self.assertNotEqual(response_body["data"], [])

    def test_service_provision_not_found(self) -> None:
        response_body = self.mock_itsm_response_body_not_found()
        self.assertListEqual(response_body["data"], [])
