from coldfront.api.allocation.tests.test_allocation_base import TestAllocationBase
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceType
from coldfront.core.resource.utils import get_primary_compute_resource_name
from http import HTTPStatus

"""A test suite for the /allocation_users/ endpoints, divided by
method."""

SERIALIZER_FIELDS = ('id', 'allocation', 'user', 'project', 'status',)


class TestListAllocationUsers(TestAllocationBase):
    """A class for testing GET /allocation_users/."""

    def endpoint_url(self):
        """Return the URL for the endpoint."""
        return self.allocation_users_base_url

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
        self.assertEqual(json['count'], AllocationUser.objects.count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            allocation_user = AllocationUser.objects.get(id=result['id'])
            self.assertEqual(allocation_user.id, result['id'])
            self.assertEqual(
                allocation_user.allocation.id, result['allocation'])
            self.assertEqual(allocation_user.user.username, result['user'])
            self.assertEqual(
                allocation_user.allocation.project.name, result['project'])
            self.assertEqual(allocation_user.status.name, result['status'])

    def test_user_filter(self):
        """Test that querying by user filters results properly."""
        user = self.user0.username

        url = self.endpoint_url()
        query_parameters = {
            'user': user,
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 2)
        for result in json['results']:
            self.assertEqual(result['user'], user)

        query_parameters = {
            'user': self.pi.username,
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 0)

        query_parameters = {
            'user': 'Invalid',
        }
        response = self.client.get(url, query_parameters)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()
        self.assertIn('user', json)
        message = (
            'Select a valid choice. Invalid is not one of the available '
            'choices.')
        self.assertIn(message, json['user'])

    def test_project_filter(self):
        """Test that querying by project filters results properly."""
        project = self.project0.name

        url = self.endpoint_url()
        query_parameters = {
            'project': project,
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 2)
        result = json['results'][0]
        self.assertEqual(result['project'], project)

        query_parameters = {
            'project': 'Invalid',
        }
        response = self.client.get(url, query_parameters)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()
        self.assertIn('project', json)
        message = (
            'Select a valid choice. Invalid is not one of the available '
            'choices.')
        self.assertIn(message, json['project'])

    def test_resources_filter(self):
        """Test that querying by resource filters results properly."""
        allocation = Allocation.objects.get(project=self.project0)
        resource_type = ResourceType.objects.get(name='Cluster')
        resource = Resource.objects.create(
            name='Other Compute', resource_type=resource_type)
        allocation.resources.add(resource)

        first = allocation.pk
        second = Allocation.objects.get(project=self.project1).pk
        allocation_ids_iterator = iter([first, first, second, second])

        resource_name = get_primary_compute_resource_name()
        url = self.endpoint_url()
        query_parameters = {
            'resources': resource_name,
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 4)
        for result in json['results']:
            self.assertEqual(
                next(allocation_ids_iterator), result['allocation'])
            self.assertTrue(
                Resource.objects.filter(
                    allocation=allocation, name=resource_name))

        query_parameters = {
            'resources': 'Other Compute',
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 2)
        for result in json['results']:
            self.assertEqual(allocation.id, result['allocation'])
            self.assertTrue(
                Resource.objects.filter(
                    allocation=allocation, name='Other Compute'))

        query_parameters = {
            'resources': 'Invalid',
        }
        response = self.client.get(url, query_parameters)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()
        self.assertIn('resources', json)
        message = (
            'Select a valid choice. Invalid is not one of the available '
            'choices.')
        self.assertIn(message, json['resources'])


class TestRetrieveAllocationUsers(TestAllocationBase):
    """A class for testing GET /allocation_users/
    {allocation_user_id}/."""

    def endpoint_url(self, allocation_user_pk):
        """Return the URL for the endpoint."""
        return f'{self.allocation_users_base_url}{allocation_user_pk}/'

    def test_valid_pk(self):
        """Test that the response for a valid primary key has the
        expected format."""
        allocation_user = AllocationUser.objects.first()
        url = self.endpoint_url(allocation_user.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        self.assertEqual(len(json), len(SERIALIZER_FIELDS))
        for field in SERIALIZER_FIELDS:
            self.assertIn(field, json)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent primary key raises
        an error."""
        pk = sum(AllocationUser.objects.values_list('pk', flat=True)) + 1
        url = self.endpoint_url(pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Not found.')
