from django.test import TestCase
from unittest.mock import call, patch, MagicMock, PropertyMock
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI


@patch("coldfront.plugins.qumulo.utils.qumulo_api.RestClient")
class CreateAllocation(TestCase):
    def test_rejects_when_incorrect_protocol(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_allocation(
                protocols=["bad_protocol"],
                export_path="/foo",
                fs_path="/bar",
                name="baz",
                limit_in_bytes=10**9,
            )

    def test_rejects_if_some_protocols_are_bad(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            with patch.object(
                QumuloAPI, "create_protocol", MagicMock()
            ) as mock_create_protocol:
                qumulo_instance.create_allocation(
                    protocols=["nfs", "bad_protocol"],
                    export_path="/foo",
                    fs_path="/bar",
                    name="baz",
                    limit_in_bytes=10**9,
                )
        mock_create_protocol.assert_not_called()

    def test_rejects_when_missing_name(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_allocation(
                protocols=["nfs"],
                export_path="/foo",
                fs_path="/bar",
                name=None,
                limit_in_bytes=10**9,
            )

    def test_rejects_when_fs_path_not_absolute(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_allocation(
                protocols=["nfs"],
                export_path="/foo",
                fs_path="bar",
                name="bar",
                limit_in_bytes=10**9,
            )

    def test_rejects_when_fs_path_none(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_allocation(
                protocols=["nfs"],
                export_path="/foo",
                fs_path=None,
                name="bar",
                limit_in_bytes=10**9,
            )

    def test_rejects_nfs_when_export_path_not_abosolute(
        self, mock_RestClient: MagicMock
    ):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_allocation(
                protocols=["nfs"],
                export_path="foo",
                fs_path="/bar",
                name="bar",
                limit_in_bytes=10**9,
            )

    def test_rejects_nfs_when_export_path_none(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        with self.assertRaises(ValueError):
            qumulo_instance.create_allocation(
                protocols=["nfs"],
                export_path=None,
                fs_path="/bar",
                name="bar",
                limit_in_bytes=10**9,
            )

    def test_accepts_when_protocols_is_None(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        qumulo_instance = QumuloAPI()
        qumulo_instance.create_allocation(
            protocols=None,
            export_path="/foo",
            fs_path="/bar",
            name="bar",
            limit_in_bytes=10**9,
        )

        mock_RestClient.assert_called()

    def test_accepts_when_protocols_is_empty(self, mock_RestClient: MagicMock):
        qumulo_instance = QumuloAPI()

        qumulo_instance = QumuloAPI()
        qumulo_instance.create_allocation(
            protocols=[],
            export_path="/foo",
            fs_path="/bar",
            name="bar",
            limit_in_bytes=10**9,
        )

        mock_RestClient.assert_called()

    def test_creates_nfs_export(
        self,
        mock_RestClient: MagicMock,
    ):
        with patch.object(
            QumuloAPI, "create_protocol", MagicMock()
        ) as mock_create_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance.create_allocation(
                protocols=["nfs"],
                export_path="/foo",
                fs_path="/bar",
                name="bar",
                limit_in_bytes=10**9,
            )

            mock_RestClient.assert_called()
            mock_create_protocol.assert_called_once_with(
                protocol="nfs", export_path="/foo", fs_path="/bar", name="bar"
            )

    def test_creates_smb_share(
        self,
        mock_RestClient: MagicMock,
    ):
        with patch.object(
            QumuloAPI, "create_protocol", MagicMock()
        ) as mock_create_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance.create_allocation(
                protocols=["smb"],
                export_path="/foo",
                fs_path="/bar",
                name="bar",
                limit_in_bytes=10**9,
            )

            mock_RestClient.assert_called()
            mock_create_protocol.assert_called_once_with(
                protocol="smb", fs_path="/bar", name="bar", export_path="/foo"
            )

    def test_creates_multiple_protocols(
        self,
        mock_RestClient: MagicMock,
    ):
        with patch.object(
            QumuloAPI, "create_protocol", MagicMock()
        ) as mock_create_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance.create_allocation(
                protocols=["smb", "nfs"],
                export_path="/foo",
                fs_path="/bar",
                name="bar",
                limit_in_bytes=10**9,
            )

            mock_RestClient.assert_called()
            calls = [
                call(protocol="nfs", fs_path="/bar", name="bar", export_path="/foo"),
                call(protocol="smb", fs_path="/bar", name="bar", export_path="/foo"),
            ]
            mock_create_protocol.assert_has_calls(calls, any_order=True)

    def test_creates_nfs_smb_protocols(
        self,
        mock_RestClient: MagicMock,
    ):
        with patch.object(
            QumuloAPI, "create_protocol", MagicMock()
        ) as mock_create_protocol:
            qumulo_instance = QumuloAPI()
            qumulo_instance.create_allocation(
                protocols=["smb", "nfs"],
                export_path="/foo",
                fs_path="/bar",
                name="bar",
                limit_in_bytes=10**9,
            )

            mock_RestClient.assert_called()
            calls = [
                call(protocol="nfs", fs_path="/bar", name="bar", export_path="/foo"),
                call(protocol="smb", fs_path="/bar", name="bar", export_path="/foo"),
            ]
            mock_create_protocol.assert_has_calls(calls, any_order=True)

            assert mock_create_protocol.call_count == 2

    def test_calls_create_quota(
        self,
        mock_RestClient: MagicMock,
    ):
        mock_nfs = PropertyMock(return_value=MagicMock())
        type(mock_RestClient.return_value).nfs = mock_nfs

        qumulo_instance = QumuloAPI()

        fs_path = "/bar"
        limit_in_bytes = 10**9

        with patch.object(QumuloAPI, "create_quota", MagicMock()) as mock_create_quota:
            qumulo_instance.create_allocation(
                protocols=["nfs"],
                export_path="/foo",
                fs_path=fs_path,
                name="bar",
                limit_in_bytes=limit_in_bytes,
            )

            mock_create_quota.assert_called_once_with(
                fs_path="/bar", limit_in_bytes=limit_in_bytes
            )
