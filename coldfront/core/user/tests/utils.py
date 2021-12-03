from django.core.management import call_command
from django.test import TestCase
import os
import sys


class TestUserBase(TestCase):
    """A base class for testing User-related functionality."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        sys.stdout = open(os.devnull, 'w')
        call_command('create_staff_group')
        sys.stdout = sys.__stdout__
