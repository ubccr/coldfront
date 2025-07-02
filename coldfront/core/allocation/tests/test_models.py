# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

import datetime
import typing
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import SafeString

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationStatusChoice,
)
from coldfront.core.project.models import Project
from coldfront.core.test_helpers.factories import (
    AllocationAttributeFactory,
    AllocationAttributeTypeFactory,
    AllocationAttributeUsageFactory,
    AllocationFactory,
    AllocationStatusChoiceFactory,
    ProjectFactory,
    ResourceFactory,
)


class AllocationModelTests(TestCase):
    """tests for Allocation model"""

    @classmethod
    def setUpTestData(cls):
        """Set up project to test model properties and methods"""
        cls.allocation = AllocationFactory()
        cls.allocation.resources.add(ResourceFactory(name="holylfs07/tier1"))

    def test_allocation_str(self):
        """test that allocation str method returns correct string"""
        allocation_str = "%s (%s)" % (self.allocation.get_parent_resource.name, self.allocation.project.pi)
        self.assertEqual(str(self.allocation), allocation_str)


class AllocationModelCleanMethodTests(TestCase):
    """tests for Allocation model clean method"""

    @classmethod
    def setUpTestData(cls):
        """Set up allocation to test clean method"""
        cls.active_status: AllocationStatusChoice = AllocationStatusChoiceFactory(name="Active")
        cls.expired_status: AllocationStatusChoice = AllocationStatusChoiceFactory(name="Expired")
        cls.project: Project = ProjectFactory()

    def test_status_is_expired_and_no_end_date_has_validation_error(self):
        """Test that an allocation with status 'expired' and no end date raises a validation error."""
        actual_allocation: Allocation = AllocationFactory.build(
            status=self.expired_status, end_date=None, project=self.project
        )
        with self.assertRaises(ValidationError):
            actual_allocation.full_clean()

    def test_status_is_expired_and_end_date_not_past_has_validation_error(self):
        """Test that an allocation with status 'expired' and end date in the future raises a validation error."""
        end_date_in_the_future: datetime.date = (timezone.now() + datetime.timedelta(days=1)).date()
        actual_allocation: Allocation = AllocationFactory.build(
            status=self.expired_status, end_date=end_date_in_the_future, project=self.project
        )
        with self.assertRaises(ValidationError):
            actual_allocation.full_clean()

    def test_status_is_expired_and_start_date_after_end_date_has_validation_error(self):
        """Test that an allocation with status 'expired' and start date after end date raises a validation error."""
        end_date: datetime.date = (timezone.now() + datetime.timedelta(days=1)).date()
        start_date_after_end_date: datetime.date = end_date + datetime.timedelta(days=1)

        actual_allocation: Allocation = AllocationFactory.build(
            status=self.expired_status, start_date=start_date_after_end_date, end_date=end_date, project=self.project
        )
        with self.assertRaises(ValidationError):
            actual_allocation.full_clean()

    def test_status_is_expired_and_start_date_before_end_date_no_error(self):
        """Test that an allocation with status 'expired' and start date before end date does not raise a validation error."""
        start_date: datetime.date = datetime.datetime(year=2023, month=11, day=2, tzinfo=timezone.utc).date()
        end_date: datetime.date = start_date + datetime.timedelta(days=40)

        actual_allocation: Allocation = AllocationFactory.build(
            status=self.expired_status, start_date=start_date, end_date=end_date, project=self.project
        )
        actual_allocation.full_clean()

    def test_status_is_expired_and_start_date_equals_end_date_no_error(self):
        """Test that an allocation with status 'expired' and start date equal to end date does not raise a validation error."""
        start_and_end_date: datetime.date = datetime.datetime(year=1997, month=4, day=20, tzinfo=timezone.utc).date()

        actual_allocation: Allocation = AllocationFactory.build(
            status=self.expired_status, start_date=start_and_end_date, end_date=start_and_end_date, project=self.project
        )
        actual_allocation.full_clean()

    def test_status_is_active_and_no_start_date_has_validation_error(self):
        """Test that an allocation with status 'active' and no start date raises a validation error."""
        actual_allocation: Allocation = AllocationFactory.build(
            status=self.active_status, start_date=None, project=self.project
        )
        with self.assertRaises(ValidationError):
            actual_allocation.full_clean()

    def test_status_is_active_and_no_end_date_has_validation_error(self):
        """Test that an allocation with status 'active' and no end date raises a validation error."""
        actual_allocation: Allocation = AllocationFactory.build(
            status=self.active_status, end_date=None, project=self.project
        )
        with self.assertRaises(ValidationError):
            actual_allocation.full_clean()

    def test_status_is_active_and_start_date_after_end_date_has_validation_error(self):
        """Test that an allocation with status 'active' and start date after end date raises a validation error."""
        end_date: datetime.date = (timezone.now() + datetime.timedelta(days=1)).date()
        start_date_after_end_date: datetime.date = end_date + datetime.timedelta(days=1)

        actual_allocation: Allocation = AllocationFactory.build(
            status=self.active_status, start_date=start_date_after_end_date, end_date=end_date, project=self.project
        )
        with self.assertRaises(ValidationError):
            actual_allocation.full_clean()

    def test_status_is_active_and_start_date_before_end_date_no_error(self):
        """Test that an allocation with status 'active' and start date before end date does not raise a validation error."""
        start_date: datetime.date = datetime.datetime(year=2001, month=5, day=3, tzinfo=timezone.utc).date()
        end_date: datetime.date = start_date + datetime.timedelta(days=160)

        actual_allocation: Allocation = AllocationFactory.build(
            status=self.active_status, start_date=start_date, end_date=end_date, project=self.project
        )
        actual_allocation.full_clean()

    def test_status_is_active_and_start_date_equals_end_date_no_error(self):
        """Test that an allocation with status 'active' and start date equal to end date does not raise a validation error."""
        start_and_end_date: datetime.date = datetime.datetime(year=2005, month=6, day=3, tzinfo=timezone.utc).date()

        actual_allocation: Allocation = AllocationFactory.build(
            status=self.active_status, start_date=start_and_end_date, end_date=start_and_end_date, project=self.project
        )
        actual_allocation.full_clean()


