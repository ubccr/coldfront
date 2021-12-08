from django.contrib.auth.models import User
from django.core.management import call_command
from coldfront.core.utils.common import utc_now_offset_aware
from django.test import Client
from django.test import TestCase
from io import StringIO
import os
import sys


class TestBase(TestCase):
    """A base class for testing the application."""

    # A password for convenient reference.
    password = 'password'

    def setUp(self):
        """Set up test data."""
        out, err = StringIO(), StringIO()
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'add_brc_accounting_defaults',
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

        # Create a test client.
        self.client = Client()

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
    def sign_user_access_agreement(user):
        """Simulate the given User signing the access agreement at the
        current time."""
        user_profile = user.userprofile
        user_profile.access_agreement_signed_date = utc_now_offset_aware()
        user_profile.save()
