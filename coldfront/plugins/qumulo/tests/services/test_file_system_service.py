from unittest.mock import MagicMock, patch
from coldfront.plugins.qumulo.services.file_system_service import FileSystemService

PETABYTE_IN_BYTES = 1e15


from django.test import TestCase


class TestFileSystemService(TestCase):

    def setUp(self) -> None:
        self.mock_file_system_response_successful = {
            "block_size_bytes": 4096,
            "total_size_bytes": "5498921790996480",
            "free_size_bytes": "1449206347350016",
            "snapshot_size_bytes": "181465474080768",
        }

        self.expected_result_successful = {
            "total_size": 5.4989,
            "free_size": 1.4492,
            "snapshot_size": 0.1815,
        }

        self.mock_file_system_response_unsuccessful = {}

        self.expected_result_unsuccessful =  {
            "total_size": None,
            "free_size": None,
            "snapshot_size": None,
        }

        return super().setUp()

    @patch("coldfront.plugins.qumulo.services.file_system_service.QumuloAPI")
    def test_get_file_system_stats_when_api_call_successful(
        self, qumulo_api_mock: MagicMock
    ) -> None:
        qumulo_api = MagicMock()
        qumulo_api.get_file_system_stats.return_value = (
            self.mock_file_system_response_successful
        )
        qumulo_api_mock.return_value = qumulo_api

        actual_result = FileSystemService.get_file_system_stats()
        self.assertDictEqual(self.expected_result_successful, actual_result)

    @patch("coldfront.plugins.qumulo.services.file_system_service.QumuloAPI")
    def test_get_file_system_stats_when_api_call_unsuccessful(
        self, qumulo_api_mock: MagicMock
    ) -> None:
        qumulo_api = MagicMock()
        qumulo_api.get_file_system_stats.return_value = (
            self.mock_file_system_response_unsuccessful
        )
        qumulo_api_mock.return_value = qumulo_api

        actual_result = FileSystemService.get_file_system_stats()
        self.assertDictEqual(self.expected_result_unsuccessful, actual_result)
