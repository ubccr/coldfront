from http import HTTPStatus

from coldfront.api.billing.tests.test_billing_base import TestBillingBase
from coldfront.api.billing.tests.utils import assert_billing_activity_serialization
from coldfront.core.billing.models import BillingActivity

"""A test suite for the /billing_activities/ endpoints, divided by
method."""

SERIALIZER_FIELDS = ('id', 'billing_project', 'identifier')


class TestBillingActivitiesBase(TestBillingBase):
    """A base class for tests of the /billing_activities/ endpoints."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Run the client as the superuser.
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.superuser_token.key}')


class TestCreateBillingActivities(TestBillingActivitiesBase):
    """A class for testing POST /billing_activities/."""

    def endpoint_url(self):
        """Return the URL for the endpoint."""
        return self.billing_activities_base_url

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.endpoint_url()
        method = 'POST'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.endpoint_url()
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.endpoint_url()
        method = 'POST'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestDestroyBillingActivities(TestBillingActivitiesBase):
    """A class for testing DELETE
    /billing_activities/{billing_activity_id}/."""

    def endpoint_url(self, billing_activity_pk):
        """Return the URL for the endpoint."""
        return f'{self.billing_activities_base_url}{billing_activity_pk}/'

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.endpoint_url('1')
        method = 'DELETE'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.endpoint_url('1')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.endpoint_url('1')
        method = 'DELETE'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestListBillingActivities(TestBillingActivitiesBase):
    """A class for testing GET /billing_activities/."""

    def endpoint_url(self):
        """Return the URL for the endpoint."""
        return self.billing_activities_base_url

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.endpoint_url()
        method = 'GET'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.endpoint_url()
        method = 'GET'
        users = [
            (self.user0, False),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_response_format(self):
        """Test that the response is in the expected format."""
        url = self.endpoint_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        expected_fields = ['count', 'next', 'previous', 'results']
        self.assertEqual(sorted(json.keys()), expected_fields)
        for result in json['results']:
            self.assertEqual(len(result), len(SERIALIZER_FIELDS))
            for field in SERIALIZER_FIELDS:
                self.assertIn(field, result)

    def test_result_order(self):
        """Test that the results are sorted by ID in ascending order."""
        url = self.endpoint_url()
        response = self.client.get(url)
        json = response.json()
        self.assertGreaterEqual(json['count'], 2)
        previous = json['results'][0]['id']
        for i in range(1, len(json['results'])):
            current = json['results'][i]['id']
            self.assertGreater(current, previous)
            previous = current

    def test_no_filters(self):
        """Test that all results are returned when no query filters are
        provided."""
        url = self.endpoint_url()
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(json['count'], BillingActivity.objects.count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            billing_activity = BillingActivity.objects.get(id=result['id'])
            assert_billing_activity_serialization(
                billing_activity, result, SERIALIZER_FIELDS)


class TestRetrieveBillingActivities(TestBillingActivitiesBase):
    """A class for testing GET
    /billing_activities/{billing_activity_id}/."""

    def endpoint_url(self, billing_activity_pk):
        """Return the URL for the endpoint."""
        return f'{self.billing_activities_base_url}{billing_activity_pk}/'

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.endpoint_url('1')
        method = 'GET'
        self.assert_authorization_token_required(url, method)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.endpoint_url('1')
        method = 'GET'
        users = [
            (self.user0, False),
            (self.staff_user, True),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)

    def test_response_format(self):
        """Test that the response is in the expected format."""
        billing_activity = BillingActivity.objects.first()
        url = self.endpoint_url(billing_activity.pk)
        self.assert_retrieve_result_format(url, SERIALIZER_FIELDS)

    def test_valid_pk(self):
        """Test that the response for a valid primary key has the
        expected format."""
        billing_activity = BillingActivity.objects.first()
        url = self.endpoint_url(billing_activity.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        self.assertEqual(len(json), len(SERIALIZER_FIELDS))
        for field in SERIALIZER_FIELDS:
            self.assertIn(field, json)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent primary key raises
        an error."""
        pk = sum(BillingActivity.objects.values_list('pk', flat=True)) + 1
        url = self.endpoint_url(pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Not found.')


class TestUpdatePatchBillingActivities(TestBillingActivitiesBase):
    """A class for testing PATCH /billing_activities/
    {billing_activity_id}/."""

    def endpoint_url(self, billing_activity_pk):
        """Return the URL for the endpoint."""
        return f'{self.billing_activities_base_url}{billing_activity_pk}/'

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.endpoint_url('1')
        method = 'PATCH'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.endpoint_url('1')
        response = self.client.patch(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.endpoint_url('1')
        method = 'PATCH'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)


class TestUpdatePutBillingActivities(TestBillingActivitiesBase):
    """A class for testing PUT /billing_activities/
    {billing_activity_id}/."""

    def endpoint_url(self, billing_activity_pk):
        """Return the URL for the endpoint."""
        return f'{self.billing_activities_base_url}{billing_activity_pk}/'

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.endpoint_url('1')
        method = 'PUT'
        self.assert_authorization_token_required(url, method)

    def test_method_not_allowed(self):
        """Test that this method is not allowed."""
        url = self.endpoint_url('1')
        response = self.client.put(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_permissions_by_role(self):
        """Test permissions for regular users, staff, and superusers."""
        url = self.endpoint_url('1')
        method = 'PUT'
        users = [
            (self.user0, False),
            (self.staff_user, False),
            (self.superuser, True)
        ]
        self.assert_permissions_by_user(url, method, users)
