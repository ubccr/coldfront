from http import HTTPStatus

from django.contrib.messages import get_messages
from django.urls import reverse

from coldfront.core.project.forms import ProjectReviewUserJoinForm
from coldfront.core.project.models import *
from coldfront.core.user.models import UserProfile
from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from coldfront.core.utils.common import utc_now_offset_aware
from django.conf import settings

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

        self.password = 'password'

        # Create a requester user and multiple PI users.
        self.user1 = User.objects.create(
            email='user1@email.com',
            first_name='Normal',
            last_name='User1',
            username='user1')
        self.user1.set_password(self.password)
        self.user1.save()

        self.pi1 = User.objects.create(
            email='pi1@email.com',
            first_name='Pi1',
            last_name='User',
            username='pi1')
        self.pi1.set_password(self.password)
        self.pi1.save()
        user_profile = UserProfile.objects.get(user=self.pi1)
        user_profile.is_pi = True
        user_profile.save()

        self.manager1 = User.objects.create(
            email='manager1@email.com',
            first_name='Manager1',
            last_name='User',
            username='manager1')
        self.manager1.set_password(self.password)
        self.manager1.save()

        for user in [self.user1, self.pi1, self.manager1]:
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
        ProjectUser.objects.create(
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

        # add user1 with Pending - Add status
        project_user = ProjectUser.objects.create(
            user=self.user1,
            project=self.project1,
            role=user_project_role,
            status=pending_project_user_status)

        request = \
            ProjectUserJoinRequest.objects.create(project_user=project_user)
        request.created = datetime.datetime.now() - datetime.timedelta(days=4)
        request.save()

        # Clear the mail outbox.
        mail.outbox = []

    def test_command(self):
        """
        Testing pending_join_request_reminder command
        """
        out, err = StringIO(), StringIO()
        sys.stdout = open(os.devnull, 'w')
        call_command('pending_join_request_reminder', stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        email_to_managers = [proj_user.user.email for proj_user in
                             self.project1.projectuser_set.filter(
                                 role__name__in=['Manager', 'Principal Investigator'],
                                 status__name='Active')]

        email_body_user = f'This is a reminder that you have requested to ' \
                          f'join project {self.project1.name} via MyBRC ' \
                          f'user portal. You will periodically receive ' \
                          f'reminder emails until the managers/PIs of ' \
                          f'{self.project1.name} approve/deny this request.'

        email_body_manager = f'This is a reminder that user ' \
                             f'{self.user1.first_name} {self.user1.last_name} ' \
                             f'({self.user1.email}) has requested to join your ' \
                             f'project, {self.project1.name} via MyBRC user ' \
                             f'portal. Please approve/deny this request. ' \
                             f'You will periodically receive reminder emails ' \
                             f'until you approve/deny this request.'

        for email in mail.outbox:
            for addr in email.to:
                if addr in email_to_managers:
                    self.assertIn(email_body_manager, email.body)
                elif addr == self.user1.email:
                    self.assertIn(email_body_user, email.body)
                else:
                    self.fail('Email not sent to either the user '
                              'or managers/PIs of project')

            self.assertEqual(settings.EMAIL_SENDER, email.from_email)