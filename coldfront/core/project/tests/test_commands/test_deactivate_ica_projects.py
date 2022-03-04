import datetime
from decimal import Decimal

from django.core import mail

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.config import settings
from coldfront.core.allocation.models import AllocationAttributeUsage, \
    AllocationUserAttributeUsage
from coldfront.core.project.models import Project, ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, ProjectUser
from coldfront.core.project.utils import get_project_compute_allocation
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.project.tests.test_commands.test_service_units_base import TestSUBase


class TestDeactivateICAProjects(TestSUBase):
    """Class for testing the management command deactivate_ica_projects"""

    def setUp(self):
        """Set up test data."""
        super().setUp()

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

    def project_allocation_updates(self, project, allocation, pre_time, post_time):
        """Tests that the project and allocation were correctly updated"""
        self.assertEqual(project.status.name, 'Inactive')
        self.assertEqual(allocation.status.name, 'Expired')
        self.assertTrue(pre_time.date() <= allocation.start_date <= post_time.date())
        self.assertTrue(allocation.end_date is None)

    def usage_values_updated(self, project, updated_value):
        """Tests that allocation and allocation user usages are reset"""
        updated_value = Decimal(updated_value)
        allocation_objects = self.get_accounting_allocation_objects(project)
        project_usage = \
            AllocationAttributeUsage.objects.get(
                pk=allocation_objects.allocation_attribute_usage.pk)
        self.assertEqual(project_usage.value, updated_value)

        for project_user in project.projectuser_set.all():
            if project_user.role.name != 'User':
                continue
            allocation_objects = self.get_accounting_allocation_objects(
                project, user=project_user.user)
            user_project_usage = \
                AllocationUserAttributeUsage.objects.get(
                    pk=allocation_objects.allocation_user_attribute_usage.pk)
            self.assertEqual(user_project_usage.value,
                             updated_value)

    def test_dry_run_no_expired_projects(self):
        """Testing a dry run in which no ICA projects are expired"""
        output, error = self.call_command('deactivate_ica_projects',
                                          '--dry_run',
                                          '--send_emails')
        self.assertIn(output, '')
        self.assertEqual(error, '')

    def test_dry_run_with_expired_projects(self):
        """Testing a dry run in which an ICA project is expired"""
        self.create_expired_project('ic_project0')

        output, error = self.call_command('deactivate_ica_projects',
                                          '--dry_run',
                                          '--send_emails')

        project = Project.objects.get(name='ic_project0')
        allocation = get_project_compute_allocation(project)

        # Messages that should be output to stdout during a dry run
        messages = [f'Would update Project {project.name} ({project.pk})\'s '
                    f'status to Inactive and Allocation '
                    f'{allocation.pk}\'s status to Expired.',

                    f'Would reset {project.name} and its users\' SUs from '
                    f'1000.00 to 0.00. The reason '
                    f'would be: "Resetting SUs while deactivating expired '
                    f'ICA project."',

                    'Would send a notification email to 1 user.']

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
        output, error = self.call_command('deactivate_ica_projects')

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

        # test usages are updated
        self.usage_values_updated(project, '0.00')

        # test allocation values after command
        self.allocation_values_test(project, '0.00', '0.00')

        # test ProjectTransaction created
        self.transactions_created(project, pre_time, post_time, 0.00)

        # test historical objects created and updated
        reason = 'Resetting SUs while deactivating expired ICA project.'
        post_length_dict = self.record_historical_objects_len(project)
        self.historical_objects_created(pre_length_dict, post_length_dict)
        self.historical_objects_updated(project, reason)

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
        output, error = self.call_command('deactivate_ica_projects',
                                          '--send_emails')

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
