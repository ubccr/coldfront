from coldfront.api.project.tests.test_project_base import TestProjectBase
from coldfront.api.project.tests.utils import assert_project_user_removal_request_serialization
from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice, \
    ProjectUserRemovalRequest, ProjectUser
from coldfront.core.utils.common import utc_now_offset_aware
from http import HTTPStatus

"""A test suite for the /project_user_removal_requests/ endpoints, divided
by method."""

SERIALIZER_FIELDS = (
    'id', 'completion_time', 'status', 'project_user')
BASE_URL = '/api/project_user_removal_requests/'


class TestProjectUserRemovalRequestsBase(TestProjectBase):
    """A base class for tests of the /project_user_removal_requests/
    endpoints."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create six ProjectUserRemovalRequests: two pending, two processing,
        # and two complete.
        status_choices = ProjectUserRemovalRequestStatusChoice.objects.all()
        for i in range(6):
            kwargs = {
                'project_user': ProjectUser.objects.get(user__username=f'user{i%3}',
                                                        project__name=f'fc_project{i%2}'),
                'requester': self.pi,
                'request_time': utc_now_offset_aware(),
            }
            if i % 3 == 0:
                kwargs['status'] = status_choices.get(name='Pending')
            elif i % 3 == 1:
                kwargs['status'] = status_choices.get(name='Processing')
            else:
                kwargs['status'] = status_choices.get(name='Complete')
                kwargs['completion_time'] = utc_now_offset_aware()
            request = ProjectUserRemovalRequest.objects.create(**kwargs)
            setattr(self, f'request{i}', request)

        # Run the client as the superuser.
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Token {self.superuser_token.key}')


class TestListProjectUserRemovalRequests(TestProjectUserRemovalRequestsBase):
    """A class for testing GET /project_user_removal_requests/."""

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
        self.assertEqual(json['count'], ProjectUserRemovalRequest.objects.count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            project_user_removal_request = \
                ProjectUserRemovalRequest.objects.get(pk=result['id'])
            assert_project_user_removal_request_serialization(
                project_user_removal_request, result, SERIALIZER_FIELDS)

    def test_status_filter(self):
        """Test that querying by status filters results properly."""
        url = BASE_URL
        self.assertEqual(ProjectUserRemovalRequest.objects.count(), 6)
        for status in ('Pending', 'Processing', 'Complete'):
            query_parameters = {
                'status': status,
            }
            response = self.client.get(url, query_parameters)
            json = response.json()
            self.assertEqual(json['count'], 2)
            for result in json['results']:
                self.assertEqual(result['status'], status)


class TestRetrieveProjectUserRemovalRequests(TestProjectUserRemovalRequestsBase):
    """A class for testing GET /project_user_removal_requests/
    {project_user_removal_request_id}/."""

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
        project_user_removal_request = ProjectUserRemovalRequest.objects.first()
        url = self.pk_url(BASE_URL, project_user_removal_request.pk)
        self.assert_retrieve_result_format(url, SERIALIZER_FIELDS)

    def test_valid_pk(self):
        """Test that the response for a valid primary key contains the
        correct values."""
        project_user_removal_request = ProjectUserRemovalRequest.objects.first()
        url = self.pk_url(BASE_URL, project_user_removal_request.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        assert_project_user_removal_request_serialization(
            project_user_removal_request, json, SERIALIZER_FIELDS)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent or unassociated
        primary key raises an error."""
        pk = self.generate_invalid_pk(ProjectUserRemovalRequest)
        url = self.pk_url(BASE_URL, pk)
        self.assert_retrieve_invalid_response_format(url)


class TestUpdatePatchProjectUserRemovalRequests(TestProjectUserRemovalRequestsBase):
    """A class for testing PATCH /project_user_removal_requests/
    {project_user_removal_request_id}/."""

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
        pre_time = utc_now_offset_aware()
        pre_project_user_removal_request = ProjectUserRemovalRequest.objects.first()
        url = self.pk_url(BASE_URL, pre_project_user_removal_request.pk)
        data = {
            'id': pre_project_user_removal_request.id + 1,
            'status': 'Complete',
            'completion_time': utc_now_offset_aware(),
            'project_user': {'id': 7,
                             'user': 'user2',
                             'project': 'fc_project1',
                             'role': 'User',
                             'status': 'Active'}
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        post_project_user_removal_request = ProjectUserRemovalRequest.objects.get(
            pk=pre_project_user_removal_request.id)
        assert_project_user_removal_request_serialization(
            post_project_user_removal_request, json, SERIALIZER_FIELDS)

        self.assertEqual(pre_project_user_removal_request.id,
                         post_project_user_removal_request.id)
        self.assertEqual(pre_project_user_removal_request.status.name,
                         'Pending')
        self.assertEqual(pre_project_user_removal_request.project_user,
                         post_project_user_removal_request.project_user)
        self.assertEqual(post_project_user_removal_request.status.name,
                         'Complete')
        self.assertIsNone(pre_project_user_removal_request.completion_time)
        self.assertTrue(pre_time <
                        post_project_user_removal_request.completion_time <
                        utc_now_offset_aware())

    def test_valid_data_complete(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Complete."""
        project_user_removal_request = ProjectUserRemovalRequest.objects.first()
        url = self.pk_url(BASE_URL, project_user_removal_request.pk)
        completion_time = utc_now_offset_aware()
        data = {
            'completion_time': completion_time.isoformat(),
            'status': 'Complete',
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()

        project_user_removal_request.refresh_from_db()
        assert_project_user_removal_request_serialization(
            project_user_removal_request, json, SERIALIZER_FIELDS)

        self.assertEqual(
            project_user_removal_request.completion_time, completion_time)
        self.assertEqual(project_user_removal_request.status.name, data['status'])

    def test_valid_data_processing(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is Processing."""
        project_user_removal_request = ProjectUserRemovalRequest.objects.first()
        url = self.pk_url(BASE_URL, project_user_removal_request.pk)
        data = {
            'status': 'Processing',
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        project_user_removal_request.refresh_from_db()
        assert_project_user_removal_request_serialization(
            project_user_removal_request, json, SERIALIZER_FIELDS)

        self.assertIsNone(project_user_removal_request.completion_time)
        self.assertEqual(project_user_removal_request.status.name, data['status'])

    def test_invalid_data(self):
        """Test that updating an object with invalid PATCH data
        fails."""
        project_user_removal_request = ProjectUserRemovalRequest.objects.first()
        url = self.pk_url(BASE_URL, project_user_removal_request.pk)
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
