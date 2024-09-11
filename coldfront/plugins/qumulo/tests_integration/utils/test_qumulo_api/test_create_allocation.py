from django.test import TestCase
from coldfront_plugin_qumulo.utils.qumulo_api import QumuloAPI


class TestCreateAllocation(TestCase):
    def test_creates_nfs_export(self):
        qumulo_api = QumuloAPI()

        export_path = "/test/integration-project"
        fs_path = "/test/integration-project"
        name = "integration-test"

        qumulo_api.create_allocation(
            protocols=["nfs"],
            export_path=export_path,
            fs_path=fs_path,
            name=name,
            limit_in_bytes=10**6,
        )

        qumulo_api.delete_quota(fs_path)

        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_path)
        qumulo_api.delete_nfs_export(export_id)
