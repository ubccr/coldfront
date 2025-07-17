# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
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


class AllocationModelGetInformationTests(TestCase):
    path_to_allocation_models_allocation_attribute_view_list: str = (
        "coldfront.core.allocation.models.ALLOCATION_ATTRIBUTE_VIEW_LIST"
    )

    attribute_usage_formatter_template: str = "{}: {}/{} ({} %) <br>"
    attribute_view_list_formatter_template: str = "{}: {} <br>"

    name_in_view_list_1 = "Something 1"
    name_in_view_list_2 = "Something Else"
    name_not_in_view_list_1 = "This is another thing "
    name_not_in_view_list_2 = "This Is Not In List"
    sample_allocation_attribute_view_list = [name_in_view_list_1, name_in_view_list_2]

    def find_percent(self, numerator, denominator):
        # basically just multiplying be 100 to get percentage
        return round(float(numerator) / float(denominator) * 10000) / 100

    def setUp(self):
        self.allocation = AllocationFactory()

    def test_no_allocation_attributes_returns_empty_string(self):
        """Test that the get_information method returns an empty string if there are no allocation attributes."""
        self.assertEqual(self.allocation.get_information, "")

    @override_settings(ALLOCATION_ATTRIBUTE_VIEW_LIST=sample_allocation_attribute_view_list)
    def test_attribute_type_not_in_view_list_returns_without_type_substring_included(self):
        """Test that the get_information method returns a string without the attribute type substring when the type name is not in ALLOCATION_ATTRIBUTE_VIEW_LIST."""
        allocation_attribute_type = AllocationAttributeTypeFactory(name="Not a name in the view list")
        allocation_attribute = AllocationAttributeFactory(
            allocation_attribute_type=allocation_attribute_type, allocation=self.allocation
        )
        allocation_attribute_usage = AllocationAttributeUsageFactory(allocation_attribute=allocation_attribute)

        expected_percent = self.find_percent(allocation_attribute_usage.value, allocation_attribute.value)

        expected_information: SafeString = format_html(
            self.attribute_usage_formatter_template,
            allocation_attribute_type.name,
            float(allocation_attribute_usage.value),
            allocation_attribute.value,
            expected_percent,
        )

        self.assertHTMLEqual(self.allocation.get_information, expected_information)

    @override_settings(ALLOCATION_ATTRIBUTE_VIEW_LIST=sample_allocation_attribute_view_list)
    def test_attribute_type_in_view_list_returns_with_type_substring_included(self):
        """Test that the get_information method returns a string with the attribute type substring when the type name is in ALLOCATION_ATTRIBUTE_VIEW_LIST."""
        allocation_attribute_type = AllocationAttributeTypeFactory(name=self.name_in_view_list_1)
        allocation_attribute = AllocationAttributeFactory(
            allocation_attribute_type=allocation_attribute_type, allocation=self.allocation
        )
        allocation_attribute_usage = AllocationAttributeUsageFactory(allocation_attribute=allocation_attribute)

        expected_percent = self.find_percent(allocation_attribute_usage.value, allocation_attribute.value)

        regular_substring: SafeString = format_html(
            self.attribute_usage_formatter_template,
            allocation_attribute_type.name,
            float(allocation_attribute_usage.value),
            allocation_attribute.value,
            expected_percent,
        )

        view_list_substring: SafeString = format_html(
            self.attribute_view_list_formatter_template, allocation_attribute_type.name, allocation_attribute.value
        )

        expected_information: SafeString = view_list_substring + regular_substring

        self.assertHTMLEqual(self.allocation.get_information, expected_information)

    def test_attribute_value_is_zero_returns_100_percent_string(self):
        allocation_attribute: AllocationAttribute = AllocationAttributeFactory(allocation=self.allocation, value=0)
        allocation_attribute_usage = AllocationAttributeUsageFactory(
            allocation_attribute=allocation_attribute, value=10
        )

        allocation_attribute_type_name: str = allocation_attribute.allocation_attribute_type.name
        allocation_attribute_usage_value: float = float(allocation_attribute_usage.value)
        allocation_attribute_value: str = allocation_attribute.value
        expected_percent = 100

        expected_information: SafeString = format_html(
            self.attribute_usage_formatter_template,
            allocation_attribute_type_name,
            allocation_attribute_usage_value,
            allocation_attribute_value,
            expected_percent,
        )

        self.assertHTMLEqual(self.allocation.get_information, expected_information)

    def test_multiple_attributes_with_same_type_returns_combined_information(self):
        """Test that the get_information method returns combined information for multiple attributes."""
        allocation_attribute_type = AllocationAttributeTypeFactory()

        allocation_attribute_1: AllocationAttribute = AllocationAttributeFactory(
            allocation=self.allocation, allocation_attribute_type=allocation_attribute_type, value=100
        )
        allocation_attribute_2: AllocationAttribute = AllocationAttributeFactory(
            allocation=self.allocation, allocation_attribute_type=allocation_attribute_type, value=1000
        )
        allocation_attribute_usage_1 = AllocationAttributeUsageFactory(
            allocation_attribute=allocation_attribute_1, value=50
        )
        allocation_attribute_usage_2 = AllocationAttributeUsageFactory(
            allocation_attribute=allocation_attribute_2, value=500
        )

        percent_1 = self.find_percent(allocation_attribute_usage_1.value, allocation_attribute_1.value)
        percent_2 = self.find_percent(allocation_attribute_usage_2.value, allocation_attribute_2.value)

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

        self.assertHTMLEqual(self.allocation.get_information, expected_information)

    @override_settings(ALLOCATION_ATTRIBUTE_VIEW_LIST=sample_allocation_attribute_view_list)
    def test_attributes_with_names_in_view_list_included_in_information(self):
        """Test that only allocations with AttributeTypes whose names are in ALLOCATION_ATTRIBUTE_VIEW_LIST
        have their special snippets also included in the information"""

        # AllocationAttributeTypes whose names are inside of ALLOCATION_ATTRIBUTE_VIEW_LIST
        attribute_type_in_view_list_1 = AllocationAttributeTypeFactory(name=self.name_in_view_list_1)
        attribute_type_in_view_list_2 = AllocationAttributeTypeFactory(name=self.name_in_view_list_2)

        # AllocationAttributeTypes whose names are NOT inside of ALLOCATION_ATTRIBUTE_VIEW_LIST
        attribute_type_not_in_view_list_1 = AllocationAttributeTypeFactory(name=self.name_not_in_view_list_1)
        attribute_type_not_in_view_list_2 = AllocationAttributeTypeFactory(name=self.name_not_in_view_list_2)

        # make unique AllocationAttributes for each AllocationAttributeType, needed for get_information output

        view_list_allocation_attribute_value_1 = 2000
        view_list_allocation_attribute_1 = AllocationAttributeFactory(
            allocation_attribute_type=attribute_type_in_view_list_1,
            value=view_list_allocation_attribute_value_1,
            allocation=self.allocation,
        )

        view_list_allocation_attribute_value_2 = 5000
        view_list_allocation_attribute_2 = AllocationAttributeFactory(
            allocation_attribute_type=attribute_type_in_view_list_2,
            value=view_list_allocation_attribute_value_2,
            allocation=self.allocation,
        )

        no_view_list_allocation_attribute_value_1 = 20
        no_view_list_allocation_attribute_1 = AllocationAttributeFactory(
            allocation_attribute_type=attribute_type_not_in_view_list_1,
            value=no_view_list_allocation_attribute_value_1,
            allocation=self.allocation,
        )

        no_view_list_allocation_attribute_value_2 = 80000
        no_view_list_allocation_attribute_2 = AllocationAttributeFactory(
            allocation_attribute_type=attribute_type_not_in_view_list_2,
            value=no_view_list_allocation_attribute_value_2,
            allocation=self.allocation,
        )

        # make unique AllocationAttributeUsages for each AllocationAttribute, needed for get_information output
        view_list_allocation_attribute_usage_value_1 = 4
        view_list_allocation_attribute_usage_1 = AllocationAttributeUsageFactory(  # noqa: F841
            allocation_attribute=view_list_allocation_attribute_1,
            value=view_list_allocation_attribute_usage_value_1,
        )

        view_list_allocation_attribute_usage_value_2 = 200
        view_list_allocation_attribute_usage_2 = AllocationAttributeUsageFactory(  # noqa: F841
            allocation_attribute=view_list_allocation_attribute_2,
            value=view_list_allocation_attribute_usage_value_2,
        )

        no_view_list_allocation_attribute_usage_value_1 = 5
        no_view_list_allocation_attribute_usage_1 = AllocationAttributeUsageFactory(  # noqa: F841
            allocation_attribute=no_view_list_allocation_attribute_1,
            value=no_view_list_allocation_attribute_usage_value_1,
        )

        no_view_list_allocation_attribute_usage_value_2 = 5
        no_view_list_allocation_attribute_usage_2 = AllocationAttributeUsageFactory(  # noqa: F841
            allocation_attribute=no_view_list_allocation_attribute_2,
            value=no_view_list_allocation_attribute_usage_value_2,
        )

        view_list_percent_1 = self.find_percent(
            view_list_allocation_attribute_usage_value_1, view_list_allocation_attribute_value_1
        )
        view_list_percent_2 = self.find_percent(
            view_list_allocation_attribute_usage_value_2, view_list_allocation_attribute_value_2
        )
        no_view_list_percent_1 = self.find_percent(
            no_view_list_allocation_attribute_usage_value_1, no_view_list_allocation_attribute_value_1
        )
        no_view_list_percent_2 = self.find_percent(
            no_view_list_allocation_attribute_usage_value_2, no_view_list_allocation_attribute_value_2
        )

        # Build up the substrings that make up the expected information string

        usage_string_from_view_1: SafeString = format_html(
            self.attribute_usage_formatter_template,
            self.name_in_view_list_1,
            float(view_list_allocation_attribute_usage_value_1),
            view_list_allocation_attribute_value_1,
            view_list_percent_1,
        )

        usage_string_from_view_2: SafeString = format_html(
            self.attribute_usage_formatter_template,
            self.name_in_view_list_2,
            float(view_list_allocation_attribute_usage_value_2),
            view_list_allocation_attribute_value_2,
            view_list_percent_2,
        )

        usage_string_from_no_view_1: SafeString = format_html(
            self.attribute_usage_formatter_template,
            self.name_not_in_view_list_1,
            float(no_view_list_allocation_attribute_usage_value_1),
            no_view_list_allocation_attribute_value_1,
            no_view_list_percent_1,
        )

        usage_string_from_no_view_2: SafeString = format_html(
            self.attribute_usage_formatter_template,
            self.name_not_in_view_list_2,
            float(no_view_list_allocation_attribute_usage_value_2),
            no_view_list_allocation_attribute_value_2,
            no_view_list_percent_2,
        )

        typename_string_from_view_1: SafeString = format_html(
            self.attribute_view_list_formatter_template,
            view_list_allocation_attribute_1.allocation_attribute_type.name,
            view_list_allocation_attribute_1.value,
        )

        typename_string_from_view_2: SafeString = format_html(
            self.attribute_view_list_formatter_template,
            view_list_allocation_attribute_2.allocation_attribute_type.name,
            view_list_allocation_attribute_2.value,
        )

        # Finally we can test the values...

        expected_information: SafeString = format_html(
            "{}{}{}{}{}{}",
            typename_string_from_view_1,
            usage_string_from_view_1,
            typename_string_from_view_2,
            usage_string_from_view_2,
            usage_string_from_no_view_1,
            usage_string_from_no_view_2,
        )

        actual_information: SafeString = self.allocation.get_information

        # with open('output2.txt', 'w') as f:
        #     print(f'expected: \n\n{expected_information}', file=f)
        #     print("\n", file=f)
        #     print(f'actual: \n\n{actual_information}', file=f)

        self.assertHTMLEqual(expected_information, actual_information)
