from copy import deepcopy
from http import HTTPStatus
import os
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import override_settings
from django.test import TestCase

from flags.state import enable_flag
from rest_framework.test import APIClient

from coldfront.core.user.models import ExpiringToken


# TODO: Because FLAGS is set directly in settings, the disable_flag method has
# TODO: no effect. A better approach is to have a dedicated test_settings
# TODO: module that is used exclusively for testing.
FLAGS_COPY = deepcopy(settings.FLAGS)
FLAGS_COPY.pop('LRC_ONLY')


@override_settings(FLAGS=FLAGS_COPY, PRIMARY_CLUSTER_NAME='Savio')
class TestAPIBase(TestCase):
    """A base class for testing the API."""

    # A password for convenient reference.
    password = 'password'

    def setUp(self):
        """Set up test data."""
        self.call_setup_commands()
        # Create a test client with authorization.
        self.client = APIClient()
        staff_user = User.objects.create(
            username='staff', email='staff@nonexistent.com', is_staff=True)
        self.token = ExpiringToken.objects.create(user=staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def assert_authorization_token_required(self, url, method):
        """Assert that a request with the given method to the given URL
        requires a valid authorization token."""
        # No credentials.
        self.client = APIClient()
        response = self.send_request(self.client, url, method)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        json = response.json()
        message = 'Authentication credentials were not provided.'
        self.assertEqual(json['detail'], message)

        # Invalid credentials.
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid')
        response = self.send_request(self.client, url, method)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        json = response.json()
        message = 'Invalid token.'
        self.assertEqual(json['detail'], message)

        # Valid credentials.
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.superuser_token.key}')
        response = self.send_request(self.client, url, method)
        self.assertNotEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def assert_permissions_by_user(self, url, method, users):
        """Given a list of tuples of the form (user, boolean), assert
        that each user is not forbidden from making a request with the
        given method to the given URL."""
        for user, not_forbidden in users:
            token_key = getattr(self, f'{user.username}_token').key
            self.client.credentials(HTTP_AUTHORIZATION=f'Token {token_key}')
            response = self.send_request(self.client, url, method)
            if not_forbidden:
                func = self.assertNotEqual
            else:
                func = self.assertEqual
            func(response.status_code, HTTPStatus.FORBIDDEN)

    def assert_result_format(self, result, fields):
        """Given a dictionary representing a single result from the API,
        assert that all of the fields in the given list are in the
        result."""
        self.assertEqual(len(result), len(fields))
        for field in fields:
            self.assertIn(field, result)

    def assert_result_order(self, url, field, ascending=True):
        """Make a GET request to the given URL. Assert that the results
        are sorted in ascending or descending order on the given
        field."""
        response = self.client.get(url)
        json = response.json()
        results = json['results']
        n = len(results)
        self.assertGreaterEqual(n, 2)
        previous = results[0][field]
        for i in range(1, n):
            current = results[i][field]
            if ascending:
                self.assertGreater(current, previous)
            else:
                self.assertLess(current, previous)
            previous = current

    def assert_retrieve_invalid_response_format(self, url):
        """Make a GET request to a URL that contains an invalid primary
        key. Assert that the response code is 404 Not Found and that the
        response has the expected errors."""
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Not found.')

    def assert_retrieve_result_format(self, url, result_fields):
        """Make a GET request to the given URL. Assert that the response
        code is 200 OK and that the response has the expected fields.
        Return the response JSON."""
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        self.assert_result_format(json, result_fields)
        return json

    @staticmethod
    def call_setup_commands():
        """Call the management commands that load required database
        objects."""
        # Run the setup commands with the BRC_ONLY flag enabled.
        # TODO: Implement a long-term solution that enables testing of multiple
        # TODO: types of deployments.
        enable_flag('BRC_ONLY', create_boolean_condition=True)

        # Create initial, required database objects.
        sys.stdout = open(os.devnull, 'w')
        call_command('import_field_of_science_data')
        call_command('add_default_project_choices')
        call_command('add_resource_defaults')
        call_command('add_allocation_defaults')
        call_command('add_accounting_defaults')
        call_command('add_allowance_defaults')
        call_command('create_allocation_periods')
        call_command('create_staff_group')
        sys.stdout = sys.__stdout__

    @staticmethod
    def generate_invalid_pk(model):
        """Return a primary key that belongs to no instance of the given
        model."""
        return sum(model.objects.values_list('pk', flat=True)) + 1

    @staticmethod
    def pk_url(url, pk):
        """Return the URL for a specific primary key."""
        return os.path.join(url, str(pk), '')

    @staticmethod
    def send_request(client, url, method):
        """Use the given client to send a request with the given method
        to the given URL. Return the response."""
        return getattr(client, method.lower())(url)
