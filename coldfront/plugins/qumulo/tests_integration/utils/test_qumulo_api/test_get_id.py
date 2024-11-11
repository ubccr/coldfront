from django.test import TestCase, tag
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from qumulo.commands.nfs import parse_nfs_export_restrictions


class TestGetId(TestCase):
    @tag("integration")
    def test_gets_id(self):
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

        try:
            id_response = qumulo_api.get_id(protocol="nfs", export_path=export_path)
        except:
            self.fail("Unexpected Failure Getting Id")

        self.assertEqual(created_export["id"], id_response)

        qumulo_api.delete_nfs_export(id_response)
