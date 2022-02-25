from coldfront.core.project.models import *
from coldfront.core.user.models import UserProfile
from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from coldfront.core.utils.common import utc_now_offset_aware
from django.conf import settings
from django.db.models import Q

from io import StringIO
import os
import sys


class TestPendingJoinRequestReminderCommand(TestCase):
    """
    Base Class for testing
    """

    def setUp(self):
        """Set up test data."""

        out, err = StringIO(), StringIO()
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'import_field_of_science_data',
            'add_default_project_choices',
            'create_staff_group',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        # Create a requester user and multiple PI users.
        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')

        self.user2 = User.objects.create(
            email='user2@email.com',
            first_name='Normal',
            last_name='User2',
            username='user2')

        self.pi1 = User.objects.create(
            email='pi1@email.com',
            first_name='Pi1',
            last_name='User',
            username='pi1')
        user_profile = UserProfile.objects.get(user=self.pi1)
        user_profile.is_pi = True
        user_profile.save()

        self.manager1 = User.objects.create(
            email='manager1@email.com',
            first_name='Manager1',
            last_name='User',
            username='manager1')

        for user in [self.user1, self.user2, self.pi1, self.manager1]:
            user_profile = UserProfile.objects.get(user=user)
            user_profile.access_agreement_signed_date = utc_now_offset_aware()
            user_profile.save()

        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        pending_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Pending - Add')

        pi_project_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        manager_project_role = ProjectUserRoleChoice.objects.get(
            name='Manager')
        user_project_role = ProjectUserRoleChoice.objects.get(
            name='User')

        # Create Projects.
        self.project1 = Project.objects.create(
            name='project1', status=active_project_status)

        # add pis
        self.pi_proj_user = ProjectUser.objects.create(
            project=self.project1,
            user=self.pi1,
            role=pi_project_role,
            status=active_project_user_status)

        # add manager1
        ProjectUser.objects.create(
            project=self.project1,
            user=self.manager1,
            role=manager_project_role,
            status=active_project_user_status)

        # add user1 and user2 with Pending - Add status
        project_user = ProjectUser.objects.create(
            user=self.user1,
            project=self.project1,
            role=user_project_role,
            status=pending_project_user_status)

        project_user2 = ProjectUser.objects.create(
            user=self.user2,
            project=self.project1,
            role=user_project_role,
            status=pending_project_user_status)

        self.request1 = \
            ProjectUserJoinRequest.objects.create(project_user=project_user)

        self.request2 = \
            ProjectUserJoinRequest.objects.create(project_user=project_user2)

        # Clear the mail outbox.
        mail.outbox = []

    @staticmethod
    def manager_pi_message_body(num_requests, project_name):
        """Return the message the email sent to the managers and PIs
        should contain, given an integer number of requests and the name
        of the project."""
        verb = 'are' if num_requests > 1 else 'is'
        return (
            f'This is a reminder that there {verb} {num_requests} request(s) '
            f'to join your project, {project_name}, via the MyBRC User '
            f'Portal.')

    @staticmethod
    def user_message_body(num_requests):
        """Return the message the email sent to the user should contain,
        given an integer number of requests."""
        return (
            f'This is a reminder that you have {num_requests} project join '
            f'request(s) in the MyBRC User Portal.')

    def test_command_single_proj_multiple_requests(self):
        """
        Testing pending_join_request_reminder command with a single project,
        multiple managers and PIs, multiple join requests
        """
        out, err = StringIO(), StringIO()
        sys.stdout = open(os.devnull, 'w')
        call_command('pending_join_request_reminder', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        manager_emails = self.project1.managers_and_pis_emails()

        for email in mail.outbox:
            for addr in email.to:
                if addr in manager_emails:
                    body = self.manager_pi_message_body(2, self.project1.name)
                    self.assertIn(body, email.body)

                    for request in [self.request1, self.request2]:
                        request_list = f'{request.project_user.user.first_name} ' \
                                       f'{request.project_user.user.last_name} | ' \
                                       f'{request.project_user.user.email} | ' \
                                       f'{request.created.strftime("%m/%d/%Y, %H:%M")}'
                        self.assertIn(request_list, email.body)

                elif addr == self.user1.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request1.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    body = self.user_message_body(1)
                    self.assertIn(body, email.body)
                elif addr == self.user2.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request2.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    body = self.user_message_body(1)
                    self.assertIn(body, email.body)

                else:
                    self.fail('Email not sent to either the user '
                              'or managers/PIs of project')

            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_command_single_proj_multiple_requests_pi_no_notifications(self):
        """
        Testing pending_join_request_reminder command with a single project,
        single manager because PI has enable_notifications == False,
        multiple join requests
        """
        self.pi_proj_user.enable_notifications = False
        self.pi_proj_user.save()

        out, err = StringIO(), StringIO()
        sys.stdout = open(os.devnull, 'w')
        call_command('pending_join_request_reminder', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        manager_emails = self.project1.managers_and_pis_emails()

        for email in mail.outbox:
            for addr in email.to:
                if addr in manager_emails:
                    body = self.manager_pi_message_body(2, self.project1.name)
                    self.assertIn(body, email.body)

                    for request in [self.request1, self.request2]:
                        request_list = f'{request.project_user.user.first_name} ' \
                                       f'{request.project_user.user.last_name} | ' \
                                       f'{request.project_user.user.email} | ' \
                                       f'{request.created.strftime("%m/%d/%Y, %H:%M")}'
                        self.assertIn(request_list, email.body)

                elif addr == self.user1.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request1.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    body = self.user_message_body(1)
                    self.assertIn(body, email.body)
                elif addr == self.user2.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request2.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    body = self.user_message_body(1)
                    self.assertIn(body, email.body)

                else:
                    self.fail('Email not sent to either the user '
                              'or managers/PIs of project')

            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_command_two_proj_multiple_requests(self):
        """
        Testing pending_join_request_reminder command with a two projects,
        multiple join requests
        """
        active_project_status = ProjectStatusChoice.objects.get(name='Active')

        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        pending_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Pending - Add')

        pi_project_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')

        user_project_role = ProjectUserRoleChoice.objects.get(
            name='User')

        # Create Projects.
        project2 = Project.objects.create(
            name='project2', status=active_project_status)

        # add pis
        pi_proj_user2 = ProjectUser.objects.create(
            project=project2,
            user=self.pi1,
            role=pi_project_role,
            status=active_project_user_status)

        # add user1 with Pending - Add status
        project_user2 = ProjectUser.objects.create(
            user=self.user1,
            project=project2,
            role=user_project_role,
            status=pending_project_user_status)

        request3 = \
            ProjectUserJoinRequest.objects.create(project_user=project_user2)

        out, err = StringIO(), StringIO()
        sys.stdout = open(os.devnull, 'w')
        call_command('pending_join_request_reminder', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        manager_emails1 = self.project1.managers_and_pis_emails()

        for email in mail.outbox:
            for addr in email.to:
                if addr in manager_emails1:
                    try:
                        body = self.manager_pi_message_body(
                            2, self.project1.name)
                        self.assertIn(body, email.body)

                        for request in [self.request1, self.request2]:
                            request_list = f'{request.project_user.user.first_name} ' \
                                           f'{request.project_user.user.last_name} | ' \
                                           f'{request.project_user.user.email} | ' \
                                           f'{request.created.strftime("%m/%d/%Y, %H:%M")}'
                            self.assertIn(request_list, email.body)
                    except:
                        body = self.manager_pi_message_body(1, project2.name)
                        self.assertIn(body, email.body)

                        request_list = f'{request3.project_user.user.first_name} ' \
                                       f'{request3.project_user.user.last_name} | ' \
                                       f'{request3.project_user.user.email} | ' \
                                       f'{request3.created.strftime("%m/%d/%Y, %H:%M")}'
                        self.assertIn(request_list, email.body)

                elif addr == self.user1.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request1.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)
                    request_list = f'{project2.name} | ' \
                                   f'{request3.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    body = self.user_message_body(2)
                    self.assertIn(body, email.body)

                elif addr == self.user2.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request2.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    body = self.user_message_body(1)
                    self.assertIn(body, email.body)

                else:
                    self.fail('Email not sent to either the user '
                              'or managers/PIs of project')

            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_command_previously_denied_requests(self):
        """
        Testing pending_join_request_reminder command when a user has a
        previously denied join request
        """
        # represents a denied request
        proj_user = ProjectUser.objects.get(user=self.user1, project=self.project1)
        request4 = \
            ProjectUserJoinRequest.objects.create(project_user=proj_user)
        request4.created = utc_now_offset_aware() - datetime.timedelta(days=4)
        request4.save()

        out, err = StringIO(), StringIO()
        sys.stdout = open(os.devnull, 'w')
        call_command('pending_join_request_reminder', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        manager_emails = self.project1.managers_and_pis_emails()

        for email in mail.outbox:
            for addr in email.to:
                if addr in manager_emails:
                    body = self.manager_pi_message_body(2, self.project1.name)
                    self.assertIn(body, email.body)

                    for request in [self.request1, self.request2]:
                        request_list = f'{request.project_user.user.first_name} ' \
                                       f'{request.project_user.user.last_name} | ' \
                                       f'{request.project_user.user.email} | ' \
                                       f'{request.created.strftime("%m/%d/%Y, %H:%M")}'
                        self.assertIn(request_list, email.body)

                    request_list = f'{request4.project_user.user.first_name} ' \
                                   f'{request4.project_user.user.last_name} | ' \
                                   f'{request4.project_user.user.email} | ' \
                                   f'{request4.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertNotIn(request_list, email.body)

                elif addr == self.user1.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request1.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    request_list = f'{request4.project_user.user.first_name} ' \
                                   f'{request4.project_user.user.last_name} | ' \
                                   f'{request4.project_user.user.email} | ' \
                                   f'{request4.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertNotIn(request_list, email.body)

                    body = self.user_message_body(1)
                    self.assertIn(body, email.body)

                elif addr == self.user2.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request2.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    body = self.user_message_body(1)
                    self.assertIn(body, email.body)

                else:
                    self.fail('Email not sent to either the user '
                              'or managers/PIs of project')

            self.assertEqual(settings.EMAIL_SENDER, email.from_email)