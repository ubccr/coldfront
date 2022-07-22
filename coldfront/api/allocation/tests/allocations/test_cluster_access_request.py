from unittest.mock import patch

from django.core import mail

from coldfront.api.allocation.tests.test_allocation_base import \
    TestAllocationBase
from coldfront.api.allocation.tests.utils import \
    assert_cluster_access_request_serialization
from coldfront.config import settings
from coldfront.core.allocation.models import ClusterAccessRequestStatusChoice, \
    AllocationUser, ClusterAccessRequest, AllocationUserAttribute, \
    AllocationAttributeType
from coldfront.core.allocation.utils_.cluster_access_utils import \
    ProjectClusterAccessRequestCompleteRunner, \
    ProjectClusterAccessRequestDenialRunner
from coldfront.core.utils.common import utc_now_offset_aware
from http import HTTPStatus

"""A test suite for the /cluster_access_requests/ endpoints, divided
by method."""

SERIALIZER_FIELDS = (
    'id', 'status', 'completion_time',
    'billing_activity', 'allocation_user')

BASE_URL = '/api/cluster_access_requests/'


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


class TestClusterAccessRequestsBase(TestAllocationBase):
    """A base class for tests of the /cluster_access_requests/
    endpoints."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create two ClusterAccessRequests with statuses Pending - Add,
        # Processing, Active, Denied
        status_choices = ClusterAccessRequestStatusChoice.objects.all()
        for i in range(4):
            kwargs = {
                'allocation_user': AllocationUser.objects.get(user__username=f'user{i}',
                                                              allocation__project__name='project0'),
                'request_time': utc_now_offset_aware(),
            }
            if i == 0:
                kwargs['status'] = status_choices.get(name='Pending - Add')
            elif i == 1:
                kwargs['status'] = status_choices.get(name='Processing')
            elif i == 2:
                kwargs['status'] = status_choices.get(name='Active')
            else:
                kwargs['status'] = status_choices.get(name='Denied')
                
            request = ClusterAccessRequest.objects.create(**kwargs)
            setattr(self, f'request{i}', request)

        self.allocation_user0 = \
            AllocationUser.objects.get(user=self.user0,
                                       allocation__project=self.project0)
        self.new_username = 'new_username'
        self.cluster_uid = '1234'

        # Run the client as the superuser.
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.superuser_token.key}')


class TestListClusterAccessRequests(TestClusterAccessRequestsBase):
    """A class for testing GET /cluster_access_requests/."""

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
        self.assertEqual(json['count'], ClusterAccessRequest.objects.count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            cluster_access_request = \
                ClusterAccessRequest.objects.get(pk=result['id'])
            assert_cluster_access_request_serialization(
                cluster_access_request, result, SERIALIZER_FIELDS)

    def test_status_filter(self):
        """Test that querying by status filters results properly."""
        url = BASE_URL
        self.assertEqual(ClusterAccessRequest.objects.count(), 4)
        for status in ('Pending - Add', 'Processing', 'Active', 'Denied'):
            query_parameters = {
                'status': status,
            }
            response = self.client.get(url, query_parameters)
            json = response.json()
            self.assertEqual(json['count'], 1)
            for result in json['results']:
                self.assertEqual(result['status'], status)


class TestRetrieveClusterAccessRequests(TestClusterAccessRequestsBase):
    """A class for testing GET /cluster_access_requests/
    {cluster_access_request_id}/."""

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
        url = self.pk_url(BASE_URL, self.request0.pk)
        self.assert_retrieve_result_format(url, SERIALIZER_FIELDS)

    def test_valid_pk(self):
        """Test that the response for a valid primary key contains the
        correct values."""
        url = self.pk_url(BASE_URL, self.request0.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        assert_cluster_access_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent or unassociated
        primary key raises an error."""
        pk = self.generate_invalid_pk(ClusterAccessRequest)
        url = self.pk_url(BASE_URL, pk)
        self.assert_retrieve_invalid_response_format(url)


