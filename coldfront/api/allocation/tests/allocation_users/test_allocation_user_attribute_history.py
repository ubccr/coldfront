from coldfront.api.allocation.tests.test_allocation_base import TestAllocationBase
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserAttribute
from coldfront.core.allocation.models import HistoricalAllocationUserAttribute
from datetime import datetime
from decimal import Decimal
from http import HTTPStatus

"""A test suite for the /allocation_users/{allocation_user_id}/
attributes/{attribute_id}/history/ endpoints, divided by method."""

SERIALIZER_FIELDS = (
    'history_id', 'id', 'value', 'history_date', 'history_change_reason',
    'history_type', 'allocation_attribute_type', 'allocation',
    'allocation_user', 'history_user',)


class TestListAllocationUserAttributeHistory(TestAllocationBase):
    """A class for testing GET /allocation_users/{allocation_user_id}/
    attributes/{attribute_id}/history/."""

    def endpoint_url(self, allocation_user_pk, attribute_pk):
        """Return the endpoint for the URL."""
        return (
            f'{self.allocation_users_base_url}{allocation_user_pk}/'
            f'attributes/{attribute_pk}/history/')

    def test_response_format(self):
        """Test that the response is in the expected format."""
        allocation_user = AllocationUser.objects.first()
        allocation_user_attribute = AllocationUserAttribute.objects.filter(
            allocation_user=allocation_user).first()
        url = self.endpoint_url(
            allocation_user.pk, allocation_user_attribute.pk)
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
        allocation_user = AllocationUser.objects.first()
        allocation_user_attribute = AllocationUserAttribute.objects.filter(
            allocation_user=allocation_user).first()
        # Create a second HistoricalRecord.
        allocation_user_attribute.value = Decimal("0.00")
        allocation_user_attribute.save()

        url = self.endpoint_url(
            allocation_user.pk, allocation_user_attribute.pk)
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
        allocation_user = AllocationUser.objects.first()
        allocation_user_attribute = AllocationUserAttribute.objects.filter(
            allocation_user=allocation_user).first()
        # Create a second HistoricalRecord.
        allocation_user_attribute.value = Decimal('0.00')
        allocation_user_attribute.save()
        value_iterator = iter([Decimal('0.00'), Decimal('500.00')])

        url = self.endpoint_url(
            allocation_user.pk, allocation_user_attribute.pk)
        response = self.client.get(url)
        json = response.json()
        self.assertEqual(
            json['count'],
            HistoricalAllocationUserAttribute.objects.filter(
                id=allocation_user_attribute.pk).count())
        self.assertIsNone(json['next'])
        self.assertIsNone(json['previous'])
        for result in json['results']:
            historical_allocation_user_attribute = \
                HistoricalAllocationUserAttribute.objects.get(
                    history_id=result['history_id'])
            self.assertEqual(
                historical_allocation_user_attribute.history_id,
                result['history_id'])
            self.assertEqual(
                historical_allocation_user_attribute.id, result['id'])
            self.assertEqual(next(value_iterator), Decimal(result['value']))
            self.assertEqual(
                datetime.strftime(
                    historical_allocation_user_attribute.history_date,
                    '%Y-%m-%dT%H:%M:%S.%fZ'),
                result['history_date'])
            self.assertEqual(
                historical_allocation_user_attribute.history_change_reason,
                result['history_change_reason'])
            self.assertEqual(
                historical_allocation_user_attribute.history_type,
                result['history_type'])
            self.assertEqual(
                getattr(
                    historical_allocation_user_attribute,
                    "allocation_attribute_type").name,
                result['allocation_attribute_type'])
            self.assertEqual(
                historical_allocation_user_attribute.allocation.pk,
                result['allocation'])
            self.assertEqual(
                historical_allocation_user_attribute.allocation_user.pk,
                result['allocation_user'])
            self.assertEqual(
                historical_allocation_user_attribute.history_user,
                result['history_user'])


class TestRetrieveAllocationUserAttributeHistory(TestAllocationBase):
    """A class for testing GET /allocation_users/{allocation_user_id}/
    attributes/{attribute_id}/history/{history_id}/."""

    def endpoint_url(self, allocation_user_pk, attribute_pk, history_pk):
        """Return the endpoint for the URL."""
        return (
            f'{self.allocation_users_base_url}{allocation_user_pk}/'
            f'attributes/{attribute_pk}/history/{history_pk}/')

    def test_valid_pk(self):
        """Test that the response for a valid primary key has the
        expected format."""
        allocation_user = AllocationUser.objects.first()
        allocation_user_attribute = AllocationUserAttribute.objects.filter(
            allocation_user=allocation_user).first()
        historical_allocation_user_attribute = \
            HistoricalAllocationUserAttribute.objects.filter(
                id=allocation_user_attribute.id).first()
        url = self.endpoint_url(
            allocation_user.pk, allocation_user_attribute.pk,
            historical_allocation_user_attribute.pk)
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
        allocation_user_attribute = AllocationUserAttribute.objects.filter(
            allocation_user=allocation_user).first()
        pk = sum(
            HistoricalAllocationUserAttribute.objects.values_list(
                'pk', flat=True)) + 1
        url = self.endpoint_url(
            allocation_user.pk, allocation_user_attribute.pk, pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        json = response.json()
        self.assertIn('detail', json)
        self.assertEqual(json['detail'], 'Not found.')
