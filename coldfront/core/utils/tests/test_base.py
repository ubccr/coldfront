from django.core.management import call_command
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
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        # Create a test client.
        self.client = Client()
