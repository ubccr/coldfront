from decimal import Decimal

from django.core.management import CommandError

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.core.allocation.models import Allocation
from coldfront.core.project.models import Project, ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, ProjectUser
from coldfront.core.project.tests.test_commands.test_service_units_base import \
    TestSUBase
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import utc_now_offset_aware


class TestAddServiceUnitsToProject(TestSUBase):
    """Class for testing the management command add_service_units_to_project"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.reason = 'This is a test for add_service_units command'

        # Create Projects and associate Users with them.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')

        for i in range(2):
            # Create an ICA Project and ProjectUsers.
            project = Project.objects.create(
                name=f'project{i}', status=project_status)
            setattr(self, f'project{i}', project)
            for j in range(2):
                ProjectUser.objects.create(
                    user=getattr(self, f'user{j}'), project=project,
                    role=user_role, status=project_user_status)
            ProjectUser.objects.create(
                user=self.pi, project=project, role=manager_role,
                status=project_user_status)

            # Create a compute allocation for the Project.
            allocation = Decimal(f'{i + 1}000.00')
            create_project_allocation(project, allocation)

            # Create a compute allocation for each User on the Project.
            for j in range(2):
                create_user_project_allocation(
                    getattr(self, f'user{j}'), project, allocation / 2)

    def test_dry_run(self):
        """Testing add_service_units_to_project dry run"""
        output, error = self.call_command('add_service_units_to_project',
                                          '--project_name=project0',
                                          '--amount=1000',
                                          f'--reason={self.reason}',
                                          '--dry_run')

        dry_run_message = 'Would add 1000 additional SUs to project ' \
                          'project0. This would increase project0 ' \
                          'SUs from 1000.00 to 2000.00. ' \
                          'The reason for updating SUs for project0 ' \
                          'would be: "This is a test for ' \
                          'add_service_units command".'

        self.assertIn(dry_run_message, output)
        self.assertEqual(error, '')

    def test_creates_and_updates_objects_positive_SU(self):
        """Testing add_service_units_to_project with positive SUs"""
        # test allocation values before command
        project = Project.objects.get(name='project0')
        pre_time = utc_now_offset_aware()
        pre_length_dict = self.record_historical_objects_len(project)

        self.allocation_values_test(project, '1000.00', '500.00')

        # run command
        output, error = self.call_command('add_service_units_to_project',
                                          '--project_name=project0',
                                          '--amount=1000',
                                          f'--reason={self.reason}')

        message = f'Successfully added 1000 SUs to project0 and its users, ' \
                  f'updating project0\'s SUs from 1000.00 to 2000.00. The ' \
                  f'reason was: "This is a test for add_service_units command".'

        self.assertIn(message, output)
        self.assertEqual(error, '')

        post_time = utc_now_offset_aware()

        # test allocation values after command
        self.allocation_values_test(project, '2000.00', '2000.00')

        # test ProjectTransaction created
        self.transactions_created(project, pre_time, post_time, 2000.00)

        # test historical objects created and updated
        post_length_dict = self.record_historical_objects_len(project)
        self.historical_objects_created(pre_length_dict, post_length_dict)
        self.historical_objects_updated(project, self.reason)

    def test_creates_and_updates_objects_negative_SU(self):
        """Testing add_service_units_to_project with negative SUs"""
        # test allocation values before command
        project = Project.objects.get(name='project0')
        pre_time = utc_now_offset_aware()
        pre_length_dict = self.record_historical_objects_len(project)

        self.allocation_values_test(project, '1000.00', '500.00')

        # run command
        output, error = self.call_command('add_service_units_to_project',
                                          '--project_name=project0',
                                          '--amount=-800',
                                          f'--reason={self.reason}')

        message = f'Successfully added -800 SUs to project0 and its users, ' \
                  f'updating project0\'s SUs from 1000.00 to 200.00. The ' \
                  f'reason was: "This is a test for add_service_units command".'

        self.assertIn(message, output)
        self.assertEqual(error, '')

        post_time = utc_now_offset_aware()

        # test allocation values after command
        self.allocation_values_test(project, '200.00', '200.00')

        # test ProjectTransaction created
        self.transactions_created(project, pre_time, post_time, 200.00)

        # test historical objects created and updated
        post_length_dict = self.record_historical_objects_len(project)
        self.historical_objects_created(pre_length_dict, post_length_dict)
        self.historical_objects_updated(project, self.reason)

    def test_input_validations(self):
        """
        Tests that validate_inputs throws errors in the correct situations
        """
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
            output, error = \
                self.call_command('add_service_units_to_project',
                                  '--project_name=project1',
                                  '--amount=1000',
                                  f'--reason={self.reason}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # testing a project that does not exist
        with self.assertRaises(CommandError):
            output, error = \
                self.call_command('add_service_units_to_project',
                                  '--project_name=project555',
                                  '--amount=1000',
                                  f'--reason={self.reason}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # adding service units that results in allocation having less
        # than settings.ALLOCATION_MIN
        with self.assertRaises(CommandError):
            output, error = \
                self.call_command('add_service_units_to_project',
                                  '--project_name=project0',
                                  '--amount=-100000',
                                  f'--reason={self.reason}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # adding service units that results in allocation having more
        # than settings.ALLOCATION_MAX
        with self.assertRaises(CommandError):
            output, error = \
                self.call_command('add_service_units_to_project',
                                  '--project_name=project0',
                                  '--amount=99999500',
                                  f'--reason={self.reason}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # adding service units that are greater than settings.ALLOCATION_MAX
        with self.assertRaises(CommandError):
            output, error = \
                self.call_command('add_service_units_to_project',
                                  '--project_name=project0',
                                  '--amount=500000000',
                                  f'--reason={self.reason}')
            self.assertEqual(output, '')
            self.assertEqual(error, '')

        # reason is not long enough
        with self.assertRaises(CommandError):
            output, error = \
                self.call_command('add_service_units_to_project',
                                  '--project_name=project0',
                                  '--amount=1000',
                                  '--reason=notlong')
            self.assertEqual(output, '')
            self.assertEqual(error, '')
