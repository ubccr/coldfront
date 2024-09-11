from django.test import TestCase
from coldfront_plugin_qumulo.utils.qumulo_api import QumuloAPI
from coldfront_plugin_qumulo.tests_integration.utils.test_qumulo_api.utils import (
    create_test_export,
)


class TestGetFileAttributes(TestCase):
    def test_gets_file_attributes(self):
        qumulo_api = QumuloAPI()
        export_fs_path = "/test/test-get-file-attr"
        create_test_export(qumulo_api, export_fs_path)

        try:
            file_attributes = qumulo_api.get_file_attributes(export_fs_path)
        except:
            self.fail("Error getting file attribute")

        qumulo_api.delete_quota(export_fs_path)

        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_fs_path)
        qumulo_api.delete_nfs_export(export_id)

        self.assertIn("id", file_attributes.keys())
        self.assertIn("path", file_attributes.keys())
        self.assertEqual(file_attributes["path"], export_fs_path + "/")
