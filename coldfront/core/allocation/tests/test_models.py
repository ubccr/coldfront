# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

import datetime
import sys
from unittest.mock import patch

import factory
import factory.random
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
)
from coldfront.core.project.models import Project
from coldfront.core.test_helpers.factories import (
    AAttributeTypeFactory,
    AllocationAttributeFactory,
    AllocationAttributeTypeFactory,
    AllocationFactory,
    AllocationStatusChoiceFactory,
    ProjectFactory,
    ResourceAttributeFactory,
    ResourceAttributeTypeFactory,
    ResourceFactory,
    UserFactory,
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
        end_date_in_the_future: datetime.date = datetime.date.today() + datetime.timedelta(days=1)
        actual_allocation: Allocation = AllocationFactory.build(
            status=self.expired_status, end_date=end_date_in_the_future, project=self.project
        )
        with self.assertRaises(ValidationError):
            actual_allocation.full_clean()

    def test_status_is_expired_and_start_date_after_end_date_has_validation_error(self):
        """Test that an allocation with status 'expired' and start date after end date raises a validation error."""
        end_date: datetime.date = datetime.date.today() + datetime.timedelta(days=1)
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
        end_date: datetime.date = datetime.date.today() + datetime.timedelta(days=1)
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


class AllocationAttributeModelCleanMethodTests(TestCase):
    def _test_clean(
        self, allocation_attribute_type_name: str, allocation_attribute_values: list, expect_validation_error: bool
    ):
        attribute_type = AAttributeTypeFactory(name=allocation_attribute_type_name)
        allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=attribute_type)
        allocation_attribute = AllocationAttributeFactory(allocation_attribute_type=allocation_attribute_type)
        for value in allocation_attribute_values:
            with self.subTest(value=value):
                if not isinstance(value, str):
                    raise TypeError("allocation attribute value must be a string")
                allocation_attribute.value = value
                if expect_validation_error:
                    with self.assertRaises(ValidationError):
                        allocation_attribute.clean()
                else:
                    allocation_attribute.clean()

    def test_expect_int_given_int(self):
        self._test_clean("Int", ["-1", "0", "1", str(sys.maxsize)], False)

    def test_expect_int_given_float(self):
        self._test_clean("Int", ["-1.0", "0.0", "1.0", "2e30"], True)

    def test_expect_int_given_garbage(self):
        self._test_clean("Int", ["foobar", "", " ", "\0", "1j"], True)

    def test_expect_float_given_int(self):
        self._test_clean("Float", ["-1", "0", "1", str(sys.maxsize)], False)

    def test_expect_float_given_float(self):
        self._test_clean("Float", ["-1.0", "0.0", "1.0", "2e30"], False)

    def test_expect_float_given_garbage(self):
        self._test_clean("Float", ["foobar", "", " ", "\0", "1j"], True)

    def test_expect_yes_no_given_yes_no(self):
        self._test_clean("Yes/No", ["Yes", "No"], False)

    def test_expect_yes_no_given_garbage(self):
        self._test_clean("Yes/No", ["foobar", "", " ", "\0", "1", "1.0", "2e30", "1j", "yes", "no", "YES", "NO"], True)

    def test_expect_date_given_date(self):
        self._test_clean("Date", ["1970-01-01"], False)

    def test_expect_date_given_garbage(self):
        self._test_clean("Date", ["foobar", "", " ", "\0", "1", "1.0", "2e30", "1j"], True)


