from coldfront.api.user.tests.test_user_base import TestUserBase
from coldfront.api.user.tests.utils import assert_identity_linking_request_serialization
from coldfront.core.user.models import IdentityLinkingRequest
from coldfront.core.user.models import IdentityLinkingRequestStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware
from http import HTTPStatus

"""A test suite for the /identity_linking_requests/ endpoints, divided
by method."""

SERIALIZER_FIELDS = (
    'id', 'requester', 'request_time', 'completion_time', 'status')
BASE_URL = '/api/identity_linking_requests/'


class TestIdentityLinkingRequestsBase(TestUserBase):
    """A base class for tests of the /identity_linking_requests/
    endpoints."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create four IdentityLinkingRequests: two pending and two complete.
        status_choices = IdentityLinkingRequestStatusChoice.objects.all()
        for i in range(4):
            kwargs = {
                'requester': getattr(self, f'user{i}'),
                'request_time': utc_now_offset_aware(),
            }
            if i < 2:
                kwargs['status'] = status_choices.get(name='Pending')
            else:
                kwargs['status'] = status_choices.get(name='Complete')
                kwargs['completion_time'] = utc_now_offset_aware()
            request = IdentityLinkingRequest.objects.create(**kwargs)
            setattr(self, f'request{i}', request)

        # Run the client as the superuser.
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.superuser_token.key}')


class TestCreateIdentityLinkingRequests(TestIdentityLinkingRequestsBase):
    """A class for testing POST /identity_linking_requests/."""

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
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestDestroyIdentityLinkingRequests(TestIdentityLinkingRequestsBase):
    """A class for testing DELETE /identity_linking_requests/
    {identity_linking_request_id}/."""

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
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestListIdentityLinkingRequests(TestIdentityLinkingRequestsBase):
    """A class for testing GET /identity_linking_requests/."""

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
            (self.user0, False),
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
        self.assertEqual(json['count'], IdentityLinkingRequest.objects.count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            identity_linking_request = IdentityLinkingRequest.objects.get(
                id=result['id'])
            assert_identity_linking_request_serialization(
                identity_linking_request, result, SERIALIZER_FIELDS)

    def test_status_filter(self):
        """Test that querying by status filters results properly."""
        url = BASE_URL
        self.assertEqual(IdentityLinkingRequest.objects.count(), 4)
        for status in ('Pending', 'Complete'):
            query_parameters = {
                'status': status,
            }
            response = self.client.get(url, query_parameters)
            json = response.json()
            self.assertEqual(json['count'], 2)
            for result in json['results']:
                self.assertEqual(result['status'], status)


class TestRetrieveIdentityLinkingRequests(TestIdentityLinkingRequestsBase):
    """A class for testing GET /identity_linking_requests/
    {identity_linking_request_id}/."""

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
            (self.user0, False),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_response_format(self):
        """Test that the response is in the expected format."""
        identity_linking_request = IdentityLinkingRequest.objects.first()
        url = self.pk_url(BASE_URL, identity_linking_request.pk)
        self.assert_retrieve_result_format(url, SERIALIZER_FIELDS)

    def test_valid_pk(self):
        """Test that the response for a valid primary key contains the
        correct values."""
        identity_linking_request = IdentityLinkingRequest.objects.first()
        url = self.pk_url(BASE_URL, identity_linking_request.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        assert_identity_linking_request_serialization(
            identity_linking_request, json, SERIALIZER_FIELDS)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent or unassociated
        primary key raises an error."""
        pk = self.generate_invalid_pk(IdentityLinkingRequest)
        url = self.pk_url(BASE_URL, pk)
        self.assert_retrieve_invalid_response_format(url)


class TestUpdatePatchIdentityLinkingRequests(TestIdentityLinkingRequestsBase):
    """A class for testing PATCH /identity_linking_requests/
    {identity_linking_request_id}/."""

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PATCH'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PATCH'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_read_only_fields_ignored(self):
        """Test that requests that attempt to update read-only fields do
        not update those fields."""
        pre_identity_linking_request = IdentityLinkingRequest.objects.first()
        url = self.pk_url(BASE_URL, pre_identity_linking_request.pk)
        data = {
            'id': pre_identity_linking_request.id + 1,
            'requester': pre_identity_linking_request.requester.id + 1,
            'status': 'Complete',
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        post_identity_linking_request = IdentityLinkingRequest.objects.get(
            id=pre_identity_linking_request.id)
        assert_identity_linking_request_serialization(
            post_identity_linking_request, json, SERIALIZER_FIELDS)

        # 'id', 'requester', and 'request_time' are read-only;
        # 'completion_time' was not changed; 'status' should have changed.
        for field in SERIALIZER_FIELDS:
            pre = getattr(pre_identity_linking_request, field)
            post = getattr(post_identity_linking_request, field)
            if field != 'status':
                self.assertEqual(pre, post)
            else:
                self.assertEqual(pre.name, 'Pending')
                self.assertEqual(post.name, 'Complete')

    def test_valid_data(self):
        """Test that updating an object with valid PATCH data
        succeeds."""
        identity_linking_request = IdentityLinkingRequest.objects.first()
        url = self.pk_url(BASE_URL, identity_linking_request.pk)
        completion_time = utc_now_offset_aware()
        data = {
            'completion_time': completion_time.isoformat(),
            'status': 'Complete',
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        identity_linking_request.refresh_from_db()
        assert_identity_linking_request_serialization(
            identity_linking_request, json, SERIALIZER_FIELDS)

        self.assertEqual(
            identity_linking_request.completion_time, completion_time)
        self.assertEqual(identity_linking_request.status.name, data['status'])

    def test_invalid_data(self):
        """Test that updating an object with invalid PATCH data
        fails."""
        identity_linking_request = IdentityLinkingRequest.objects.first()
        url = self.pk_url(BASE_URL, identity_linking_request.pk)
        data = {
            'completion_time': 'Invalid',
            'status': 'Invalid',
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()
        self.assertIn('completion_time', json)
        self.assertIn('Datetime has wrong format.', json['completion_time'][0])
        self.assertIn('status', json)
        self.assertEqual(
            json['status'], ['Object with name=Invalid does not exist.'])


class TestUpdatePutIdentityLinkingRequests(TestIdentityLinkingRequestsBase):
    """A class for testing PUT /identity_linking_requests/
    {identity_linking_request_id}/."""

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
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)
