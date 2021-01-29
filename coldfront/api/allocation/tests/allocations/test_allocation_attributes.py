from coldfront.api.allocation.tests.test_allocation_base import TestAllocationBase
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AttributeType
from decimal import Decimal
from http import HTTPStatus

"""A test suite for the /allocations/{allocation_id}/attributes/
endpoints, divided by method."""

SERIALIZER_FIELDS = (
    'id', 'allocation_attribute_type', 'allocation', 'value', 'usage',)
USAGE_SERIALIZER_FIELDS = ('allocation_attribute', 'value',)


class TestListAllocationAttributes(TestAllocationBase):
    """A class for testing GET /allocations/{allocation_id}/
    attributes/."""

    def endpoint_url(self, allocation_pk):
        """Return the URL for the endpoint."""
        return f'{self.allocations_base_url}{allocation_pk}/attributes/'

    def test_response_format(self):
        """Test that the response is in the expected format."""
        allocation = Allocation.objects.first()
        url = self.endpoint_url(allocation.pk)
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
        allocation = Allocation.objects.first()
        attribute_type = AttributeType.objects.get(name='Decimal')
        allocation_attribute_type = AllocationAttributeType.objects.create(
            name='Other Units', attribute_type=attribute_type)
        AllocationAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation, value='0.00')

        url = self.endpoint_url(allocation.pk)
        response = self.client.get(url)
        json = response.json()
        self.assertGreaterEqual(len(json['results']), 2)
        previous = json['results'][0]['id']
        for i in range(1, len(json['results'])):
            current = json['results'][i]['id']
            self.assertGreater(current, previous)
            previous = current

    def test_no_filters(self):
        """Test that all results are returned when no query filters are
        provided."""
        allocation = Allocation.objects.first()

        url = self.endpoint_url(allocation.pk)
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(
            json['count'],
            AllocationAttribute.objects.filter(allocation=allocation).count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            allocation_attribute = AllocationAttribute.objects.get(
                id=result['id'])
            self.assertEqual(allocation_attribute.id, result['id'])
            self.assertEqual(
                allocation_attribute.allocation_attribute_type.name,
                result['allocation_attribute_type'])
            self.assertEqual(
                allocation_attribute.allocation.id, result['allocation'])
            self.assertEqual(allocation_attribute.value, result['value'])
            usage = AllocationAttributeUsage.objects.get(
                allocation_attribute=allocation_attribute)
            self.assertEqual(
                usage.allocation_attribute.id,
                result['usage']['allocation_attribute'])
            self.assertEqual(usage.value, Decimal(result['usage']['value']))

    def test_type_filter(self):
        """Test that querying by type filters results properly."""
        allocation = Allocation.objects.first()
        type_name = 'Service Units'

        url = self.endpoint_url(allocation.pk)
        query_parameters = {
            'type': type_name,
        }
        response = self.client.get(url, query_parameters)
        json = response.json()
        self.assertEqual(json['count'], 1)
        result = json['results'][0]
        self.assertEqual(result['allocation_attribute_type'], type_name)

        query_parameters = {
            'type': 'Invalid',
        }
        response = self.client.get(url, query_parameters)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        json = response.json()
        self.assertIn('type', json)
        message = (
            'Select a valid choice. Invalid is not one of the available '
            'choices.')
        self.assertIn(message, json['type'])


class TestRetrieveAllocationAttributes(TestAllocationBase):
    """A class testing GET /allocations/{allocation_id}/attributes/
    {attribute_id}/."""

    def endpoint_url(self, allocation_pk, attribute_pk):
        """Return the URL for the endpoint."""
        return (
            f'{self.allocations_base_url}{allocation_pk}/attributes/'
            f'{attribute_pk}/')

    def test_valid_pk(self):
        """Test that the response for a valid primary key has the
        expected format."""
        allocation = Allocation.objects.first()
        allocation_attribute = AllocationAttribute.objects.filter(
            allocation=allocation).first()
        url = self.endpoint_url(allocation.pk, allocation_attribute.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        self.assertEqual(len(json), len(SERIALIZER_FIELDS))
        for field in SERIALIZER_FIELDS:
            self.assertIn(field, json)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent primary key raises
        an error."""
        allocation = Allocation.objects.first()
        pk = sum(AllocationAttribute.objects.values_list('pk', flat=True)) + 1
        url = self.endpoint_url(allocation.pk, pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Not found.')
