from coldfront.core.user.models import ExpiringToken
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient
import os
import sys


class TestAPIBase(TestCase):
    """A base class for testing the API."""

    def setUp(self):
        """Set up test data."""
        # Create initial, required database objects.
        sys.stdout = open(os.devnull, 'w')
        call_command('import_field_of_science_data')
        call_command('add_default_project_choices')
        call_command('add_resource_defaults')
        call_command('add_allocation_defaults')
        call_command('add_brc_accounting_data')
        sys.stdout = sys.__stdout__

        # Create a test client with authorization.
        self.client = APIClient()
        staff_user = User.objects.create(
            username='staff', email='staff@nonexistent.com', is_staff=True)
        self.token = ExpiringToken.objects.create(user=staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
