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

    def test_command_single_proj_multiple_requests(self):
        """
        Testing pending_join_request_reminder command with a single project,
        multiple managers and PIs, multiple join requests
        """
        out, err = StringIO(), StringIO()
        sys.stdout = open(os.devnull, 'w')
        call_command('pending_join_request_reminder', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        pi_condition = Q(
            role__name='Principal Investigator', status__name='Active',
            enable_notifications=True)
        manager_condition = Q(role__name='Manager', status__name='Active')
        manager_emails = list(
            self.project1.projectuser_set.filter(
                pi_condition | manager_condition
            ).values_list(
                'user__email', flat=True
            ))

        for email in mail.outbox:
            for addr in email.to:
                if addr in manager_emails:
                    body = f'This is a reminder that there are 2 requests(s) ' \
                           f'to join your project, { self.project1.name }, ' \
                           f'via MyBRC user portal.'
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
                elif addr == self.user2.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request2.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

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

        pi_condition = Q(
            role__name='Principal Investigator', status__name='Active',
            enable_notifications=True)
        manager_condition = Q(role__name='Manager', status__name='Active')
        manager_emails = list(
            self.project1.projectuser_set.filter(
                pi_condition | manager_condition
            ).values_list(
                'user__email', flat=True
            ))

        for email in mail.outbox:
            for addr in email.to:
                if addr in manager_emails:
                    body = f'This is a reminder that there are 2 requests(s) ' \
                           f'to join your project, { self.project1.name }, ' \
                           f'via MyBRC user portal.'
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
                elif addr == self.user2.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request2.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

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

        pi_condition = Q(
            role__name='Principal Investigator', status__name='Active',
            enable_notifications=True)
        manager_condition = Q(role__name='Manager', status__name='Active')
        manager_emails1 = list(
            self.project1.projectuser_set.filter(
                pi_condition | manager_condition
            ).values_list(
                'user__email', flat=True
            ))

        manager_emails2 = list(
            project2.projectuser_set.filter(
                pi_condition | manager_condition
            ).values_list(
                'user__email', flat=True
            ))

        for email in mail.outbox:
            for addr in email.to:
                if addr in manager_emails1:
                    try:
                        body = f'This is a reminder that there are 2 requests(s) ' \
                               f'to join your project, { self.project1.name }, ' \
                               f'via MyBRC user portal.'
                        self.assertIn(body, email.body)

                        for request in [self.request1, self.request2]:
                            request_list = f'{request.project_user.user.first_name} ' \
                                           f'{request.project_user.user.last_name} | ' \
                                           f'{request.project_user.user.email} | ' \
                                           f'{request.created.strftime("%m/%d/%Y, %H:%M")}'
                            self.assertIn(request_list, email.body)
                    except:
                        body = f'This is a reminder that there is 1 requests(s) ' \
                               f'to join your project, { project2.name }, ' \
                               f'via MyBRC user portal.'
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

                    body = 'This is a reminder that you have 2' \
                              ' project join request(s).'
                    self.assertIn(body, email.body)

                elif addr == self.user2.email:
                    request_list = f'{self.project1.name} | ' \
                                   f'{self.request2.created.strftime("%m/%d/%Y, %H:%M")}'
                    self.assertIn(request_list, email.body)

                    body = 'This is a reminder that you have 1' \
                              ' project join request(s).'
                    self.assertIn(body, email.body)

                else:
                    self.fail('Email not sent to either the user '
                              'or managers/PIs of project')

            self.assertEqual(settings.EMAIL_SENDER, email.from_email)
