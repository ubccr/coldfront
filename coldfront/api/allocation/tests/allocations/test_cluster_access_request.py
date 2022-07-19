from coldfront.api.allocation.tests.test_allocation_base import \
    TestAllocationBase
from coldfront.api.allocation.tests.utils import \
    assert_cluster_access_request_serialization
from coldfront.core.allocation.models import ClusterAccessRequestStatusChoice, \
    AllocationUser, ClusterAccessRequest, AllocationUserAttribute, \
    AllocationAttributeType
from coldfront.core.utils.common import utc_now_offset_aware
from http import HTTPStatus

"""A test suite for the /cluster_access_requests/ endpoints, divided
by method."""

SERIALIZER_FIELDS = (
    'id', 'status', 'completion_time', 'cluster_uid',
    'username', 'host_user', 'billing_activity', 'allocation_user')
BASE_URL = '/api/cluster_access_requests/'


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
        cluster_access_request = ClusterAccessRequest.objects.first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)
        self.assert_retrieve_result_format(url, SERIALIZER_FIELDS)

    def test_valid_pk(self):
        """Test that the response for a valid primary key contains the
        correct values."""
        cluster_access_request = ClusterAccessRequest.objects.first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        assert_cluster_access_request_serialization(
            cluster_access_request, json, SERIALIZER_FIELDS)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent or unassociated
        primary key raises an error."""
        pk = self.generate_invalid_pk(ClusterAccessRequest)
        url = self.pk_url(BASE_URL, pk)
        self.assert_retrieve_invalid_response_format(url)


class TestUpdatePatchClusterAccessRequests(TestClusterAccessRequestsBase):
    """A class for testing PATCH /cluster_access_requests/
    {cluster_access_request_id}/."""

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
        pre_cluster_access_request = ClusterAccessRequest.objects.filter(allocation_user__user=self.user0).first()
        url = self.pk_url(BASE_URL, pre_cluster_access_request.pk)
        data = {
            'id': pre_cluster_access_request.id + 1,
            'status': 'Active',
            'completion_time': utc_now_offset_aware(),
            'allocation_user': {'id': 12,
                                'allocation': 3,
                                'user': 'user3',
                                'project': 'project0',
                                'status': 'Active'},
            'username': 'new_username',
            'cluster_uid': '1234',
            'host_user': 'user2'
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        post_cluster_access_request = ClusterAccessRequest.objects.get(
            pk=pre_cluster_access_request.id)
        assert_cluster_access_request_serialization(
            post_cluster_access_request, json, SERIALIZER_FIELDS)

        self.assertEqual(pre_cluster_access_request.id,
                         post_cluster_access_request.id)
        self.assertEqual(pre_cluster_access_request.status.name,
                         'Pending - Add')
        self.assertEqual(pre_cluster_access_request.allocation_user,
                         post_cluster_access_request.allocation_user)
        self.assertEqual(post_cluster_access_request.status.name,
                         'Active')
        self.assertIsNone(pre_cluster_access_request.completion_time)
        self.assertEqual(post_cluster_access_request.completion_time,
                         data.get('completion_time'))
        self.assertEqual(pre_cluster_access_request.host_user,
                         post_cluster_access_request.host_user)
        self.assertEqual(post_cluster_access_request.cluster_uid,
                         data.get('cluster_uid'))
        self.assertEqual(post_cluster_access_request.username,
                         data.get('username'))

    def test_valid_data_complete(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Active."""
        cluster_access_request = ClusterAccessRequest.objects.first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)
        completion_time = utc_now_offset_aware()
        data = {
            'completion_time': completion_time.isoformat(),
            'status': 'Active',
            'username': 'new_username',
            'cluster_uid': '1234',
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        cluster_access_request.refresh_from_db()
        assert_cluster_access_request_serialization(
            cluster_access_request, json, SERIALIZER_FIELDS)

        self.assertEqual(
            cluster_access_request.completion_time, completion_time)
        self.assertEqual(cluster_access_request.status.name, data['status'])
        self.assertEqual(cluster_access_request.username, data['username'])
        self.assertEqual(cluster_access_request.cluster_uid, data['cluster_uid'])

        user = cluster_access_request.allocation_user.user
        self.assertEqual(user.username, data['username'])
        self.assertEqual(user.userprofile.cluster_uid, data['cluster_uid'])

        cluster_account_status = \
            AllocationAttributeType.objects.get(name='Cluster Account Status')
        cluster_access_attribute = \
            AllocationUserAttribute.objects.filter(
                allocation_attribute_type=cluster_account_status,
                allocation=cluster_access_request.allocation_user.allocation,
                allocation_user=cluster_access_request.allocation_user)
        self.assertTrue(cluster_access_attribute.exists())

    def test_valid_data_processing(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Processing."""
        cluster_access_request = ClusterAccessRequest.objects.first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)
        data = {
            'status': 'Processing',
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        cluster_access_request.refresh_from_db()
        assert_cluster_access_request_serialization(
            cluster_access_request, json, SERIALIZER_FIELDS)

        self.assertIsNone(cluster_access_request.completion_time)
        self.assertIsNone(cluster_access_request.username)
        self.assertIsNone(cluster_access_request.cluster_uid)
        self.assertEqual(cluster_access_request.status.name, data['status'])

    def test_invalid_data(self):
        """Test that updating an object with invalid PATCH data
        fails."""
        cluster_access_request = ClusterAccessRequest.objects.filter(allocation_user__user=self.user0).first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)
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

    def test_no_completion_time(self):
        """Test no completion time given when status == Active."""
        cluster_access_request = ClusterAccessRequest.objects.filter(allocation_user__user=self.user0).first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)

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

    def test_no_username_given(self):
        """Test no username given when status == Active."""
        cluster_access_request = ClusterAccessRequest.objects.filter(allocation_user__user=self.user0).first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)

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

    def test_no_cluster_uid_given(self):
        """Test no cluster_uid given when status == Active."""
        cluster_access_request = ClusterAccessRequest.objects.filter(allocation_user__user=self.user0).first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)

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

    def test_username_taken(self):
        """Test given username is already taken."""
        cluster_access_request = ClusterAccessRequest.objects.filter(allocation_user__user=self.user0).first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)

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

    def test_cluster_uid_taken(self):
        """Test given cluster_uid is already taken."""
        self.user1.userprofile.cluster_uid = '1234'
        self.user1.userprofile.save()

        cluster_access_request = ClusterAccessRequest.objects.filter(allocation_user__user=self.user0).first()
        url = self.pk_url(BASE_URL, cluster_access_request.pk)

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
