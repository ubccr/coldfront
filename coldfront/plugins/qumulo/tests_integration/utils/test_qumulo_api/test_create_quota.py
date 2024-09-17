from django.test import TestCase, tag
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from qumulo.commands.nfs import parse_nfs_export_restrictions


class TestCreateQuota(TestCase):
    @tag('integration')
    def test_creates_quota(self):
        qumulo_api = QumuloAPI()

        export_path = "/test-project"
        fs_path = "/test-other"
        nfs_restrictions = [
            {
                "host_restrictions": [],
                "user_mapping": "NFS_MAP_NONE",
                "require_privileged_port": False,
                "read_only": False,
            }
        ]

        created_export = qumulo_api.rc.nfs.nfs_add_export(
            export_path=export_path,
            fs_path=fs_path,
            description=export_path,
            restrictions=parse_nfs_export_restrictions(nfs_restrictions),
            allow_fs_path_create=True,
            tenant_id=1,
        )

        limit_in_bytes = 1024

        try:
            created_quota = qumulo_api.create_quota(fs_path, limit_in_bytes)
        except:
            self.fail("Unexpected failure creating quota")

        qumulo_api.delete_quota(fs_path)

        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_path)
        qumulo_api.delete_nfs_export(export_id)

        self.assertEquals(created_quota["limit"], str(limit_in_bytes))
