from django.test import TestCase
from unittest.mock import patch, MagicMock, PropertyMock
from coldfront_plugin_qumulo.utils.qumulo_api import QumuloAPI


@patch("coldfront_plugin_qumulo.utils.qumulo_api.RestClient")
class CreateQuota(TestCase):
    def test_calls_get_file_attr(self, mock_RestClient: MagicMock):
        mock_quota = PropertyMock(return_value=MagicMock())
        type(mock_RestClient.return_value).quota = mock_quota

        mock_fs = PropertyMock(return_value=MagicMock())
        type(mock_RestClient.return_value).fs = mock_fs

        fs_path = "foo"

        qumulo_instance = QumuloAPI()
        qumulo_instance.create_quota(fs_path=fs_path, limit_in_bytes=10**9)

        mock_fs.return_value.get_file_attr.assert_called_once_with(path=fs_path)

    def test_calls_create_quota(self, mock_RestClient: MagicMock):
        mock_quota = PropertyMock(return_value=MagicMock())
        type(mock_RestClient.return_value).quota = mock_quota

        mock_fs = PropertyMock(return_value=MagicMock())
        type(mock_RestClient.return_value).fs = mock_fs

        fs_path = "foo"
        id = 1
        limit_in_bytes = 10**9
        mock_fs.return_value.get_file_attr.return_value = {"id": id}

        qumulo_instance = QumuloAPI()
        qumulo_instance.create_quota(fs_path=fs_path, limit_in_bytes=limit_in_bytes)

        mock_quota.return_value.create_quota.assert_called_once_with(id, limit_in_bytes)
