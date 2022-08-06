from http import HTTPStatus
from unittest.mock import patch

from django.conf import settings
from django.core import mail

from coldfront.api.project.tests.test_project_base import TestProjectBase
from coldfront.api.project.tests.utils import assert_project_user_removal_request_serialization
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRemovalRequest
from coldfront.core.project.models import ProjectUserRemovalRequestStatusChoice
from coldfront.core.project.utils_.removal_utils import ProjectRemovalRequestProcessingRunner
from coldfront.core.utils.common import utc_now_offset_aware

"""A test suite for the /project_user_removal_requests/ endpoints, divided
by method."""

SERIALIZER_FIELDS = (
    'id', 'completion_time', 'status', 'project_user')
BASE_URL = '/api/project_user_removal_requests/'


def raise_exception(*args, **kwargs):
    """Raise an exception."""
    raise Exception('Test exception.')


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

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.request_obj = ProjectUserRemovalRequest.objects.filter(
            status__name='Pending').first()
        self.project_user_obj = self.request_obj.project_user
        self.allocation_user_obj = AllocationUser.objects.get(
            allocation__project=self.project_user_obj.project,
            user=self.project_user_obj.user)
        self.allocation_user_attribute_obj = \
            self.allocation_user_obj.allocationuserattribute_set.get(
                allocation_attribute_type__name='Cluster Account Status')

    def _assert_emails_sent(self):
        """Assert that emails are sent from the expected sender to the
        expected recipients, with the expected body."""
        user = self.request_obj.project_user.user
        requester = self.request_obj.requester
        project = self.request_obj.project_user.project

        expected_from = settings.EMAIL_SENDER
        expected_to = {user.email for user in [user, requester]}
        user_name = f'{user.first_name} {user.last_name}'
        requester_name = f'{requester.first_name} {requester.last_name}'
        project_name = project.name
        expected_body = (
            f'The request to remove {user_name} of Project {project_name} '
            f'initiated by {requester_name} has been completed. {user_name} '
            f'is no longer a user of Project {project_name}.')

        for email in mail.outbox:
            self.assertEqual(email.from_email, expected_from)
            self.assertEqual(len(email.to), 1)
            to = email.to[0]
            self.assertIn(to, expected_to)
            expected_to.remove(to)
            self.assertIn(expected_body, email.body)

        self.assertFalse(expected_to)

    def _assert_post_state(self, completion_time):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has run successfully. In particular,
        assert that the request's completion_time the given one."""
        self._refresh_objects()
        self.assertEqual(self.project_user_obj.status.name, 'Removed')
        self.assertEqual(self.allocation_user_obj.status.name, 'Removed')
        self.assertEqual(self.allocation_user_attribute_obj.value, 'Denied')
        self.assertEqual(self.request_obj.status.name, 'Complete')
        self.assertEqual(self.request_obj.completion_time, completion_time)

    def _assert_pre_state(self):
        """Assert that the relevant objects have the expected state,
        assuming that the runner has either not run or not run
        successfully."""
        self._refresh_objects()
        self.assertEqual(self.project_user_obj.status.name, 'Active')
        self.assertEqual(self.allocation_user_obj.status.name, 'Active')
        self.assertEqual(self.allocation_user_attribute_obj.value, 'Active')
        self.assertEqual(self.request_obj.status.name, 'Pending')
        self.assertFalse(self.request_obj.completion_time)

    def _refresh_objects(self):
        """Refresh relevant objects from the database."""
        self.project_user_obj.refresh_from_db()
        self.allocation_user_obj.refresh_from_db()
        self.allocation_user_attribute_obj.refresh_from_db()
        self.request_obj.refresh_from_db()

    def test_authorization_token_required(self):
        """Test that an authorization token is required."""
        url = self.pk_url(BASE_URL, '1')
        method = 'PATCH'
        self.assert_authorization_token_required(url, method)

    def test_exception_causes_rollback(self):
        """Test that, when an exception occurs, changes made so far are
        rolled back."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request_obj.pk)
        completion_time = utc_now_offset_aware()
        data = {
            'completion_time': completion_time.isoformat(),
            'status': 'Complete',
        }
        with patch.object(
                ProjectRemovalRequestProcessingRunner, 'run', raise_exception):
            response = self.client.patch(url, data)

        self.assertEqual(
            response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Internal server error.')

        self._assert_pre_state()

        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_data(self):
        """Test that updating an object with invalid PATCH data
        fails."""
        project_user_removal_request = \
            ProjectUserRemovalRequest.objects.first()
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

    def test_set_to_complete_without_time(self):
        """Test that attempting to set the status to 'Complete' without
        providing a completion_time fails."""
        project_user_removal_request = \
            ProjectUserRemovalRequest.objects.first()
        url = self.pk_url(BASE_URL, project_user_removal_request.pk)
        data = {
            'status': 'Complete',
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()

        self.assertEqual(
            json.get('non_field_errors', []),
            ['No completion_time is given.'])

    def test_valid_data_complete(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is 'Complete', and additional
        processing is run."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request_obj.pk)
        completion_time = utc_now_offset_aware()
        data = {
            'completion_time': completion_time.isoformat(),
            'status': 'Complete',
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self._assert_post_state(completion_time)

        self._assert_emails_sent()

    def test_valid_data_processing(self):
        """Test that updating an object with valid PATCH data
        succeeds when the new status is 'Processing', and additional
        processing is not run."""
        self._assert_pre_state()

        url = self.pk_url(BASE_URL, self.request_obj.pk)
        data = {
            'status': 'Processing',
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status.name, data['status'])

        # Set the status back so that the helper method may be used for
        # checking that other objects were not changed.
        self.request_obj.status = \
            ProjectUserRemovalRequestStatusChoice.objects.get(name='Pending')
        self.request_obj.save()
        self._assert_pre_state()

        self.assertEqual(len(mail.outbox), 0)


class TestDestroyProjectUserRemovalRequests(TestProjectUserRemovalRequestsBase):
    """A class for testing DELETE /project_user_removal_requests/
    {project_user_removal_request_id}/."""

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


class TestUpdatePutProjectUserRemovalRequests(TestProjectUserRemovalRequestsBase):
    """A class for testing PUT /project_user_removal_requests/
    {project_user_removal_request_id}/."""

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


class TestCreateProjectUserRemovalRequests(TestProjectUserRemovalRequestsBase):
    """A class for testing POST /project_user_removal_requests/."""

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