class AllocationFuncOnExpireException(Exception):
    """Custom exception for testing allocation expiration function in the AllocationModelSaveMethodTests class."""

    pass


def allocation_func_on_expire_exception(*args, **kwargs):
    """Test function to be called on allocation expiration in the AllocationModelSaveMethodTests class."""
    raise AllocationFuncOnExpireException("This is a test exception for allocation expiration.")


def get_dotted_path(func):
    """Return the dotted path string for a Python function in the AllocationModelSaveMethodTests class."""
    return f"{func.__module__}.{func.__qualname__}"


NUMBER_OF_INVOCATIONS = 12


def count_invocations(*args, **kwargs):
    count_invocations.invocation_count = getattr(count_invocations, "invocation_count", 0) + 1  # type: ignore


def count_invocations_negative(*args, **kwargs):
    count_invocations_negative.invocation_count = getattr(count_invocations_negative, "invocation_count", 0) - 1  # type: ignore


def list_of_same_expire_funcs(func: typing.Callable, size=NUMBER_OF_INVOCATIONS) -> list[str]:
    return [get_dotted_path(func) for _ in range(size)]


def list_of_different_expire_funcs() -> list[str]:
    """Return a list of different functions to be called on allocation expiration.
    The list will have a length of NUMBER_OF_INVOCATIONS, with the last function being allocation_func_on_expire_exception.
    If NUMBER_OF_INVOCATIONS is odd, the list will contain (NUMBER_OF_INVOCATIONS // 2) instances of count_invocations and (NUMBER_OF_INVOCATIONS // 2) instances of count_invocations_negative.
    If NUMBER_OF_INVOCATIONS is even, the list will contain (NUMBER_OF_INVOCATIONS // 2) instances of count_invocations and ((NUMBER_OF_INVOCATIONS // 2)-1) instances of count_invocations_negative.
    """
    expire_funcs: list[str] = []
    for i in range(NUMBER_OF_INVOCATIONS):
        if i == (NUMBER_OF_INVOCATIONS - 1):
            expire_funcs.append(get_dotted_path(allocation_func_on_expire_exception))
        elif i % 2 == 0:
            expire_funcs.append(get_dotted_path(count_invocations))
        else:
            expire_funcs.append(get_dotted_path(count_invocations_negative))
    return expire_funcs


