from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.utils import prorated_allocation_amount
from coldfront.core.utils.common import display_time_zone_current_date
from datetime import date
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.test import TestCase
import pytz


class TestProratedAllocationAmount(TestCase):
    """A class for testing the prorated_allocation_amount method."""

    def setUp(self):
        """Set up test data."""
        self.today = display_time_zone_current_date()
        self.num_service_units = Decimal('300000.00')
        self.period = AllocationPeriod.objects.create(
            name='Allocation Period',
            start_date=date(self.today.year, 6, 1),
            end_date=date(self.today.year + 1, 5, 31))

    def test_datetime_after_period_returns_none(self):
        """Test that passing a datetime that is after the
        AllocationPeriod results in zero service units."""
        time_zone = pytz.timezone(settings.DISPLAY_TIME_ZONE)
        dt = datetime(self.today.year + 1, 6, 1, tzinfo=time_zone)
        expected_amount = Decimal('0.00')
        actual_amount = prorated_allocation_amount(
            self.num_service_units, dt, self.period)
        self.assertEqual(expected_amount, actual_amount)

    def test_datetime_before_period_returns_all(self):
        """Test that passing a datetime that is before the
        AllocationPeriod results in the total number of service
        units."""
        time_zone = pytz.timezone(settings.DISPLAY_TIME_ZONE)
        dt = datetime(self.today.year - 1, 5, 31, tzinfo=time_zone)
        expected_amount = self.num_service_units
        actual_amount = prorated_allocation_amount(
            self.num_service_units, dt, self.period)
        self.assertEqual(expected_amount, actual_amount)

    def test_datetime_during_period_returns_fraction(self):
        """Test that passing a datetime that is during the
        AllocationPeriod results in a fraction of the total number of
        service units."""
        expected_amounts_by_date = {
            (self.today.year, 6, 1): Decimal('300000.00'),
            (self.today.year, 6, 30): Decimal('300000.00'),
            (self.today.year, 7, 1): Decimal('275000.00'),
            (self.today.year, 7, 31): Decimal('275000.00'),
            (self.today.year, 12, 1): Decimal('150000.00'),
            (self.today.year, 12, 31): Decimal('150000.00'),
            (self.today.year + 1, 4, 1): Decimal('50000.00'),
            (self.today.year + 1, 4, 30): Decimal('50000.00'),
            (self.today.year + 1, 5, 1): Decimal('25000.00'),
            (self.today.year + 1, 5, 31): Decimal('25000.00'),
        }
        timezone = pytz.timezone(settings.DISPLAY_TIME_ZONE)
        for date_triple, expected_amount in expected_amounts_by_date.items():
            dt = datetime(*date_triple, tzinfo=timezone)
            actual_amount = prorated_allocation_amount(
                self.num_service_units, dt, self.period)
            self.assertEqual(expected_amount, actual_amount)
