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

    def historical_objects_updated(self, project):
        allocation_objects = get_accounting_allocation_objects(project)
        historical_allocation_attribute = \
            allocation_objects.allocation_attribute.history.latest("id")
        historical_reason = historical_allocation_attribute.history_change_reason

        self.assertEqual(historical_reason, 'This is a test')

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
            self.assertEqual(historical_reason, 'This is a test')

    def test_dry_run(self):
        """Testing add_service_units_to_project dry run"""
        out, err = StringIO(''), StringIO('')
        call_command('add_service_units_to_project',
                     '--project=project0',
                     '--amount=1000',
                     '--reason=This is a test',
                     '--dry_run',
                     stdout=out,
                     stderr=err)
        sys.stdout = sys.__stdout__
        out.seek(0)

        dry_run_message = 'Would add 1000 additional SUs to project ' \
                          'project0. This would increase project0 ' \
                          'SUs from 1000.00 to 2000.00. ' \
                          'The reason for updating SUs for project0 ' \
                          'would be: This is a test.'

        self.assertIn(dry_run_message, out.read())
        err.seek(0)
        self.assertEqual(err.read(), '')

    def test_command(self):
        """Testing add_service_units_to_project dry run"""

        # test allocation values before command
        project = Project.objects.get(name='project0')
        pre_time = utc_now_offset_aware()

        self.allocation_values_test(project, '1000.00', '500.00')

        # run command
        out, err = StringIO(''), StringIO('')
        call_command('add_service_units_to_project',
                     '--project=project0',
                     '--amount=1000',
                     '--reason=This is a test',
                     stdout=out,
                     stderr=err)
        sys.stdout = sys.__stdout__
        out.seek(0)

        message = "Successfully added 1000 SUs to project0" \
                  ", updating project0's SUs from " \
                  "1000.00 to 2000.00."

        self.assertIn(message, out.read())
        err.seek(0)
        self.assertEqual(err.read(), '')

        post_time = utc_now_offset_aware()

        # test allocation values after command
        self.allocation_values_test(project, '2000.00', '2000.00')

        # test ProjectTransaction created
        self.transactions_created(project, pre_time, post_time)

        # test historical objects updated
        self.historical_objects_updated(project)

    def test_non_savio_compute(self):
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
                         '--project=project1',
                         '--amount=1000',
                         '--reason=This is a test',
                         stdout=out,
                         stderr=err)
            sys.stdout = sys.__stdout__
            out.seek(0)
            self.assertEqual(out.read(), '')
            err.seek(0)
            self.assertEqual(err.read(), '')
