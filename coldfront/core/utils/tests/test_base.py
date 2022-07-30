from copy import deepcopy
from http import HTTPStatus
from io import StringIO
import os
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.test import Client
from django.test import override_settings
from django.test import TestCase
from django.test.utils import TestContextDecorator

from flags.state import disable_flag
from flags.state import enable_flag
from flags.state import flag_enabled

from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.utils.common import utc_now_offset_aware


# TODO: Because FLAGS is set directly in settings, the disable_flag method has
# TODO: no effect. A better approach is to have a dedicated test_settings
# TODO: module that is used exclusively for testing.
FLAGS_COPY = deepcopy(settings.FLAGS)
FLAGS_COPY.pop('LRC_ONLY')


@override_settings(FLAGS=FLAGS_COPY, PRIMARY_CLUSTER_NAME='Savio')
class TestBase(TestCase):
    """A base class for testing the application."""

    # A password for convenient reference.
    password = 'password'

    def setUp(self):
        """Set up test data."""
        self.call_setup_commands()
        self.client = Client()

    def assert_has_access(self, url, user, has_access=True,
                          expected_messages=[]):
        """Assert that the given user has or does not have access to the
        given URL. Optionally, assert that the given messages were sent
        to the user.

        This method assumes that all users have their passwords set to
        self.password. It logs the user in and out.
        """
        self.client.login(username=user.username, password=self.password)
        status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
        response = self.client.get(url)
        if expected_messages:
            actual_messages = self.get_message_strings(response)
            for message in expected_messages:
                self.assertIn(message, actual_messages)
        self.assertEqual(response.status_code, status_code)
        self.client.logout()

    @staticmethod
    def call_setup_commands():
        """Call the management commands that load required database
        objects."""
        # Run the setup commands with the BRC_ONLY flag enabled.
        # TODO: Implement a long-term solution that enables testing of multiple
        # TODO: types of deployments.
        enable_flag('BRC_ONLY', create_boolean_condition=True)
        enable_flag('SERVICE_UNITS_PURCHASABLE', create_boolean_condition=True)

        out, err = StringIO(), StringIO()
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'add_accounting_defaults',
            'add_allowance_defaults',
            'create_allocation_periods',
            # This command calls 'print', whose output must be suppressed.
            'import_field_of_science_data',
            'add_default_project_choices',
            'create_staff_group',
            'add_default_user_choices',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

    @staticmethod
    def create_active_project_with_pi(project_name, pi_user):
        """Create an 'Active' Project with the given name and the given
        user as its PI. Return the Project."""
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=pi_user)
        return project

    def create_test_user(self):
        """Create a User with username 'test_user' and set this
        instance's 'user' attribute to it."""
        self.user = User.objects.create(
            email='test_user@email.com',
            first_name='Test',
            last_name='User',
            username='test_user')
        self.user.set_password(self.password)
        self.user.save()
        return self.user

    @staticmethod
    def get_fca_computing_allowance():
        """Return the FCA Resource."""
        return Resource.objects.get(name=BRCAllowances.FCA)

    @staticmethod
    def get_message_strings(response):
        """Return messages included in the given response as a list of
        strings."""
        return [str(m) for m in get_messages(response.wsgi_request)]

    @staticmethod
    def sign_user_access_agreement(user):
        """Simulate the given User signing the access agreement at the
        current time."""
        user_profile = user.userprofile
        user_profile.access_agreement_signed_date = utc_now_offset_aware()
        user_profile.save()


class enable_deployment(TestContextDecorator):
    """A class that enables the deployment with the given name and
    disables the other, and then reverts to the previous states when
    done. It may be used as a context manager or as a decorator.

    Modeled after django.test.utils.override_settings.

    WARNING: Decorating a class does not produce the expected results.
    """

    def __init__(self, deployment_name):
        assert deployment_name in ('BRC', 'LRC')
        self._deployment_name = deployment_name
        super().__init__()

        if self._deployment_name == 'BRC':
            self._flag_to_enable = 'BRC_ONLY'
            self._flag_to_disable = 'LRC_ONLY'
        else:
            self._flag_to_enable = 'LRC_ONLY'
            self._flag_to_disable = 'BRC_ONLY'

        self._pre_states = {
            flag_name: flag_enabled(flag_name) or False
            for flag_name in ('BRC_ONLY', 'LRC_ONLY')}

        self._override_settings_cm = None

    def enable(self):
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy[self._flag_to_enable] = {
            'condition': 'boolean', 'value': True}
        flags_copy[self._flag_to_disable] = {
            'condition': 'boolean', 'value': False}

        self._override_settings_cm = override_settings(FLAGS=flags_copy)
        self._override_settings_cm.__enter__()

        enable_flag(self._flag_to_enable)
        disable_flag(self._flag_to_disable)
        assert flag_enabled(self._flag_to_enable)
        assert not flag_enabled(self._flag_to_disable)

    def disable(self):
        for flag_name, pre_state in self._pre_states.items():
            if pre_state:
                enable_flag(flag_name)
            else:
                disable_flag(flag_name)

        if self._override_settings_cm is not None:
            self._override_settings_cm.__exit__(None, None, None)

        for flag_name in self._pre_states:
            assert flag_enabled(flag_name) == self._pre_states[flag_name]