class AllocationModelStrTests(TestCase):
    """Tests for Allocation.__str__"""

    def setUp(self):
        self.allocation = AllocationFactory()
        self.resource = ResourceFactory()
        self.allocation.resources.add(self.resource)

    def test_allocation_str_only_contains_parent_resource_and_project_pi(self):
        """Test that the allocation's str only contains self.allocation.get_parent_resource.name and self.allocation.project.pi"""
        parent_resource_name: str = self.allocation.get_parent_resource.name
        project_pi: str = self.allocation.project.pi
        expected: str = f"{parent_resource_name} ({project_pi})"
        actual = str(self.allocation)
        self.assertEqual(actual, expected)

    def test_parent_resource_name_updated_changes_str(self):
        """Test that when the name of the parent resource changes the str changes"""
        project_pi: str = self.allocation.project.pi

        new_name: str = "This is the new name"
        self.resource.name = new_name
        self.resource.save()

        expected: str = f"{new_name} ({project_pi})"
        actual = str(self.allocation)
        self.assertEqual(actual, expected)

    def test_project_pi_name_updated_changes_str(self):
        """Test that if the name of the PI is updated that the str changes"""
        pi: User = self.allocation.project.pi
        new_username: str = "This is a new username!"
        pi.username = new_username
        pi.save()

        parent_resource_name: str = self.allocation.get_parent_resource.name
        expected: str = f"{parent_resource_name} ({pi})"
        actual = str(self.allocation)
        self.assertEqual(actual, expected)

    def test_parent_resource_changed_changes_str(self):
        """When the original parent resource is removed and replaced with another the str changes"""
        original_pi: User = self.allocation.project.pi

        original_string = str(self.allocation)

        self.allocation.resources.clear()
        new_resource = ResourceFactory()
        self.allocation.resources.add(new_resource)
        new_string = str(self.allocation)

        expected_new_string = f"{new_resource.name} ({original_pi})"

        self.assertNotEqual(original_string, new_string)
        self.assertIn(new_string, expected_new_string)

    def test_project_changed_changes_str(self):
        """When the project associated with this allocation changes the str should change"""
        original_string = str(self.allocation)

        new_project = ProjectFactory()
        self.allocation.project = new_project
        self.allocation.save()

        new_string = str(self.allocation)
        expected_new_string = f"{self.resource.name} ({new_project.pi})"

        self.assertNotEqual(original_string, new_string)
        self.assertEqual(new_string, expected_new_string)

    def test_project_pi_changed_changes_str(self):
        """When the project associated with this allocation has its PI change the str should change"""
        original_string = str(self.allocation)

        new_pi = UserFactory()
        self.allocation.project.pi = new_pi
        self.allocation.save()

        new_string = str(self.allocation)
        expected_new_string = f"{self.resource.name} ({new_pi})"

        self.assertNotEqual(original_string, new_string)
        self.assertEqual(new_string, expected_new_string)


class AllocationModelExpiresInTests(TestCase):
    mocked_today = datetime.date(2025, 1, 1)
    three_years_after_mocked_today = datetime.date(2028, 1, 1)
    four_years_after_mocked_today = datetime.date(2029, 1, 1)

    def test_end_date_is_today_returns_zero(self):
        """Test that the expires_in method returns 0 when the end date is today."""
        allocation: Allocation = AllocationFactory(end_date=datetime.date.today())
        self.assertEqual(allocation.expires_in, 0)

    def test_end_date_tomorrow_returns_one(self):
        """Test that the expires_in method returns 1 when the end date is tomorrow."""
        tomorrow: datetime.date = datetime.date.today() + datetime.timedelta(days=1)
        allocation: Allocation = AllocationFactory(end_date=tomorrow)
        self.assertEqual(allocation.expires_in, 1)

    def test_end_date_yesterday_returns_negative_one(self):
        """Test that the expires_in method returns -1 when the end date is yesterday."""
        yesterday: datetime.date = datetime.date.today() - datetime.timedelta(days=1)
        allocation: Allocation = AllocationFactory(end_date=yesterday)
        self.assertEqual(allocation.expires_in, -1)

    def test_end_date_one_week_ago_returns_negative_seven(self):
        """Test that the expires_in method returns -7 when the end date is one week ago."""
        days_in_a_week: int = 7
        one_week_ago: datetime.date = datetime.date.today() - datetime.timedelta(days=days_in_a_week)
        allocation: Allocation = AllocationFactory(end_date=one_week_ago)
        self.assertEqual(allocation.expires_in, -days_in_a_week)

    def test_end_date_in_one_week_returns_seven(self):
        """Test that the expires_in method returns 7 when the end date is in one week."""
        days_in_a_week: int = 7
        one_week_from_now: datetime.date = datetime.date.today() + datetime.timedelta(days=days_in_a_week)
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


