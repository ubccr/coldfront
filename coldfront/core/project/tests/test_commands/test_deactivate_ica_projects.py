import datetime
from decimal import Decimal
from io import StringIO
import sys

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.db.models import Q

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation, AccountingAllocationObjects, \
    get_accounting_allocation_objects
from coldfront.config import settings
from coldfront.core.allocation.models import Allocation, \
    AllocationAttributeType, AllocationAttribute, \
    AllocationAttributeUsage, AllocationUserStatusChoice, AllocationUser, \
    AllocationUserAttribute, AllocationUserAttributeUsage
from coldfront.core.project.models import Project, ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, ProjectUser
from coldfront.core.project.utils import get_project_compute_allocation
from coldfront.core.statistics.models import ProjectTransaction, ProjectUserTransaction
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestDeactivateICAProjects(TestBase):
    """Class for testing the management command deactivate_ica_projects"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a PI.
        self.pi = User.objects.create(
            username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        # Create two Users.
        for i in range(2):
            user = User.objects.create(
                username=f'user{i}', email=f'user{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=user)
            user_profile.cluster_uid = f'{i}'
            user_profile.save()
            setattr(self, f'user{i}', user)
            setattr(self, f'user_profile{i}', user_profile)

        # Create Projects and associate Users with them.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
        current_date = utc_now_offset_aware()

        for i in range(2):
            # Create an ICA Project and ProjectUsers.
            project = Project.objects.create(
                name=f'ic_project{i}', status=project_status)
            setattr(self, f'ic_project{i}', project)
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

            # Set start and end dates for allocations
            allocation_object = get_project_compute_allocation(project)
            allocation_object.start_date = \
                current_date - datetime.timedelta(days=(i+1)*5)
            allocation_object.end_date = \
                current_date + datetime.timedelta(days=(i+1)*5)
            allocation_object.save()

            # Create a compute allocation for each User on the Project.
            for j in range(2):
                create_user_project_allocation(
                    getattr(self, f'user{j}'), project, allocation / 2)

        # Clear the mail outbox.
        mail.outbox = []

    @staticmethod
    def call_deactivate_command(*args):
        """Call the command with the given arguments, returning the messages
        written to stdout and stderr."""
        out, err = StringIO(), StringIO()
        args = ['deactivate_ica_projects', *args]
        kwargs = {'stdout': out, 'stderr': err}
        call_command(*args, **kwargs)
        return out.getvalue(), err.getvalue()

    def get_accounting_allocation_objects(self, project, user=None):
        """Return a namedtuple of database objects related to accounting and
        allocation for the given project and optional user.

        Parameters:
            - project (Project): an instance of the Project model
            - user (User): an instance of the User model

        Returns:
            - AccountingAllocationObjects instance

        Raises:
            - MultipleObjectsReturned, if a database retrieval returns more
            than one object
            - ObjectDoesNotExist, if a database retrieval returns less than
            one object
            - TypeError, if one or more inputs has the wrong type

        NOTE: this function was taken from coldfront.core.statistics.utils.
        This version does not check that the allocation status is Active
        """
        if not isinstance(project, Project):
            raise TypeError(f'Project {project} is not a Project object.')

        objects = AccountingAllocationObjects()

        allocation = Allocation.objects.get(
            project=project, resources__name='Savio Compute')

        # Check that the allocation has an attribute for Service Units and
        # an associated usage.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute = AllocationAttribute.objects.get(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation)
        allocation_attribute_usage = AllocationAttributeUsage.objects.get(
            allocation_attribute=allocation_attribute)

        objects.allocation = allocation
        objects.allocation_attribute = allocation_attribute
        objects.allocation_attribute_usage = allocation_attribute_usage

        if user is None:
            return objects

        if not isinstance(user, User):
            raise TypeError(f'User {user} is not a User object.')

        # Check that there is an active association between the user and project.
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        ProjectUser.objects.get(user=user, project=project, status=active_status)

        # Check that the user is an active member of the allocation.
        active_status = AllocationUserStatusChoice.objects.get(name='Active')
        allocation_user = AllocationUser.objects.get(
            allocation=allocation, user=user, status=active_status)

        # Check that the allocation user has an attribute for Service Units
        # and an associated usage.
        allocation_user_attribute = AllocationUserAttribute.objects.get(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation, allocation_user=allocation_user)
        allocation_user_attribute_usage = AllocationUserAttributeUsage.objects.get(
            allocation_user_attribute=allocation_user_attribute)

        objects.allocation_user = allocation_user
        objects.allocation_user_attribute = allocation_user_attribute
        objects.allocation_user_attribute_usage = allocation_user_attribute_usage

        return objects

    def create_expired_project(self, project_name):
        """Change the end date of ic_project0 to be expired"""
        project = Project.objects.get(name=project_name)
        allocation = get_project_compute_allocation(project)
        current_date = utc_now_offset_aware()
        expired_date = (current_date - datetime.timedelta(days=4)).date()

        allocation.end_date = expired_date
        allocation.save()
        allocation.refresh_from_db()
        self.assertEqual(allocation.end_date, expired_date)

    def record_historical_objects_len(self, project):
        """ Records the lengths of all relevant historical objects to a dict"""
        length_dict = {}
        allocation_objects = self.get_accounting_allocation_objects(project)
        historical_allocation_attribute = \
            allocation_objects.allocation_attribute.history.all()

        length_dict['historical_allocation_attribute'] = \
            len(historical_allocation_attribute)

        allocation_attribute_type = AllocationAttributeType.objects.get(
            name="Service Units")
        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            allocation_user_obj = self.get_accounting_allocation_objects(
                project, user=project_user.user)

            historical_allocation_user_attribute = \
                allocation_user_obj.allocation_user_attribute.history.all()

            key = 'historical_allocation_user_attribute_' + project_user.user.username
            length_dict[key] = len(historical_allocation_user_attribute)

        return length_dict

    def allocation_values_test(self, project, value, user_value):
        """
        Tests that the allocation user values are correct
        """
        allocation_objects = self.get_accounting_allocation_objects(project)
        self.assertEqual(allocation_objects.allocation_attribute.value, value)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue
            allocation_objects = self.get_accounting_allocation_objects(
                project, user=project_user.user)

            self.assertEqual(allocation_objects.allocation_user_attribute.value,
                             user_value)

    def transactions_created(self, project, pre_time, post_time, amount):
        """
        Tests that transactions were created for the zeroing of SUs
        """
        proj_transaction = ProjectTransaction.objects.get(project=project,
                                                          allocation=amount)

        self.assertTrue(pre_time <= proj_transaction.date_time <= post_time)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            proj_user_transaction = ProjectUserTransaction.objects.get(
                project_user=project_user,
                allocation=amount)

            self.assertTrue(pre_time <= proj_user_transaction.date_time <= post_time)

    def historical_objects_created(self, pre_length_dict, post_length_dict):
        """Test that historical objects were created"""
        for k, v in pre_length_dict.items():
            self.assertEqual(v + 1, post_length_dict[k])

    def historical_objects_updated(self, project):
        """
        Tests that the relevant historical objects have the correct reason
        """

        reason = 'Resetting SUs while deactivating expired ICA project.'
        allocation_objects = self.get_accounting_allocation_objects(project)

        alloc_attr_hist_reason = \
            allocation_objects.allocation_attribute.history.\
                latest('id').history_change_reason
        self.assertEqual(alloc_attr_hist_reason, reason)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue

            allocation_user_obj = self.get_accounting_allocation_objects(
                project, user=project_user.user)

            alloc_attr_hist_reason = \
                allocation_user_obj.allocation_user_attribute.history. \
                    latest('id').history_change_reason
            self.assertEqual(alloc_attr_hist_reason, reason)

    def project_allocation_updates(self, project, allocation, pre_time, post_time):
        """Tests that the project and allocation were correctly updated"""
        self.assertEqual(project.status.name, 'Inactive')
        self.assertEqual(allocation.status.name, 'Expired')
        self.assertTrue(pre_time.date() <= allocation.start_date <= post_time.date())
        self.assertTrue(allocation.end_date is None)

    def test_dry_run_no_expired_projects(self):
        """Testing a dry run in which no ICA projects are expired"""
        output, error = self.call_deactivate_command('--dry_run',
                                                     '--send_emails')
        self.assertIn(output, '')
        self.assertEqual(error, '')

    def test_dry_run_with_expired_projects(self):
        """Testing a dry run in which an ICA project is expired"""
        self.create_expired_project('ic_project0')

        output, error = self.call_deactivate_command('--dry_run',
                                                     '--send_emails')

        project = Project.objects.get(name='ic_project0')
        allocation = get_project_compute_allocation(project)

        # Messages that should be output to stdout during a dry run
        messages = [f'Would update Project {project.name} ({project.pk})\'s '
                    f'status to Inactive and Allocation '
                    f'{allocation.pk}\'s status to Expired.',

                    f'Would reset {project.name} and its users\'s SUs from '
                    f'1000.00 to 0.00. The reason '
                    f'would be: "Resetting SUs while deactivating expired '
                    f'ICA project."',

                    'Would send the following email to 1 users:',
                    f'Dear managers of {project.name},',

                    f'This is a notification that the project {project.name} '
                    f'expired on {allocation.end_date.strftime("%m-%d-%Y")} '
                    f'and has therefore been deactivated. '
                    f'Accounts under this project will no longer be able '
                    f'to access its compute resources.']

        for message in messages:
            self.assertIn(message, output)

        self.assertEqual(error, '')

    def test_creates_and_updates_objects(self):
        """Testing deactivate_ica_projects WITHOUT send_emails flag"""
        self.create_expired_project('ic_project0')

        project = Project.objects.get(name='ic_project0')
        allocation = get_project_compute_allocation(project)

        pre_time = utc_now_offset_aware()
        pre_length_dict = self.record_historical_objects_len(project)

        # test allocation values before command
        self.allocation_values_test(project, '1000.00', '500.00')

        # run command
        output, error = self.call_deactivate_command()

        messages = [
            f'Updated Project {project.name} ({project.pk})\'s status to '
            f'Inactive and Allocation {allocation.pk}\'s '
            f'status to Expired.',

            f'Successfully reset SUs for {project.name} '
            f'and its users, updating {project.name}\'s SUs from '
            f'1000.00 to 0.00. The reason '
            f'was: "Resetting SUs while deactivating expired ICA '
            f'project.".']

        for message in messages:
            self.assertIn(message, output)
        self.assertEqual(error, '')

        post_time = utc_now_offset_aware()
        project.refresh_from_db()
        allocation.refresh_from_db()

        # test project and allocation statuses
        self.project_allocation_updates(project, allocation, pre_time, post_time)

        # test allocation values after command
        self.allocation_values_test(project, '0.00', '0.00')

        # test ProjectTransaction created
        self.transactions_created(project, pre_time, post_time, 0.00)

        # test historical objects created and updated
        post_length_dict = self.record_historical_objects_len(project)
        self.historical_objects_created(pre_length_dict, post_length_dict)
        self.historical_objects_updated(project)

    def test_emails_sent(self):
        """
        Tests that emails are sent correctly when there is an expired
        ICA project
        """

        self.create_expired_project('ic_project0')

        project = Project.objects.get(name='ic_project0')
        allocation = get_project_compute_allocation(project)
        old_end_date = allocation.end_date

        # run command
        output, error = self.call_deactivate_command('--send_emails')

        recipients = project.managers_and_pis_emails()

        # Testing that the correct text is output to stdout
        message = f'Sent deactivation notification email to ' \
                  f'{len(recipients)} users.'

        self.assertIn(message, output)
        self.assertEqual(error, '')

        # Testing that the correct number of emails were sent
        self.assertEqual(len(mail.outbox), len(recipients))

        email_body = [f'Dear managers of {project.name},',

                      f'This is a notification that the project {project.name} '
                      f'expired on {old_end_date.strftime("%m-%d-%Y")} '
                      f'and has therefore been deactivated. '
                      f'Accounts under this project will no longer be able '
                      f'to access its compute resources.']

        for email in mail.outbox:
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertIn(email.to[0], recipients)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)
