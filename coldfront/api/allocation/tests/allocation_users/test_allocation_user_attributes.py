from coldfront.api.allocation.tests.test_allocation_base import TestAllocationBase
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AttributeType
from decimal import Decimal
from http import HTTPStatus

"""A test suite for the /allocation_users/{allocation_user_id}/
attributes/ endpoints, divided by method."""

SERIALIZER_FIELDS = (
    'id', 'allocation_attribute_type', 'allocation', 'allocation_user',
    'value', 'usage',)
USAGE_SERIALIZER_FIELDS = ('allocation_user_attribute', 'value',)


class TestListAllocationUserAttributes(TestAllocationBase):
    """A class for testing GET /allocation_users/{allocation_user_id}/
    attributes/."""

    def endpoint_url(self, allocation_user_pk):
        """Return the URL for the endpoint."""
        return (
            f'{self.allocation_users_base_url}{allocation_user_pk}/'
            f'attributes/')

    def test_response_format(self):
        """Test that the response is in the expected format."""
        allocation_user = AllocationUser.objects.first()
        url = self.endpoint_url(allocation_user.pk)
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
        allocation_user = AllocationUser.objects.first()
        attribute_type = AttributeType.objects.get(name='Decimal')
        allocation_attribute_type = AllocationAttributeType.objects.create(
            name='Other Units', attribute_type=attribute_type)
        AllocationUserAttribute.objects.create(
            allocation_attribute_type=allocation_attribute_type,
            allocation=allocation_user.allocation,
            allocation_user=allocation_user, value='0.00')

        url = self.endpoint_url(allocation_user.pk)
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
        allocation_user = AllocationUser.objects.first()

        url = self.endpoint_url(allocation_user.pk)
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(
            json['count'],
            AllocationUserAttribute.objects.filter(
                allocation_user=allocation_user).count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            allocation_user_attribute = AllocationUserAttribute.objects.get(
                id=result['id'])
            self.assertEqual(allocation_user_attribute.id, result['id'])
            self.assertEqual(
                allocation_user_attribute.allocation_attribute_type.name,
                result['allocation_attribute_type'])
            self.assertEqual(
                allocation_user_attribute.allocation.id, result['allocation'])
            self.assertEqual(
                allocation_user_attribute.allocation_user.id,
                result['allocation_user'])
            self.assertEqual(allocation_user_attribute.value, result['value'])
            usage = AllocationUserAttributeUsage.objects.get(
                allocation_user_attribute=allocation_user_attribute)
            self.assertEqual(
                usage.allocation_user_attribute.id,
                result['usage']['allocation_user_attribute'])
            self.assertEqual(usage.value, Decimal(result['usage']['value']))

    def test_type_filter(self):
        """Test that querying by type filters results properly."""
        allocation_user = AllocationUser.objects.first()
        type_name = 'Service Units'

        url = self.endpoint_url(allocation_user.pk)
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


class TestRetrieveAllocationUserAttributes(TestAllocationBase):
    """A class for testing GET /allocation_users/{allocation_user_id}/
    attributes/{attribute_id}/."""

    def endpoint_url(self, allocation_user_pk, attribute_pk):
        """Return the URL for the endpoint."""
        return (
            f'{self.allocation_users_base_url}{allocation_user_pk}/'
            f'attributes/{attribute_pk}/')

    def test_valid_pk(self):
        """Test that the response for a valid primary key has the
        expected format."""
        allocation_user = AllocationUser.objects.first()
        allocation_user_attribute = AllocationUserAttribute.objects.filter(
            allocation_user=allocation_user).first()
        url = self.endpoint_url(
            allocation_user.pk, allocation_user_attribute.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        json = response.json()
        self.assertEqual(len(json), len(SERIALIZER_FIELDS))
        for field in SERIALIZER_FIELDS:
            self.assertIn(field, json)

    def test_invalid_pk(self):
        """Test that the response for a nonexistent primary key raises
        an error."""
        allocation_user = AllocationUser.objects.first()
        pk = sum(
            AllocationUserAttribute.objects.values_list('pk', flat=True)) + 1
        url = self.endpoint_url(allocation_user.pk, pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Not found.')
