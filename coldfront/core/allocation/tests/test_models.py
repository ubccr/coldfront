# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

from unittest.mock import patch

from django.test import TestCase
from django.utils.html import format_html
from django.utils.safestring import SafeString

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
)
from coldfront.core.test_helpers.factories import (
    AllocationAttributeFactory,
    AllocationAttributeTypeFactory,
    AllocationAttributeUsageFactory,
    AllocationFactory,
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
