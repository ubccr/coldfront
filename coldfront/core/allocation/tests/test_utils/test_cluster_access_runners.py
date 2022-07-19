from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.core.allocation.models import ClusterAccessRequest, \
    ClusterAccessRequestStatusChoice, AllocationAttributeType, \
    AllocationUserAttribute
from coldfront.core.allocation.utils_.cluster_access_utils import \
    ProjectClusterAccessRequestUpdateRunner, \
    ProjectClusterAccessRequestDenialRunner
from coldfront.core.project.models import ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, ProjectUser, Project
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestClusterAccessRunnersBase(TestBase):
    """A base testing class for cluster access runners."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create User
        self.user0 = User.objects.create(
            username='user0', email=f'user0@nonexistent.com')

        self.manager = User.objects.create(
            username='manager', email='manager@nonexistent.com')

        # Create Projects and associate Users with them.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
        user_role = ProjectUserRoleChoice.objects.get(name='User')

        # Create a Project and ProjectUsers.
        self.project0 = Project.objects.create(
            name='project0', status=project_status)

        ProjectUser.objects.create(
            user=self.user0, project=self.project0,
            role=user_role, status=project_user_status)
        ProjectUser.objects.create(
            user=self.manager, project=self.project0,
            role=manager_role, status=project_user_status)

        # Create a compute allocation for the Project.
        allocation = Decimal('1000.00')
        self.alloc_obj = create_project_allocation(self.project0, allocation)

        # Create a compute allocation for each User on the Project.
        self.alloc_user_obj = create_user_project_allocation(
            self.user0, self.project0, allocation / 2)

        # Create ClusterAccessRequest
        self.request_obj = ClusterAccessRequest.objects.create(
            allocation_user=self.alloc_user_obj.allocation_user,
            status=ClusterAccessRequestStatusChoice.objects.get(
                name='Pending - Add'),
            request_time=utc_now_offset_aware())


class TestProjectClusterAccessRequestUpdateRunner(TestClusterAccessRunnersBase):
    """A testing class for ProjectClusterAccessRequestUpdateRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.runner = ProjectClusterAccessRequestUpdateRunner(self.request_obj)

    def test_update_request(self):
        """Tests update_request functionality."""
        self.assertEqual(self.request_obj.status.name, 'Pending - Add')

        for status in ['Processing', 'Active']:
            self.runner.update_request(status)
            self.request_obj.refresh_from_db()
            self.assertEqual(self.request_obj.status.name, status)

    def test_complete_request(self):
        """Tests complete_request functionality."""
        # Test that values are correct before the runner completes the request.
        cluster_account_status = \
            AllocationAttributeType.objects.get(name='Cluster Account Status')
        cluster_access_attribute = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                allocation=self.alloc_obj.allocation,
                allocation_user=self.alloc_user_obj.allocation_user)
        self.assertFalse(cluster_access_attribute.exists())

        self.alloc_user_obj.allocation_user_attribute.value = Decimal('0.00')
        self.alloc_user_obj.allocation_user_attribute.save()
        self.assertNotEqual(self.alloc_user_obj.allocation_user_attribute.value,
                            self.alloc_obj.allocation_attribute.value)

        self.assertIsNone(self.user0.userprofile.cluster_uid)
        self.assertIsNone(self.request_obj.cluster_uid)
        self.assertIsNone(self.request_obj.username)

        pre_time = utc_now_offset_aware()
        self.assertIsNone(self.request_obj.completion_time)

        new_username = 'new_username'
        self.assertNotEqual(self.user0.username, new_username)

        self.assertEqual(self.request_obj.status.name, 'Pending - Add')

        self.runner.complete_request(new_username, 111, utc_now_offset_aware())

        # give_cluster_access_attribute
        cluster_access_attribute = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                allocation=self.alloc_obj.allocation,
                allocation_user=self.alloc_user_obj.allocation_user,
                value='Active')
        self.assertTrue(cluster_access_attribute.exists())

        # set_username
        self.assertEqual(self.user0.username, new_username)
        self.assertEqual(self.request_obj.username, new_username)

        # set_cluster_uid
        self.assertEqual(self.user0.userprofile.cluster_uid, 111)
        self.assertEqual(self.request_obj.cluster_uid, 111)

        # set_completion_time
        self.assertTrue(pre_time <
                        self.request_obj.completion_time <
                        utc_now_offset_aware())

        # set_user_service_units
        self.alloc_user_obj.allocation_user_attribute.refresh_from_db()
        self.alloc_obj.allocation_attribute.refresh_from_db()
        self.assertEqual(self.alloc_user_obj.allocation_user_attribute.value,
                         self.alloc_obj.allocation_attribute.value)

        self.assertEqual(self.request_obj.status.name, 'Active')

    def test_emails_sent(self):
        """Test that the correct emails are sent."""

        new_username = 'new_username'
        self.runner.complete_request(new_username, 111, utc_now_offset_aware())

        email_body = [f'now has access to the project {self.project0.name}.',
                      f'supercluster username is - {new_username}',
                      f'If this is the first time you are accessing',
                      f'start with the below Logging In page:']

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Cluster Access Activated', email.subject)
        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user0.email])
        self.assertEqual(email.cc, [self.manager.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)


class TestProjectClusterAccessRequestDenialRunner(TestClusterAccessRunnersBase):
    """A testing class for ProjectClusterAccessRequestDenialRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.runner = ProjectClusterAccessRequestDenialRunner(self.request_obj)

    def test_deny_request(self):
        """Tests deny_request functionality."""
        # Test that values are correct before the runner completes the request.
        cluster_account_status = \
            AllocationAttributeType.objects.get(name='Cluster Account Status')
        cluster_access_attribute = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                allocation=self.alloc_obj.allocation,
                allocation_user=self.alloc_user_obj.allocation_user)
        self.assertFalse(cluster_access_attribute.exists())

        pre_time = utc_now_offset_aware()
        self.assertIsNone(self.request_obj.completion_time)

        self.assertEqual(self.request_obj.status.name, 'Pending - Add')

        self.runner.deny_request()

        # give_cluster_access_attribute
        cluster_access_attribute = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                allocation=self.alloc_obj.allocation,
                allocation_user=self.alloc_user_obj.allocation_user,
                value='Denied')
        self.assertTrue(cluster_access_attribute.exists())

        # set_completion_time
        self.assertTrue(pre_time <
                        self.request_obj.completion_time <
                        utc_now_offset_aware())

        self.assertEqual(self.request_obj.status.name, 'Denied')

    def test_emails_sent(self):
        """Test that the correct emails are sent."""

        self.runner.deny_request()

        email_body = [f'access request under project {self.project0.name}',
                      f'and allocation {self.alloc_obj.allocation.pk} '
                      f'has been denied.']

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Cluster Access Denied', email.subject)
        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user0.email])
        self.assertEqual(email.cc, [self.manager.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)
