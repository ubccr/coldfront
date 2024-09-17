from django.test import TestCase, tag
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.tests_integration.utils.test_qumulo_api.utils import (
    create_test_export,
)


class TestDeleteQuota(TestCase):
    @tag('integration')
    def test_deletes_a_quota(self):
        qumulo_api = QumuloAPI()
        export_fs_path = "/test/test-project"
        create_test_export(qumulo_api, export_fs_path)

        file_attr = qumulo_api.get_file_attributes(export_fs_path)

        qumulo_api.delete_quota(export_fs_path)

        get_quotas_res = qumulo_api.rc.quota.get_all_quotas()
        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_fs_path)
        qumulo_api.delete_nfs_export(export_id)

        for page in get_quotas_res:
            for quota in page["quotas"]:
                self.assertNotEqual(quota["id"], file_attr["id"])
