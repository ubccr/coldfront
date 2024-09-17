from django.test import TestCase
from unittest.mock import call, patch, MagicMock
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI


@patch.object(QumuloAPI, "get_id", MagicMock())
@patch("coldfront.plugins.qumulo.utils.qumulo_api.RestClient")
class DeleteAllocation(TestCase):
    def test_gets_nfs_export_id(self, mock_RestClient: MagicMock):
        with patch.object(QumuloAPI, "get_id", MagicMock()) as mock_get_id:
            qumulo_instance = QumuloAPI()
            qumulo_instance._delete_allocation(
                fs_path="/foo", name="foo", protocols=["nfs"], export_path="bar"
            )

            mock_get_id.assert_called_once_with(protocol="nfs", export_path="bar")

    def test_gets_smb_export_id(self, mock_RestClient: MagicMock):
        with patch.object(QumuloAPI, "get_id", MagicMock()) as mock_get_id:
            qumulo_instance = QumuloAPI()
            qumulo_instance._delete_allocation(
                fs_path="/foo", name="foo", protocols=["smb"], export_path="bar"
            )

            mock_get_id.assert_called_once_with(protocol="smb", name="foo")

    def test_deletes_nfs_export(self, mock_RestClient: MagicMock):
        with patch.object(
            QumuloAPI, "delete_protocol", MagicMock()
        ) as mock_delete_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance._delete_allocation(
                fs_path="/foo", export_path="bar", name="foo", protocols=["nfs"]
            )

            mock_RestClient.assert_called_once()
            mock_delete_protocol.assert_called_once_with(
                export_path="bar", name="foo", protocol="nfs"
            )

    def test_deletes_smb_share(self, mock_RestClient: MagicMock):
        with patch.object(
            QumuloAPI, "delete_protocol", MagicMock()
        ) as mock_delete_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance._delete_allocation(
                fs_path="/foo", export_path="bar", name="foo", protocols=["smb"]
            )

            mock_RestClient.assert_called_once()
            mock_delete_protocol.assert_called_once_with(
                export_path="bar", name="foo", protocol="smb"
            )

    def test_deletes_multiple_allocations(self, mock_RestClient: MagicMock):
        with patch.object(
            QumuloAPI, "delete_protocol", MagicMock()
        ) as mock_delete_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance._delete_allocation(
                fs_path="/foo",
                export_path="bar",
                name="foo",
                protocols=["smb", "nfs"],
            )

            mock_RestClient.assert_called_once()
            calls = [
                call(export_path="bar", name="foo", protocol="nfs"),
                call(export_path="bar", name="foo", protocol="smb"),
            ]
            mock_delete_protocol.assert_has_calls(calls, any_order=True)

    def test_deletes_nfs_smb_allocations(self, mock_RestClient: MagicMock):
        with patch.object(
            QumuloAPI, "delete_protocol", MagicMock()
        ) as mock_delete_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance._delete_allocation(
                fs_path="/foo",
                export_path="bar",
                name="foo",
                protocols=["smb", "nfs"],
            )

            mock_RestClient.assert_called_once()
            calls = [
                call(export_path="bar", name="foo", protocol="nfs"),
                call(export_path="bar", name="foo", protocol="smb"),
            ]
            mock_delete_protocol.assert_has_calls(calls, any_order=True)
            assert mock_delete_protocol.call_count == 2

    def test_rejects_when_incorrect_protocol(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance._delete_allocation(
                fs_path="/foo", protocols=["bad_protocol"]
            )

    def test_deletes_nfs_smb_with_only_required_params(
        self, mock_RestClient: MagicMock
    ):
        with patch.object(
            QumuloAPI, "delete_protocol", MagicMock()
        ) as mock_delete_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance._delete_allocation(
                fs_path="/foo", export_path="bar", protocols=["nfs", "smb"]
            )

            mock_RestClient.assert_called_once()
            calls = [
                call(export_path="bar", name=None, protocol="nfs"),
                call(export_path="bar", name=None, protocol="smb"),
            ]
            mock_delete_protocol.assert_has_calls(calls, any_order=True)
            assert mock_delete_protocol.call_count == 2

    def test_calls_delete_quota(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with patch.object(QumuloAPI, "delete_quota", MagicMock()) as mock_delete_quota:
            qumulo_instance._delete_allocation(
                fs_path="/foo", name="foo", protocols=["smb"]
            )

            mock_delete_quota.assert_called_once_with("/foo")
