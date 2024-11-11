from django.test import TestCase, tag
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.tests_integration.utils.test_qumulo_api.utils import (
    create_test_export,
)


class TestDeleteNFSExport(TestCase):
    @tag("integration")
    def test_deletes_nfs_export(self):
        qumulo_api = QumuloAPI()

        export_fs_path = "/test-delete"

        create_test_export(qumulo_api, export_fs_path=export_fs_path)
        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_fs_path)

        qumulo_api.delete_quota(export_fs_path)
        qumulo_api.delete_nfs_export(export_id)

        exports = qumulo_api.list_nfs_exports()

        for entry in exports["entries"]:
            self.assertNotEqual(export_id, entry["id"])
