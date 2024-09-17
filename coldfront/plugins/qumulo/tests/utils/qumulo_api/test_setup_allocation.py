from django.test import TestCase
from unittest.mock import patch, MagicMock

from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.utils.aces_manager import AcesManager

from deepdiff import DeepDiff


@patch("coldfront.plugins.qumulo.utils.qumulo_api.RestClient")
class SetupAllocation(TestCase):
    def test_calls_create_directory_if_root_path(self, mock_RestClient: MagicMock):
        mock_create_directory = MagicMock()
        mock_RestClient.return_value.fs.create_directory = mock_create_directory

        fs_path = "/storage2/fs1/foo"

        qumulo_instance = QumuloAPI()

        with patch("coldfront.plugins.qumulo.utils.qumulo_api.open") as mock_open:
            qumulo_instance.setup_allocation(fs_path)

            mock_create_directory.assert_called_once_with(
                dir_path=fs_path, name="Active"
            )

    def test_does_nothing_if_not_root_path(self, mock_RestClient: MagicMock):
        mock_create_directory = MagicMock()
        mock_RestClient.return_value.fs.create_directory = mock_create_directory

        fs_path = "/storage2/fs1/foo/bar"

        qumulo_instance = QumuloAPI()

        qumulo_instance.setup_allocation(fs_path)

        mock_create_directory.assert_not_called()

    def test_creates_default_acls_if_root_path(self, mock_RestClient: MagicMock):
        mock_set_acl_v2 = MagicMock()
        mock_RestClient.return_value.fs.set_acl_v2 = mock_set_acl_v2

        fs_path = "/storage2/fs1/foo"
        expected_acl = AcesManager().get_base_acl()
        expected_acl["aces"] = AcesManager.default_aces

        qumulo_instance = QumuloAPI()

        with patch("coldfront.plugins.qumulo.utils.qumulo_api.open") as mock_open:
            qumulo_instance.setup_allocation(fs_path)

            mock_set_acl_v2.assert_called_once()

            call_args = mock_set_acl_v2.call_args
            self.assertEqual(call_args.kwargs["path"], fs_path)

            diff = DeepDiff(call_args.kwargs["acl"], expected_acl, ignore_order=True)
            self.assertFalse(diff)
