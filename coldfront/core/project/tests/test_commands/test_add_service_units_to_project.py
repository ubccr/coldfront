from io import StringIO
import sys

from django.core.management import call_command, CommandError

from coldfront.api.allocation.tests.test_allocation_base import TestAllocationBase
from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.allocation.models import Allocation, AllocationAttributeType
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.core.statistics.models import ProjectTransaction, ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware


class TestAddServiceUnitsToProject(TestAllocationBase):
    """Class for testing the management command add_service_units_to_project"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def record_historical_objects_len(self, project):
        """ Records the lengths of all relevant historical objects to a dict"""
        length_dict = {}
        allocation_objects = get_accounting_allocation_objects(project)
        historical_allocation_attribute = \
            allocation_objects.allocation_attribute.history.all()

        length_dict['historical_allocation_attribute'] = \
            len(historical_allocation_attribute)

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name="Service Units")
        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            allocation_user = \
                allocation_objects.allocation.allocationuser_set.get(
                    user=project_user.user)
            allocation_user_attribute = \
                allocation_user.allocationuserattribute_set.get(
                    allocation_attribute_type=allocation_attribute_type,
                    allocation=allocation_objects.allocation)
            historical_allocation_user_attribute = \
                allocation_user_attribute.history.all()

            key = 'historical_allocation_user_attribute_' + project_user.user.username
            length_dict[key] = len(historical_allocation_user_attribute)

        return length_dict

    def allocation_values_test(self, project, value, user_value):
        allocation_objects = get_accounting_allocation_objects(project)
        self.assertEqual(allocation_objects.allocation_attribute.value, value)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue
            allocation_objects = get_accounting_allocation_objects(
                project, user=project_user.user)

            self.assertEqual(allocation_objects.allocation_user_attribute.value,
                             user_value)

    def transactions_created(self, project, pre_time, post_time):
        proj_transaction = ProjectTransaction.objects.get(project=project,
                                                          allocation=2000.0)

        self.assertTrue(pre_time <= proj_transaction.date_time <= post_time)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            proj_user_transaction = ProjectUserTransaction.objects.get(
                project_user=project_user,
                allocation=2000.0)

            self.assertTrue(pre_time <= proj_user_transaction.date_time <= post_time)

    def historical_objects_created(self, pre_length_dict, post_length_dict):
        """Test that historical objects were created"""
        for k, v in pre_length_dict.items():
            self.assertEqual(v + 1, post_length_dict[k])

    def historical_objects_updated(self, project):
        allocation_objects = get_accounting_allocation_objects(project)
        historical_allocation_attribute = \
            allocation_objects.allocation_attribute.history.latest("id")
        historical_reason = historical_allocation_attribute.history_change_reason

        self.assertEqual(historical_reason, 'This is a test for add_service_units command')

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name="Service Units")
        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            allocation_user = \
                allocation_objects.allocation.allocationuser_set.get(
                    user=project_user.user)
            allocation_user_attribute = \
                allocation_user.allocationuserattribute_set.get(
                    allocation_attribute_type=allocation_attribute_type,
                    allocation=allocation_objects.allocation)
            historical_allocation_user_attribute = \
                allocation_user_attribute.history.latest("id")
            historical_reason = \
                historical_allocation_user_attribute.history_change_reason
            self.assertEqual(historical_reason,
                             'This is a test for add_service_units command')

    def test_dry_run(self):
        """Testing add_service_units_to_project dry run"""
        out, err = StringIO(''), StringIO('')
        call_command('add_service_units_to_project',
                     '--project_name=project0',
                     '--amount=1000',
                     '--reason=This is a test for add_service_units command',
                     '--dry_run',
                     stdout=out,
                     stderr=err)
        sys.stdout = sys.__stdout__
        out.seek(0)

        dry_run_message = 'Would add 1000 additional SUs to project ' \
                          'project0. This would increase project0 ' \
                          'SUs from 1000.00 to 2000.00. ' \
                          'The reason for updating SUs for project0 ' \
                          'would be: "This is a test for ' \
                          'add_service_units command".'

        self.assertIn(dry_run_message, out.read())
        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_creates_and_updates_objects(self):
        """Testing add_service_units_to_project dry run"""

        # test allocation values before command
        project = Project.objects.get(name='project0')
        pre_time = utc_now_offset_aware()
        pre_length_dict = self.record_historical_objects_len(project)

        self.allocation_values_test(project, '1000.00', '500.00')

        # run command
        out, err = StringIO(''), StringIO('')
        call_command('add_service_units_to_project',
                     '--project_name=project0',
                     '--amount=1000',
                     '--reason=This is a test for add_service_units command',
                     stdout=out,
                     stderr=err)
        sys.stdout = sys.__stdout__
        out.seek(0)

        message = f'Successfully added 1000 SUs to project0 and its users, ' \
                  f'updating project0\'s SUs from 1000.00 to 2000.00. The ' \
                  f'reason was: "This is a test for add_service_units command".'

        self.assertIn(message, out.read())
        err.seek(0)
        self.assertEqual(err.read(), '')

        post_time = utc_now_offset_aware()

        # test allocation values after command
        self.allocation_values_test(project, '2000.00', '2000.00')

        # test ProjectTransaction created
        self.transactions_created(project, pre_time, post_time)

        # test historical objects created and updated
        post_length_dict = self.record_historical_objects_len(project)
        self.historical_objects_created(pre_length_dict, post_length_dict)
        self.historical_objects_updated(project)

    def test_input_validations(self):
        project = Project.objects.get(name='project1')
        allocation = Allocation.objects.get(project=project)

        # clear resources from allocation
        allocation.resources.clear()
        allocation.refresh_from_db()
        self.assertEqual(allocation.resources.all().count(), 0)

        # add vector compute allocation
        vector_resource = Resource.objects.get(name='Vector Compute')
        allocation.resources.add(vector_resource)
        allocation.save()
        allocation.refresh_from_db()
        self.assertEqual(allocation.resources.all().count(), 1)
        self.assertEqual(allocation.resources.first().name, 'Vector Compute')

        # command should throw a CommandError because the allocation is not
        # part of Savio Compute
        with self.assertRaises(CommandError):
            out, err = StringIO(''), StringIO('')
            call_command('add_service_units_to_project',
                         '--project_name=project1',
                         '--amount=1000',
                         '--reason=This is a test for add_service_units command',
                         stdout=out,
                         stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')
            err.seek(0)
            self.assertEqual(err.read(), '')

        # testing a project that does not exist
        with self.assertRaises(CommandError):
            out, err = StringIO(''), StringIO('')
            call_command('add_service_units_to_project',
                         '--project_name=project555',
                         '--amount=1000',
                         '--reason=This is a test for add_service_units command',
                         stdout=out,
                         stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')
            err.seek(0)
            self.assertEqual(err.read(), '')

        # adding service units that are less than settings.ALLOCATION_MIN
        with self.assertRaises(CommandError):
            out, err = StringIO(''), StringIO('')
            call_command('add_service_units_to_project',
                         '--project_name=project0',
                         '--amount=-1000',
                         '--reason=This is a test for add_service_units command',
                         stdout=out,
                         stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')
            err.seek(0)
            self.assertEqual(err.read(), '')

        # adding service units that are greater than settings.ALLOCATION_MIN
        with self.assertRaises(CommandError):
            out, err = StringIO(''), StringIO('')
            call_command('add_service_units_to_project',
                         '--project_name=project0',
                         '--amount=500000000',
                         '--reason=This is a test for add_service_units command',
                         stdout=out,
                         stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')
            err.seek(0)
            self.assertEqual(err.read(), '')

        # reason is not long enough
        with self.assertRaises(CommandError):
            out, err = StringIO(''), StringIO('')
            call_command('add_service_units_to_project',
                         '--project_name=project0',
                         '--amount=1000',
                         '--reason=notlong',
                         stdout=out,
                         stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')
            err.seek(0)
            self.assertEqual(err.read(), '')
