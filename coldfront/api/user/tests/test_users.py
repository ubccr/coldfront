from coldfront.api.user.tests.test_user_base import TestUserBase
from coldfront.api.user.tests.utils import assert_user_serialization
from django.contrib.auth.models import User
from http import HTTPStatus

"""A test suite for the /users/ endpoints, divided by method."""

SERIALIZER_FIELDS = ('id', 'username', 'first_name', 'last_name', 'email')
BASE_URL = '/api/users/'


class TestUsersBase(TestUserBase):
    """A base class for tests of the /users/ endpoints."""

    def setUp(self):
        """Set up test data."""
        super().setUp()


class TestCreateUsers(TestUsersBase):
    """A class for testing POST /users/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = BASE_URL
        method = 'POST'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = BASE_URL
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = BASE_URL
        method = 'POST'
        users = [
            (self.user0, True),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestDestroyUsers(TestUsersBase):
    """A class for testing DELETE /users/{userid}/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'DELETE'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.pk_url(BASE_URL, '1')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'DELETE'
        users = [
            (self.user0, True),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestListUsers(TestUsersBase):
    """A class for testing GET /users/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = BASE_URL
        method = 'GET'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = BASE_URL
        method = 'GET'
        users = [
            (self.user0, True),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_result_order(self):
        """Test that the results are sorted by ID in ascending order."""
        url = BASE_URL
        self.assert_result_order(url, 'id', ascending=True)

    def test_no_filters(self):
        """Test that all results are returned when no query filters are
        provided."""
        url = BASE_URL
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json['count'], User.objects.count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            user = User.objects.get(id=result['id'])
            assert_user_serialization(user, result, SERIALIZER_FIELDS)


class TestRetrieveUsers(TestUsersBase):
    """A class for testing GET /users/{user_id}/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'GET'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'GET'
        users = [
            (self.user0, True),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_response_format(self):
        """Test that the response is in the expected format."""
        user = User.objects.first()
        url = self.pk_url(BASE_URL, user.pk)
        self.assert_retrieve_result_format(url, SERIALIZER_FIELDS)

    def test_valid_pk(self):
        """Test that the response for a valid primary key contains the
        correct values."""
        user = User.objects.first()
        url = self.pk_url(BASE_URL, user.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        assert_user_serialization(user, json, SERIALIZER_FIELDS)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent or unassociated
        primary key raises an error."""
        pk = self.generate_invalid_pk(User)
        url = self.pk_url(BASE_URL, pk)
        self.assert_retrieve_invalid_response_format(url)


class TestUpdatePatchUsers(TestUsersBase):
    """A class for testing PATCH /users/{user_id}/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PATCH'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.pk_url(BASE_URL, '1')
        response = self.client.patch(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PATCH'
        users = [
            (self.user0, True),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestUpdatePutUsers(TestUsersBase):
    """A class for testing PUT /users/{user_id}/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PUT'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.pk_url(BASE_URL, '1')
        response = self.client.put(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PUT'
        users = [
            (self.user0, True),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)