class AllocationModelSaveMethodTests(TestCase):
    path_to_allocation_models_funcs_on_expire: str = "coldfront.core.allocation.models.ALLOCATION_FUNCS_ON_EXPIRE"

    def setUp(self):
        count_invocations.invocation_count = 0  # type: ignore
        count_invocations_negative.invocation_count = 0  # type: ignore

    @classmethod
    def setUpTestData(cls):
        """Set up allocation to test clean method"""
        cls.active_status: AllocationStatusChoice = AllocationStatusChoiceFactory(name="Active")
        cls.expired_status: AllocationStatusChoice = AllocationStatusChoiceFactory(name="Expired")
        cls.other_status: AllocationStatusChoice = AllocationStatusChoiceFactory(name="Other")
        cls.project: Project = ProjectFactory()

    @patch(path_to_allocation_models_funcs_on_expire, list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_on_expiration_calls_single_func_in_funcs_on_expire(self):
        """Test that the allocation save method calls the functions specified in ALLOCATION_FUNCS_ON_EXPIRE when it expires."""
        allocation = AllocationFactory(status=self.active_status)
        with self.assertRaises(AllocationFuncOnExpireException):
            allocation.status = self.expired_status
            allocation.save()

    @patch(path_to_allocation_models_funcs_on_expire, list_of_same_expire_funcs(count_invocations))
    def test_on_expiration_calls_multiple_funcs_in_funcs_on_expire(self):
        """Test that the allocation save method calls a function multiple times when ALLOCATION_FUNCS_ON_EXPIRE has multiple instances of it."""
        allocation = AllocationFactory(status=self.active_status)
        allocation.status = self.expired_status
        allocation.save()
        self.assertEqual(count_invocations.invocation_count, NUMBER_OF_INVOCATIONS)  # type: ignore

    @patch(path_to_allocation_models_funcs_on_expire, list_of_different_expire_funcs())
    def test_on_expiration_calls_multiple_different_funcs_in_funcs_on_expire(self):
        """Test that the allocation save method calls all the different functions present in the list ALLOCATION_FUNCS_ON_EXPIRE."""
        allocation = AllocationFactory(status=self.active_status)
        allocation.status = self.expired_status

        # the last function in the list is allocation_func_on_expire_exception, which raises an exception
        with self.assertRaises(AllocationFuncOnExpireException):
            allocation.save()

        # the other functions will have been called a different number of times depending on whether NUMBER_OF_INVOCATIONS is odd or even
        if NUMBER_OF_INVOCATIONS % 2 == 0:
            expected_positive_invocations = NUMBER_OF_INVOCATIONS // 2
            expected_negative_invocations = -((NUMBER_OF_INVOCATIONS // 2) - 1)
            self.assertEqual(count_invocations.invocation_count, expected_positive_invocations)  # type: ignore
            self.assertEqual(count_invocations_negative.invocation_count, expected_negative_invocations)  # type: ignore
        else:
            expected_positive_invocations = NUMBER_OF_INVOCATIONS // 2
            expected_negative_invocations = -(NUMBER_OF_INVOCATIONS // 2)
            self.assertEqual(count_invocations.invocation_count, expected_positive_invocations)  # type: ignore
            self.assertEqual(count_invocations_negative.invocation_count, expected_negative_invocations)  # type: ignore

    @patch(path_to_allocation_models_funcs_on_expire, list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_no_expire_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is not expired."""
        allocation = AllocationFactory(status=self.active_status)
        allocation.save()

    @patch(path_to_allocation_models_funcs_on_expire, list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_allocation_changed_but_always_expired_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is always expired."""
        allocation = AllocationFactory(status=self.expired_status)
        allocation.justification = "This allocation is always expired."
        allocation.save()

    @patch(path_to_allocation_models_funcs_on_expire, list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_allocation_changed_but_never_expired_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is never expired."""
        allocation = AllocationFactory(status=self.active_status)
        allocation.status = self.other_status
        allocation.save()

    @patch(path_to_allocation_models_funcs_on_expire, list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_allocation_always_expired_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is always expired."""
        allocation = AllocationFactory(status=self.expired_status)
        allocation.justification = "This allocation is always expired."
        allocation.save()

    @patch(path_to_allocation_models_funcs_on_expire, list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_allocation_reactivated_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is reactivated."""
        allocation = AllocationFactory(status=self.expired_status)
        allocation.status = self.active_status
        allocation.save()

    @patch(path_to_allocation_models_funcs_on_expire, list())
    def test_new_allocation_is_in_database(self):
        """Test that a new allocation is saved in the database."""
        allocation: Allocation = AllocationFactory(status=self.active_status)
        allocation.save()
        self.assertTrue(Allocation.objects.filter(id=allocation.id).exists())

    @patch(path_to_allocation_models_funcs_on_expire, list())
    def test_multiple_new_allocations_are_in_database(self):
        """Test that multiple new allocations are saved in the database."""
        allocations = [AllocationFactory(status=self.active_status) for _ in range(25)]
        for allocation in allocations:
            self.assertTrue(Allocation.objects.filter(id=allocation.id).exists())


class AllocationModelExpiresInTests(TestCase):
    mocked_today = datetime.date(2025, 1, 1)
    three_years_after_mocked_today = datetime.date(2028, 1, 1)
    four_years_after_mocked_today = datetime.date(2029, 1, 1)

    def test_end_date_is_today_returns_zero(self):
        """Test that the expires_in method returns 0 when the end date is today."""
        allocation: Allocation = AllocationFactory(end_date=timezone.now().date())
        self.assertEqual(allocation.expires_in, 0)

    def test_end_date_tomorrow_returns_one(self):
        """Test that the expires_in method returns 1 when the end date is tomorrow."""
        tomorrow: datetime.date = (timezone.now() + datetime.timedelta(days=1)).date()
        allocation: Allocation = AllocationFactory(end_date=tomorrow)
        self.assertEqual(allocation.expires_in, 1)

    def test_end_date_yesterday_returns_negative_one(self):
        """Test that the expires_in method returns -1 when the end date is yesterday."""
        yesterday: datetime.date = (timezone.now() - datetime.timedelta(days=1)).date()
        allocation: Allocation = AllocationFactory(end_date=yesterday)
        self.assertEqual(allocation.expires_in, -1)

    def test_end_date_one_week_ago_returns_negative_seven(self):
        """Test that the expires_in method returns -7 when the end date is one week ago."""
        days_in_a_week: int = 7
        one_week_ago: datetime.date = (timezone.now() - datetime.timedelta(days=days_in_a_week)).date()
        allocation: Allocation = AllocationFactory(end_date=one_week_ago)
        self.assertEqual(allocation.expires_in, -days_in_a_week)

    def test_end_date_in_one_week_returns_seven(self):
        """Test that the expires_in method returns 7 when the end date is in one week."""
        days_in_a_week: int = 7
        one_week_from_now: datetime.date = (timezone.now() + datetime.timedelta(days=days_in_a_week)).date()
        allocation: Allocation = AllocationFactory(end_date=one_week_from_now)
        self.assertEqual(allocation.expires_in, days_in_a_week)

    def test_end_date_in_three_years_without_leap_day_returns_days_including_no_leap_day(self):
        """Test that the expires_in method returns the correct number of days in three years when those years did not have a leap year."""
        days_in_three_years_excluding_leap_year = 365 * 3

        with patch("coldfront.core.allocation.models.datetime") as mock_datetime:
            mock_datetime.date.today.return_value = self.mocked_today

            allocation: Allocation = AllocationFactory(end_date=self.three_years_after_mocked_today)

            self.assertEqual(allocation.expires_in, days_in_three_years_excluding_leap_year)

    def test_end_date_in_four_years_returns_days_including_leap_day(self):
        """Test that the expires_in method accounts for the extra day of a leap year."""
        days_in_four_years_including_leap_year = (365 * 4) + 1

        with patch("coldfront.core.allocation.models.datetime") as mock_datetime:
            mock_datetime.date.today.return_value = self.mocked_today

            allocation: Allocation = AllocationFactory(end_date=self.four_years_after_mocked_today)

            self.assertEqual(allocation.expires_in, days_in_four_years_including_leap_year)


class AllocationModelGetInformationTests(TestCase):
    path_to_allocation_models_allocation_attribute_view_list: str = (
        "coldfront.core.allocation.models.ALLOCATION_ATTRIBUTE_VIEW_LIST"
    )

    def test_no_allocation_attributes_returns_empty_string(self):
        """Test that the get_information method returns an empty string if there are no allocation attributes."""
        allocation: Allocation = AllocationFactory()
        self.assertEqual(allocation.get_information, "")

    @patch(path_to_allocation_models_allocation_attribute_view_list, list())
    def test_attribute_type_not_in_view_list_returns_empty_string(self):
        """Test that the get_information method returns an empty string if the attribute type is not in ALLOCATION_ATTRIBUTE_VIEW_LIST."""
        allocation: Allocation = AllocationFactory()
        self.assertEqual(allocation.get_information, "")

    def test_attribute_value_is_zero_returns_100_percent_string(self):
        allocation: Allocation = AllocationFactory()
        allocation_attribute: AllocationAttribute = AllocationAttributeFactory(allocation=allocation, value=0)
        allocation_attribute_usage = AllocationAttributeUsageFactory(
            allocation_attribute=allocation_attribute, value=10
        )

        allocation_attribute_type_name: str = allocation_attribute.allocation_attribute_type.name
        allocation_attribute_usage_value: float = float(allocation_attribute_usage.value)
        allocation_attribute_value: str = allocation_attribute.value
        expected_percent = 100

        expected_information: SafeString = format_html(
            "{}: {}/{} ({} %) <br>",
            allocation_attribute_type_name,
            allocation_attribute_usage_value,
            allocation_attribute_value,
            expected_percent,
        )

        self.assertEqual(allocation.get_information, expected_information)

    def test_multiple_attributes_with_same_type_returns_combined_information(self):
        """Test that the get_information method returns combined information for multiple attributes."""
        allocation: Allocation = AllocationFactory()
        allocation_attribute_type = AllocationAttributeTypeFactory()

        allocation_attribute_1: AllocationAttribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=allocation_attribute_type, value=100
        )
        allocation_attribute_2: AllocationAttribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=allocation_attribute_type, value=1000
        )
        allocation_attribute_usage_1 = AllocationAttributeUsageFactory(
            allocation_attribute=allocation_attribute_1, value=50
        )
        allocation_attribute_usage_2 = AllocationAttributeUsageFactory(
            allocation_attribute=allocation_attribute_2, value=500
        )

        percent_1 = (
            round((float(allocation_attribute_usage_1.value) / float(allocation_attribute_1.value)) * 10_000) / 100
        )
        percent_2 = (
            round((float(allocation_attribute_usage_2.value) / float(allocation_attribute_2.value)) * 10_000) / 100
        )

        expected_information: SafeString = format_html(
            "{}: {}/{} ({} %) <br>{}: {}/{} ({} %) <br>",
            allocation_attribute_type.name,
            float(allocation_attribute_usage_1.value),
            allocation_attribute_1.value,
            percent_1,
            allocation_attribute_type.name,
            float(allocation_attribute_usage_2.value),
            allocation_attribute_2.value,
            percent_2,
        )

        self.assertEqual(allocation.get_information, expected_information)