class TestUpdatePatchClusterAccessRequests(TestClusterAccessRequestsBase):
    """A class for testing PATCH /cluster_access_requests/
    {cluster_access_request_id}/."""

    def _get_cluster_account_status_attr(self, allocation_user):
        cluster_account_status = \
            AllocationAttributeType.objects.get(name='Cluster Account Status')
        cluster_access_attribute = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                allocation=allocation_user.allocation,
                allocation_user=allocation_user)
        return cluster_access_attribute

    def _assert_complete_emails_sent(self):
        email_body = [f'now has access to the project {self.project0.name}.',
                      f'supercluster username is - {self.new_username}',
                      f'If this is the first time you are accessing',
                      f'start with the below Logging In page:']

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Cluster Access Activated', email.subject)
        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user0.email])
        self.assertEqual(email.cc, [self.pi.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def _assert_denial_emails_sent(self):
        email_body = [f'access request under project {self.project0.name}',
                      f'and allocation '
                      f'{self.allocation_user0.allocation.pk} '
                      f'has been denied.']

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('Cluster Access Denied', email.subject)
        for section in email_body:
            self.assertIn(section, email.body)
        self.assertEqual(email.to, [self.user0.email])
        self.assertEqual(email.cc, [self.pi.email])
        self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def _refresh_objects(self):
        """Refresh relevant objects from db."""
        self.request0.refresh_from_db()
        self.user0.refresh_from_db()
        # self.alloc_obj.allocation.refresh_from_db()
        # self.alloc_user_obj.allocation_user.refresh_from_db()
        # self.alloc_user_obj.allocation_user_attribute.refresh_from_db()

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self._refresh_objects()
        self.assertEqual(self.request0.status.name, 'Pending - Add')
        self.assertIsNone(self.user0.userprofile.cluster_uid)
        self.assertEqual(self.user0.username, 'user0')
        self.assertIsNone(self.request0.completion_time)
        # self.assertNotEqual(self.alloc_user_obj.allocation_user_attribute.value,
        #                     self.alloc_obj.allocation_attribute.value)
        self.assertFalse(self._get_cluster_account_status_attr(self.allocation_user0).exists())
        self.assertEqual(self.request0.allocation_user.pk, self.allocation_user0.pk)

    def _assert_post_state(self, pre_time, post_time, status, check_username_clusteruid=True):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully."""
        self._refresh_objects()
        self.assertEqual(self.request0.status.name, status)
        self.assertTrue(pre_time < self.request0.completion_time < post_time)
        # self.assertEqual(self.alloc_user_obj.allocation_user_attribute.value,
        #                  self.alloc_obj.allocation_attribute.value)
        self.assertTrue(self._get_cluster_account_status_attr(self.allocation_user0).exists())
        self.assertEqual(self._get_cluster_account_status_attr(self.allocation_user0).first().value,
                         status)
        self.assertEqual(self.request0.allocation_user.pk, self.allocation_user0.pk)

        if check_username_clusteruid:
            self.assertEqual(self.user0.userprofile.cluster_uid, self.cluster_uid)
            self.assertEqual(self.user0.username, self.new_username)

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
        self._assert_pre_state()
        pre_time = utc_now_offset_aware()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'id': self.request0.pk + 1,
            'status': 'Active',
            'completion_time': utc_now_offset_aware(),
            'allocation_user': {'id': 12,
                                'allocation': 3,
                                'user': 'user3',
                                'project': 'project0',
                                'status': 'Active'},
            'username': 'new_username',
            'cluster_uid': '1234'
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        post_time = utc_now_offset_aware()
        self._assert_post_state(pre_time, post_time, data.get('status'))

        assert_cluster_access_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)

        self.assertEqual(data.get('id') - 1, self.request0.pk)
        self.assertNotEqual(data.get('allocation_user').get('id'),
                            self.request0.allocation_user.pk)

        self._assert_complete_emails_sent()

    def test_valid_data_complete(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Active."""
        self._assert_pre_state()
        pre_time = utc_now_offset_aware()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'completion_time': utc_now_offset_aware(),
            'status': 'Active',
            'username': self.new_username,
            'cluster_uid': self.cluster_uid,
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        post_time = utc_now_offset_aware()
        self._assert_post_state(pre_time, post_time, data.get('status'))

        assert_cluster_access_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)
        
        self._assert_complete_emails_sent()

    def test_valid_data_denied(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Active."""
        self._assert_pre_state()
        pre_time = utc_now_offset_aware()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'completion_time': utc_now_offset_aware(),
            'status': 'Denied',
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        post_time = utc_now_offset_aware()
        self._assert_post_state(pre_time, post_time, data.get('status'), False)

        assert_cluster_access_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)

        self._assert_denial_emails_sent()

    def test_valid_data_processing(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Processing."""
        self._assert_pre_state()
        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'status': 'Processing',
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        
        self.request0.refresh_from_db()
        assert_cluster_access_request_serialization(
            self.request0, json, SERIALIZER_FIELDS)

        self.assertIsNone(self.request0.completion_time)
        self.assertEqual(self.request0.status.name, data.get('status'))
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_data(self):
        """Test that updating an object with invalid PATCH data
        fails."""
        self._assert_pre_state()
        
        url = self.pk_url(BASE_URL, self.request0.pk)
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

        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_no_completion_time(self):
        """Test no completion time given when status == Active."""
        self._assert_pre_state()
        url = self.pk_url(BASE_URL, self.request0.pk)

        data = {
            'status': 'Active',
            'username': 'new_username',
            'cluster_uid': '1234',
        }

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        message = 'No completion_time is given.'
        self.assertIn(message, json['non_field_errors'])
        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_no_username_given(self):
        """Test no username given when status == Active."""
        self._assert_pre_state()
        url = self.pk_url(BASE_URL, self.request0.pk)

        data = {
            'status': 'Active',
            'completion_time': utc_now_offset_aware(),
            'cluster_uid': '1234',
        }

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        message = 'No username is given.'
        self.assertIn(message, json['non_field_errors'])
        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_no_cluster_uid_given(self):
        """Test no cluster_uid given when status == Active."""
        self._assert_pre_state()
        url = self.pk_url(BASE_URL, self.request0.pk)

        data = {
            'status': 'Active',
            'completion_time': utc_now_offset_aware(),
            'username': 'new_username',
        }

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        message = 'No cluster_uid is given.'
        self.assertIn(message, json['non_field_errors'])
        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_username_taken(self):
        """Test given username is already taken."""
        self._assert_pre_state()
        url = self.pk_url(BASE_URL, self.request0.pk)

        data = {
            'status': 'Active',
            'completion_time': utc_now_offset_aware(),
            'username': 'user1',
            'cluster_uid': '1234'
        }

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        message = 'A user with username user1 already exists.'
        self.assertIn(message, json['non_field_errors'])
        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_cluster_uid_taken(self):
        """Test given cluster_uid is already taken."""
        self._assert_pre_state()
        self.user1.userprofile.cluster_uid = '1234'
        self.user1.userprofile.save()

        url = self.pk_url(BASE_URL, self.request0.pk)

        data = {
            'status': 'Active',
            'completion_time': utc_now_offset_aware(),
            'username': 'user0',
            'cluster_uid': '1234'
        }

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        message = 'A user with cluster_uid 1234 already exists.'
        self.assertIn(message, json['non_field_errors'])
        self._assert_pre_state()
        self.assertEqual(len(mail.outbox), 0)

    def test_exception_causes_rollback_complete(self):
        """Test that, when an exception occurs, changes made so far are
        rolled back."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'completion_time': utc_now_offset_aware(),
            'status': 'Active',
            'username': self.new_username,
            'cluster_uid': self.cluster_uid
        }
        with patch.object(
                ProjectClusterAccessRequestCompleteRunner, 
                'run',
                raise_exception):
            response = self.client.patch(url, data)

        self.assertEqual(
            response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Internal server error.')

        self._assert_pre_state()

        self.assertEqual(len(mail.outbox), 0)

    def test_exception_causes_rollback_denial(self):
        """Test that, when an exception occurs, changes made so far are
        rolled back."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request0.pk)
        data = {
            'completion_time': utc_now_offset_aware(),
            'status': 'Denied'
        }
        with patch.object(
                ProjectClusterAccessRequestDenialRunner,
                'run',
                raise_exception):
            response = self.client.patch(url, data)

        self.assertEqual(
            response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Internal server error.')

        self._assert_pre_state()

        self.assertEqual(len(mail.outbox), 0)


class TestDestroyClusterAccessRequests(TestClusterAccessRequestsBase):
    """A class for testing DELETE /cluster_access_requests/
    {cluster_access_request_id}/."""

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


class TestUpdatePutClusterAccessRequests(TestClusterAccessRequestsBase):
    """A class for testing PUT /cluster_access_requests/
    {cluster_access_request_id}/."""

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


class TestCreateClusterAccessRequests(TestClusterAccessRequestsBase):
    """A class for testing POST /cluster_access_requests/."""

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
