# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

import datetime
from unittest import skip
from collections.abc import Iterable
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
)
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.core.test_helpers.factories import (
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

class AllocationModelGetResourcesAsStringTests(TestCase):

    @skip("Is it ever valid to have an allocation without a resource? This constraint is not enforced and this test does work. ")
    def test_no_resources_with_allocation_returns_empty_string(self):
        """Test that when an Allocation has no resources that the empty string is returned."""
        allocation = AllocationFactory()
        expected = ""
        self.assertEqual(expected, allocation.get_resources_as_string)

    def test_single_resource_with_allocation_returns_just_resource_name(self):
        """Test that when an Allocation only has a single resource associated with it just the name of that Resource is returned."""
        allocation = AllocationFactory()
        resource = ResourceFactory()
        allocation.resources.add(resource)
        expected = resource.name
        self.assertEqual(expected, allocation.get_resources_as_string)

    def test_two_resources_with_allocation_returns_string_with_both_separated_by_one_comma(self):
        """Test that when two separate resources as associated with an Allocation that both names are returned in the string separated by a comma. """
        allocation = AllocationFactory()
        resource_1 = ResourceFactory()
        resource_2 = ResourceFactory()
        allocation.resources.add(resource_1, resource_2)

        expected_characters: Iterable = f"{resource_1.name}, {resource_2.name}" 
        actual: str = allocation.get_resources_as_string
        self.assertCountEqual(expected_characters, actual)

        self.assertIn(", ", actual)
        substrings = actual.split(", ")
        self.assertCountEqual(substrings, [resource_1.name, resource_2.name])

    def test_multiple_resources_not_associated_with_allocation_not_included(self):
        allocation = AllocationFactory()
        resource_1 = ResourceFactory(name="this is a super unique name")
        allocation.resources.add(resource_1)

        num_irrelevant_resources = 12
        for _ in range(num_irrelevant_resources):
            irrelevant_resource = ResourceFactory()
        
        resource_2 = ResourceFactory(name="this is another super unique name")
        allocation.resources.add(resource_2)

        expected_characters: Iterable = f"{resource_1.name}, {resource_2.name}" 
        actual: str = allocation.get_resources_as_string
        self.assertCountEqual(expected_characters, actual)

        self.assertIn(", ", actual)
        substrings = actual.split(", ")
        self.assertCountEqual(substrings, [resource_1.name, resource_2.name])

    def test_multiple_allocations_with_a_resource_do_not_conflict(self):
        """Test that when there are multiple Allocations that each have an associated Resource only their respective Resource is included."""
        num_unique_pairs = 14
        pairs: list[tuple[Allocation, Resource]] = []
        for i in range(num_unique_pairs):
            unique_allocation_project = ProjectFactory(title=str(i))
            unique_allocation = AllocationFactory(project=unique_allocation_project)
            unique_resource = ResourceFactory(name=str(i))
            unique_allocation.resources.add(unique_resource)
            pair = (unique_allocation, unique_resource)
            pairs.append(pair)

        for pair in pairs:
            alloc, res = pair
            with self.subTest(alloc=alloc, res=res):
                self.assertEqual(alloc.get_resources_as_string, res.name)


    def test_allocation_with_many_resources_exact_number_names_found_in_string(self):
        allocation = AllocationFactory()
        large_number = 33
        large_number_of_resources = [ResourceFactory(name=str(i)) for i in range(large_number)]

        res_set = set(large_number_of_resources)
        self.assertEqual(large_number, len(res_set))

        allocation.resources.add(*large_number_of_resources)

        resources_as_string = allocation.get_resources_as_string

        expected_number_separators = large_number - 1
        actual_number_separators = resources_as_string.count(", ")
        self.assertEqual(expected_number_separators, actual_number_separators)

        expected_number_resource_names = large_number
        actual_number_resource_names = len(resources_as_string.split(", "))
        self.assertEqual(expected_number_resource_names, actual_number_resource_names)


    @skip("The setting ALLOCATION_RESOURCE_ORDERING is currently broken.")
    # @override_settings(ALLOCATION_RESOURCE_ORDERING=["-is_allocatable", "name"])
    @patch('coldfront.core.allocation.models.ALLOCATION_RESOURCE_ORDERING', ["-is_allocatable", "name"])
    def test_default_allocation_resource_ordering_determines_string_order(self):
        """Test that the string returned is properly ordered when the default value ALLOCATION_RESOURCE_ORDERING=["-is_allocatable", "name"] is used. """
        expected_resource_1 = ResourceFactory(is_allocatable=True, name="Alice")
        expected_resource_2 = ResourceFactory(is_allocatable=True, name="Bob") 
        expected_resource_3 = ResourceFactory(is_allocatable=True, name="Sally")
        expected_resource_4 = ResourceFactory(is_allocatable=False, name="Bart")
        expected_resource_5 = ResourceFactory(is_allocatable=False, name="Charlie")
        allocation = AllocationFactory()
        allocation.resources.add(expected_resource_1, expected_resource_2, expected_resource_3, expected_resource_4, expected_resource_5)

        expected_string = "Alice, Bob, Sally, Bart, Charlie"
        actual_string = allocation.get_resources_as_string

        self.assertEqual(expected_string, actual_string)

    @skip("The setting ALLOCATION_RESOURCE_ORDERING is currently broken.")
    # @override_settings(ALLOCATION_RESOURCE_ORDERING=["-is_available", "-is_public", "name"])
    @patch('coldfront.core.allocation.models.ALLOCATION_RESOURCE_ORDERING', ["-is_available", "-is_public", "name"])
    def test_custom_allocation_resource_ordering_determines_string_order(self):
        """Test that the string returned is properly ordered when a custom value ALLOCATION_RESOURCE_ORDERING is used."""
        expected_resource_1 = ResourceFactory(is_available=True, is_public=True, name="Alice")
        expected_resource_2 = ResourceFactory(is_available=True, is_public=True, name="Bob")
        expected_resource_3 = ResourceFactory(is_available=True, is_public=False, name="Andrew")
        expected_resource_4 = ResourceFactory(is_available=False, is_public=True, name="Charlie")
        expected_resource_5 = ResourceFactory(is_available=False, is_public=True, name="Xavier")
        expected_resource_6 = ResourceFactory(is_available=False, is_public=False, name="Bart")
        expected_resource_7 = ResourceFactory(is_available=False, is_public=False, name="John")

        allocation = AllocationFactory()
        allocation.resources.add(expected_resource_1, expected_resource_2, expected_resource_3, expected_resource_4, expected_resource_5, expected_resource_6, expected_resource_7)

        expected_string = "Alice, Bob, Andrew, Charlie, Xavier, Bart, John"
        actual_string = allocation.get_resources_as_string

        self.assertEqual(expected_string, actual_string)
