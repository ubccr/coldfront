from django.test import TestCase
from django.core.management import call_command


class CommandsTestCase(TestCase):
    def test_import_allocations(self):
        ''' Test import_add_allocations command.
        confirm that:
        - projects that haven't been added get properly logged
        - allocations require dirpath values to be added
        - allocation pi gets added
        - allocation usage, users, user usage get added
        '''

        opts = {'file':'coldfront/core/test_helpers/test_data/test_add_allocations.csv'}
        call_command('import_add_allocations', **opts)
