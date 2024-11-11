from django.test import TestCase, tag
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.tests_integration.utils.test_qumulo_api.utils import (
    create_test_export,
)


class TestUpdateAllocation(TestCase):
    @tag("integration")
    def test_update_allocation_logs_error(self):
        qumulo_api = QumuloAPI()
        export_fs_path = "/test-project/update-allocation"
        name = "random"
        create_test_export(qumulo_api, export_fs_path)

        file_attr = qumulo_api.get_file_attributes(export_fs_path)
        new_limit_in_bytes = 10**6
        qumulo_api.update_allocation(
            protocols=["nfs"],
            export_path=export_fs_path,
            fs_path=export_fs_path,
            name=name,
            limit_in_bytes=new_limit_in_bytes,
        )

        quota = qumulo_api.rc.quota.get_quota(file_attr["id"])

        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_fs_path)

        qumulo_api._delete_allocation(
            protocols=["nfs"], fs_path=export_fs_path, export_path=export_fs_path
        )

        self.assertIsNotNone(export_id)

        self.assertEquals(quota["limit"], str(new_limit_in_bytes))
