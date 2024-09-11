from django.test import TestCase
from coldfront_plugin_qumulo.utils.qumulo_api import QumuloAPI


class TestListNFSExports(TestCase):
    def test_lists_all_exports(self):
        qumulo_api = QumuloAPI()

        nfs_exports = qumulo_api.list_nfs_exports()

        self.assertTrue("entries" in nfs_exports)
        self.assertIsInstance(nfs_exports["entries"], list)
