from django.test import TestCase, tag

from coldfront.plugins.qumulo.services.itsm.migrate_to_coldfront import (
    MigrateToColdfront,
)

from coldfront.plugins.qumulo.tests.fixtures import create_allocation_assets

class TestMigrateToColdfront(TestCase):

    def setUp(self) -> None:
        self.migrate = MigrateToColdfront()
        create_allocation_assets()

    @tag("integration")
    def test_migrate_to_coldfront_by_fileset_name_found(self):
        self.migrate.by_fileset_name("ysjun_active")

    @tag("integration")
    def test_migrate_to_coldfront_by_fileset_name_not_found(self):
        fileset_key = "not_going_to_be_found"
        self.assertRaises(
            Exception,
            self.migrate.by_fileset_name,
            fileset_key,
            msg=(f'ITSM allocation was not found for "{fileset_key}"'),
        )