class AllocationModelGetEulaTests(TestCase):
    def test_no_resources_with_eula_attribute_does_nothing(self):
        """
        Test that None is returned when there are no Resources associated
        with this allocation that have any ResourceAttributes with a ResourceAttributeType of 'eula'.
        """
        allocation = AllocationFactory()

        magic_number = 10
        non_eula_resources = []
        for i in range(magic_number):
            non_eula_resource = ResourceFactory()
            non_eula_resource_attribute_type = ResourceAttributeTypeFactory(name=f"noteula #{i}")
            non_eula_resource_attribute = ResourceAttributeFactory(  # noqa: F841
                resource=non_eula_resource, resource_attribute_type=non_eula_resource_attribute_type
            )
            non_eula_resources.append(non_eula_resource)

        allocation.resources.add(*non_eula_resources)

        actual = allocation.get_eula()

        self.assertIsNone(actual)

    def test_only_resources_with_eula_for_other_allocations_returns_none(self):
        """
        Test that None is returned when there are other allocations with eulas but
        this allocation does not have any Resources with a eula.
        """
        num_eulas = 10
        for i in range(num_eulas):
            eula_resource = ResourceFactory()
            eula_resource_attribute_type = ResourceAttributeTypeFactory(name="eula")
            eula_resource_attribute = ResourceAttributeFactory(  # noqa: F841
                resource=eula_resource, resource_attribute_type=eula_resource_attribute_type
            )
            eula_allocation = AllocationFactory(description=f"eula allocation {i}")
            eula_allocation.resources.add(eula_resource)

        non_eula_resource = ResourceFactory()
        non_eula_resource_attribute_type = ResourceAttributeTypeFactory(name="noteula")
        non_eula_resource_attribute = ResourceAttributeFactory(  # noqa: F841
            resource=non_eula_resource, resource_attribute_type=non_eula_resource_attribute_type
        )
        non_eula_allocation = AllocationFactory(description="No eula here.")
        non_eula_allocation.resources.add(non_eula_resource)

        actual = non_eula_allocation.get_eula()

        self.assertIsNone(actual)

    def test_one_resource_with_eula_returns_eula_resource_attribute_expanded_value(self):
        """
        Test that when there is only one Resource with a eula ResourceAttribute
        associated with this allocation that the expanded value for that ResourceAttribute
        is returned.
        """
        eula_resource = ResourceFactory()
        eula_resource_attribute_type = ResourceAttributeTypeFactory(name="eula")
        eula_resource_attribute = ResourceAttributeFactory(
            resource=eula_resource, resource_attribute_type=eula_resource_attribute_type
        )
        eula_allocation = AllocationFactory()
        eula_allocation.resources.add(eula_resource)

        actual = eula_allocation.get_eula()

        self.assertEqual(actual, eula_resource_attribute.expanded_value())

    def test_allocation_with_multiple_resources_still_returns_eula_expanded_value(self):
        """
        Test that when there are multiple other resources with and without eulas
        that one of the expanded_values with a eula is still returned for this Allocation.
        """
        allocation = AllocationFactory()
        num_other_resources = 10
        all_expanded_values = []
        for _ in range(num_other_resources):
            resource = ResourceFactory()
            type_name = factory.random.randgen.choice(["eula", "noteula"])
            resource_attribute_type = ResourceAttributeTypeFactory(name=type_name)
            resource_attribute = ResourceAttributeFactory(
                resource=resource, resource_attribute_type=resource_attribute_type
            )
            all_expanded_values.append(resource_attribute.expanded_value())
            allocation.resources.add(resource)

        guaranteed_resource_with_eula = ResourceFactory()
        guaranteed_resource_attribute_type_with_eula = ResourceAttributeTypeFactory(name="eula")
        guaranteed_resource_attribute_with_eula = ResourceAttributeFactory(
            resource=guaranteed_resource_with_eula, resource_attribute_type=guaranteed_resource_attribute_type_with_eula
        )
        all_expanded_values.append(guaranteed_resource_attribute_with_eula.expanded_value())

        self.assertIn(allocation.get_eula(), all_expanded_values)
