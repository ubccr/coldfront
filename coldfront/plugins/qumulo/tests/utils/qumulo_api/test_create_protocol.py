from django.test import TestCase
from unittest.mock import patch, MagicMock, PropertyMock
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI


@patch("coldfront.plugins.qumulo.utils.qumulo_api.RestClient")
class CreateProtocol(TestCase):
    def test_rejects_when_missing_protocol(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_protocol(
                protocol=None,
                export_path="/foo",
                fs_path="/bar",
                name="baz",
            )

    def test_rejects_when_incorrect_protocol(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_protocol(
                protocol="bad_protocol",
                export_path="/foo",
                fs_path="/bar",
                name="baz",
            )

    def test_rejects_when_missing_name(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_protocol(
                protocol="nfs",
                export_path="/foo",
                fs_path="/bar",
                name=None,
            )

    def test_rejects_when_fs_path_not_absolute(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_protocol(
                protocol="nfs",
                export_path="/foo",
                fs_path="bar",
                name="bar",
            )

    def test_rejects_when_fs_path_none(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_protocol(
                protocol="nfs",
                export_path="/foo",
                fs_path=None,
                name="bar",
            )

    def test_rejects_when_nfs_export_path_not_abosolute(
        self, mock_RestClient: MagicMock
    ):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_protocol(
                protocol="nfs",
                export_path="foo",
                fs_path="/bar",
                name="bar",
            )

    def test_rejects_when_nfs_export_path_none(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_protocol(
                protocol="nfs",
                export_path=None,
                fs_path="/bar",
                name="bar",
            )

    def test_creates_nfs_export(
        self,
        mock_RestClient: MagicMock,
    ):
        mock_nfs = PropertyMock(return_value=MagicMock())
        type(mock_RestClient.return_value).nfs = mock_nfs

        qumulo_instance = QumuloAPI()
        qumulo_instance.create_protocol(
            protocol="nfs",
            export_path="/foo",
            fs_path="/bar",
            name="bar",
        )

        mock_RestClient.assert_called()
        mock_nfs.return_value.nfs_add_export.assert_called()

    def test_creates_smb_share(
        self,
        mock_RestClient: MagicMock,
    ):
        mock_smb = PropertyMock(return_value=MagicMock())
        type(mock_RestClient.return_value).smb = mock_smb

        qumulo_instance = QumuloAPI()
        qumulo_instance.create_protocol(
            protocol="smb",
            export_path="/foo",
            fs_path="/bar",
            name="bar",
        )

        mock_RestClient.assert_called()
        mock_smb.return_value.smb_add_share.assert_called()
