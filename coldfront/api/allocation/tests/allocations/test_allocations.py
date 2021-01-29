from coldfront.api.allocation.tests.test_allocation_base import TestAllocationBase
from coldfront.core.allocation.models import Allocation
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceType
from http import HTTPStatus

"""A test suite for the /allocations/ endpoints, divided by method."""

SERIALIZER_FIELDS = (
    'id', 'project', 'resources', 'status', 'quantity', 'start_date',
    'end_date', 'justification', 'description', 'is_locked',)


class TestListAllocations(TestAllocationBase):
    """A class for testing GET /allocations/."""

    def endpoint_url(self):
        """Return the URL for the endpoint."""
        return self.allocations_base_url

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
        self.assertEqual(json['count'], Allocation.objects.count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            allocation = Allocation.objects.get(id=result['id'])
            self.assertEqual(allocation.id, result['id'])
            self.assertEqual(allocation.project.name, result['project'])
            self.assertTrue(
                allocation.resources.count() == len(result['resources']) == 1)
            self.assertEqual(
                allocation.resources.first().name,
                result['resources'][0]['name'])
            self.assertEqual(allocation.status.name, result['status'])
            self.assertEqual(allocation.start_date, result['start_date'])
            self.assertEqual(allocation.end_date, result['end_date'])
            self.assertEqual(allocation.justification, result['justification'])
            self.assertEqual(allocation.description, result['description'])
            self.assertEqual(allocation.is_locked, result['is_locked'])

    def test_project_filter(self):
        """Test that querying by project filters results properly."""
        project = self.project0.name

        url = self.endpoint_url()
        query_parameters = {
            'project': project,
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 1)
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

        url = self.endpoint_url()
        query_parameters = {
            'resources': 'Savio Compute',
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 2)
        for result in json['results']:
            self.assertIn({'name': 'Savio Compute'}, result['resources'])

        query_parameters = {
            'resources': 'Other Compute',
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 1)
        result = json['results'][0]
        self.assertEqual(allocation.id, result['id'])
        self.assertIn({'name': 'Other Compute'}, result['resources'])

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


class TestRetrieveAllocations(TestAllocationBase):
    """A class for testing GET /allocations/{allocation_id}/."""

    def endpoint_url(self, allocation_pk):
        """Return the URL for the endpoint."""
        return f'{self.allocations_base_url}{allocation_pk}/'

    def test_valid_pk(self):
        """Test that the response for a valid primary key has the
        expected format."""
        allocation = Allocation.objects.first()
        url = self.endpoint_url(allocation.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        self.assertEqual(len(json), len(SERIALIZER_FIELDS))
        for field in SERIALIZER_FIELDS:
            self.assertIn(field, json)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent primary key raises
        an error."""
        pk = sum(Allocation.objects.values_list('pk', flat=True)) + 1
        url = self.endpoint_url(pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Not found.')
