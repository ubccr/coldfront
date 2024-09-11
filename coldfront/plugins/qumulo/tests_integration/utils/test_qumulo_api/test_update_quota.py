from django.test import TestCase
from coldfront_plugin_qumulo.utils.qumulo_api import QumuloAPI
from coldfront_plugin_qumulo.tests_integration.utils.test_qumulo_api.utils import (
    create_test_export,
)


class TestDeleteQuota(TestCase):
    def test_deletes_a_quota(self):
        qumulo_api = QumuloAPI()
        export_fs_path = "/test-project"
        create_test_export(qumulo_api, export_fs_path)

        file_attr = qumulo_api.get_file_attributes(export_fs_path)

        new_limit_in_bytes = 8192
        try:
            qumulo_api.update_quota(export_fs_path, new_limit_in_bytes)
        except:
            self.fail("Unexpected failure updating quota")
        quota = qumulo_api.rc.quota.get_quota(file_attr["id"])

        qumulo_api.delete_quota(export_fs_path)
        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_fs_path)
        qumulo_api.delete_nfs_export(export_id)

        self.assertEquals(quota["limit"], str(new_limit_in_bytes))
