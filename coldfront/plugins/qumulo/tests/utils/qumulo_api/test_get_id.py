from django.test import TestCase
from unittest.mock import patch, MagicMock
from coldfront_plugin_qumulo.utils.qumulo_api import QumuloAPI


@patch("coldfront_plugin_qumulo.utils.qumulo_api.RestClient")
class GetId(TestCase):
    def test_calls_nfs_endpoint_with_url_encode(self, mock_RestClient: MagicMock):
        mock_request: MagicMock = mock_RestClient.return_value.request
        qumulo_instance = QumuloAPI()

        qumulo_instance.get_id(protocol="nfs", export_path="/test")

        mock_request.assert_called_once_with(
            method="GET", uri="/v2/nfs/exports/%2Ftest"
        )

    def test_nfs_returns_id(self, mock_RestClient: MagicMock):
        mock_request: MagicMock = mock_RestClient.return_value.request
        qumulo_instance = QumuloAPI()
        mock_request.return_value = {"id": "856", "export_path": "/test-project"}

        id = qumulo_instance.get_id(protocol="nfs", export_path="/test")
        self.assertEqual(id, "856")

    def test_calls_smb_endpoint_with_url_encode(self, mock_RestClient: MagicMock):
        mock_request: MagicMock = mock_RestClient.return_value.request
        qumulo_instance = QumuloAPI()
        qumulo_instance.get_id(protocol="smb", name="/test")

        mock_request.assert_called_once_with(method="GET", uri="/v2/smb/shares/%2Ftest")

    def test_smb_returns_id(self, mock_RestClient: MagicMock):
        mock_request: MagicMock = mock_RestClient.return_value.request
        qumulo_instance = QumuloAPI()
        mock_request.return_value = {"id": "856"}

        id = qumulo_instance.get_id(protocol="smb", name="test")
        self.assertEqual(id, "856")

    def test_rejects_bad_protocol(self, mock_RestClient: MagicMock):
        mock_request: MagicMock = mock_RestClient.return_value.request
        qumulo_instance = QumuloAPI()
        mock_request.return_value = {"id": "856"}

        with self.assertRaises(ValueError):
            qumulo_instance.get_id(protocol="foo", name="test")
