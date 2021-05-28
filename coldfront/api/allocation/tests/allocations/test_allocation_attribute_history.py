from coldfront.api.allocation.tests.test_allocation_base import TestAllocationBase
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import HistoricalAllocationAttribute
from datetime import datetime
from decimal import Decimal
from http import HTTPStatus

"""A test suite for the /allocations/{allocation_id}/attributes/
{attribute_id}/history/ endpoints, divided by method."""

SERIALIZER_FIELDS = (
    'history_id', 'id', 'value', 'history_date', 'history_change_reason',
    'history_type', 'allocation_attribute_type', 'allocation', 'history_user',)


class TestListAllocationAttributeHistory(TestAllocationBase):
    """A class for testing GET /allocations/{allocation_id}/attributes/
    {attribute_id}/history/."""

    def endpoint_url(self, allocation_pk, attribute_pk):
        """Return the URL for the endpoint."""
        return (
            f'{self.allocations_base_url}{allocation_pk}/attributes/'
            f'{attribute_pk}/history/')

    def test_response_format(self):
        """Test that the response is in the expected format."""
        allocation = Allocation.objects.first()
        allocation_attribute = AllocationAttribute.objects.filter(
            allocation=allocation).first()
        url = self.endpoint_url(allocation.pk, allocation_attribute.pk)
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
        """Test that the results are sorted by date in descending
        order."""
        allocation = Allocation.objects.first()
        allocation_attribute = AllocationAttribute.objects.filter(
            allocation=allocation).first()
        # Create a second HistoricalRecord.
        allocation_attribute.value = Decimal('0.00')
        allocation_attribute.save()

        url = self.endpoint_url(allocation.pk, allocation_attribute.pk)
        response = self.client.get(url)
        json = response.json()
        self.assertGreaterEqual(json['count'], 2)
        previous = json['results'][0]['history_date']
        for i in range(1, len(json['results'])):
            current = json['results'][i]['history_date']
            self.assertLess(current, previous)
            previous = current

    def test_no_filters(self):
        """Test that all results are returned when no query filters are
        provided."""
        allocation = Allocation.objects.first()
        allocation_attribute = AllocationAttribute.objects.filter(
            allocation=allocation).first()
        # Create a second HistoricalRecord.
        allocation_attribute.value = Decimal('0.00')
        allocation_attribute.save()
        value_iterator = iter([Decimal('0.00'), Decimal('1000.00')])

        url = self.endpoint_url(allocation.pk, allocation_attribute.pk)
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(
            json['count'],
            HistoricalAllocationAttribute.objects.filter(
                id=allocation_attribute.pk).count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            historical_allocation_attribute = \
                HistoricalAllocationAttribute.objects.get(
                    history_id=result['history_id'])
            self.assertEqual(
                historical_allocation_attribute.history_id,
                result['history_id'])
            self.assertEqual(historical_allocation_attribute.id, result['id'])
            self.assertEqual(next(value_iterator), Decimal(result['value']))
            self.assertEqual(
                datetime.strftime(
                    historical_allocation_attribute.history_date,
                    '%Y-%m-%dT%H:%M:%S.%fZ'),
                result['history_date'])
            self.assertEqual(
                historical_allocation_attribute.history_change_reason,
                result['history_change_reason'])
            self.assertEqual(
                historical_allocation_attribute.history_type,
                result['history_type'])
            self.assertEqual(
                historical_allocation_attribute.allocation_attribute_type.name,
                result['allocation_attribute_type'])
            self.assertEqual(
                historical_allocation_attribute.allocation.pk,
                result['allocation'])
            self.assertEqual(
                historical_allocation_attribute.history_user,
                result['history_user'])


class TestRetrieveAllocationAttributeHistory(TestAllocationBase):
    """A class for testing GET /allocations/{allocation_id}/attributes/
    {attribute_id}/history/{history_id}."""

    def endpoint_url(self, allocation_pk, attribute_pk, history_pk):
        """Return the URL for the endpoint."""
        return (
            f'{self.allocations_base_url}{allocation_pk}/attributes/'
            f'{attribute_pk}/history/{history_pk}/')

    def test_valid_pk(self):
        """Test that the response for a valid primary key has the
        expected format."""
        allocation = Allocation.objects.first()
        allocation_attribute = AllocationAttribute.objects.filter(
            allocation=allocation).first()
        historical_allocation_attribute = \
            HistoricalAllocationAttribute.objects.filter(
                id=allocation_attribute.id).first()
        url = self.endpoint_url(
            allocation.pk, allocation_attribute.pk,
            historical_allocation_attribute.pk)
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
        allocation_attribute = AllocationAttribute.objects.filter(
            allocation=allocation).first()
        pk = sum(
            HistoricalAllocationAttribute.objects.values_list(
                'pk', flat=True)) + 1
        url = self.endpoint_url(allocation.pk, allocation_attribute.pk, pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Not found.')
