from django.test import TestCase, tag
from coldfront.plugins.qumulo.utils.qumulo_api import QumuloAPI
from coldfront.plugins.qumulo.tests_integration.utils.test_qumulo_api.utils import (
    create_test_export,
)


class TestUpdateNFSExport(TestCase):
    @tag('integration')
    def test_updates_an_export_description(self):
        qumulo_api = QumuloAPI()
        description = "test-test_update_project-active"
        export_fs_path = "/test/test-update-description"
        create_test_export(
            qumulo_api,
            export_fs_path=export_fs_path,
            description=description,
        )
        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_fs_path)

        update_description = "updated_description"

        try:
            update_response = qumulo_api.update_nfs_export(
                export_id, description=update_description
            )
        except:
            self.fail("Error updating nfs export")

        qumulo_api.delete_quota(export_fs_path)
        qumulo_api.delete_nfs_export(export_id)

        self.assertEqual(update_response["description"], update_description)

    @tag('integration')
    def test_updates_paths(self):
        qumulo_api = QumuloAPI()

        export_fs_path = "/test/test-update-project"
        create_test_export(qumulo_api, export_fs_path)
        export_id = qumulo_api.get_id(protocol="nfs", export_path=export_fs_path)

        export_path = "/test/test_move"
        fs_path = "/test/test_foo"

        try:
            update_response = qumulo_api.update_nfs_export(
                export_id=export_id,
                export_path=export_path,
                fs_path=fs_path,
            )
        except:
            self.fail("Error updating nfs export")

        qumulo_api.delete_quota(export_fs_path)
        qumulo_api.delete_nfs_export(export_id)

        self.assertEqual(update_response["export_path"], export_path)
        self.assertEqual(update_response["fs_path"], fs_path)
