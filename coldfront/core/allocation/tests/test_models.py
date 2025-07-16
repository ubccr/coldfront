# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

import datetime
from unittest import skip
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
)
from coldfront.core.project.models import Project
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


class AllocationModelGetParentResourceTests(TestCase):
    def test_allocation_has_no_resources_none_is_returned(self):
        """Test that an exception is thrown when get_parent_resource is called when the Allocation has no resources."""
        allocation = AllocationFactory()
        self.assertIsNone(allocation.get_parent_resource)

    def test_all_resources_removed_none_is_returned(self):
        """Test that when an Allocation originally has resources but then they are all removed that None is returned."""
        allocation = AllocationFactory()
        magic_constant = 10
        resources = [ResourceFactory() for _ in range(magic_constant)]

        allocation.resources.add(*resources)
        self.assertIsNotNone(allocation.get_parent_resource)

        allocation.resources.remove(*resources)
        self.assertIsNone(allocation.get_parent_resource)

    def test_allocation_has_one_resource_that_resource_is_returned(self):
        """The Allocation's only resource is returned."""
        allocation = AllocationFactory()
        resource = ResourceFactory()
        allocation.resources.add(resource)

        self.assertEqual(resource, allocation.get_parent_resource)

    def test_multiple_allocations_share_one_parent_resource_that_resource_is_returned(self):
        """All Allocations that share the same parent resource return it as parent."""
        magic_constant = 10
        allocations = [AllocationFactory() for _ in range(magic_constant)]

        resource = ResourceFactory()

        for allocation in allocations:
            allocation.resources.add(resource)

        for allocation in allocations:
            with self.subTest(allocation=allocation, resource=resource):
                self.assertEqual(resource, allocation.get_parent_resource)

    def test_other_allocations_have_no_resources_parent_resource_is_returned_no_interference(self):
        """When other Allocations have no resources but this one does, the parent is returned fine and that all the others still return None."""
        magic_constant = 10
        other_allocations = [AllocationFactory() for _ in range(magic_constant)]

        tested_allocation = AllocationFactory()
        resource = ResourceFactory()
        tested_allocation.resources.add(resource)

        self.assertEqual(resource, tested_allocation.get_parent_resource)

        for other_allocation in other_allocations:
            with self.subTest(other_allocation=other_allocation):
                self.assertIsNone(other_allocation.get_parent_resource)

    def test_after_resource_removal_remaining_resource_returned(self):
        allocation = AllocationFactory()
        magic_constant = 10
        all_resources = [ResourceFactory() for _ in range(magic_constant)]

        allocation.resources.add(*all_resources)
        self.assertIsNotNone(allocation.get_parent_resource)

        remaining_resource = all_resources.pop()
        resources_to_remove = all_resources
        allocation.resources.remove(*resources_to_remove)

        self.assertEqual(remaining_resource, allocation.get_parent_resource)

    def test_parent_resource_changed_resource_still_returned(self):
        """Test that making changes to the resource itself does not alter which resource is returned by get_parent_resource."""
        resource = ResourceFactory(name="First Name", is_available=False, is_public=True)

        allocation = AllocationFactory()
        allocation.resources.add(resource)

        original_name = allocation.get_parent_resource.name
        original_is_available = allocation.get_parent_resource.is_available
        original_is_public = allocation.get_parent_resource.is_public
        original_pk = resource.pk

        self.assertEqual(resource.name, original_name)
        self.assertEqual(resource.is_available, original_is_available)
        self.assertEqual(resource.is_public, original_is_public)
        self.assertEqual(resource.pk, original_pk)

        resource.name = changed_name = "A different name"
        resource.is_available = changed_is_available = True
        resource.is_public = changed_is_public = False
        resource.save()

        actual_resource = allocation.get_parent_resource

        self.assertEqual(actual_resource.name, changed_name)
        self.assertEqual(actual_resource.is_available, changed_is_available)
        self.assertEqual(actual_resource.is_public, changed_is_public)
        self.assertEqual(actual_resource.pk, original_pk)

    def test_other_allocation_removed_resource_this_allocation_unchanged(self):
        """Test that an Allocation is not affected when another Allocation removes a shared parent resource as its resource."""
        this_allocation = AllocationFactory()
        other_allocation = AllocationFactory()

        shared_resource = ResourceFactory()
        this_allocation.resources.add(shared_resource)
        other_allocation.resources.add(shared_resource)

        self.assertEqual(this_allocation.get_parent_resource, shared_resource)
        self.assertEqual(other_allocation.get_parent_resource, shared_resource)

        other_allocation.resources.remove(shared_resource)

        self.assertEqual(this_allocation.get_parent_resource, shared_resource)
        self.assertIsNone(other_allocation.get_parent_resource)

    @skip("Currently the setting ALLOCATION_RESOURCE_ORDERING is broken.")
    # @override_settings(ALLOCATION_RESOURCE_ORDERING=["-is_allocatable", "name"])
    @patch("coldfront.core.allocation.models.ALLOCATION_RESOURCE_ORDERING", ["-is_allocatable", "name"])
    def test_multiple_resources_first_by_default_order_is_returned(self):
        resource_1 = ResourceFactory(is_allocatable=True, name="Alice")
        resource_2 = ResourceFactory(is_allocatable=True, name="Daniel")
        resource_3 = ResourceFactory(is_allocatable=False, name="Benjamin")
        resource_4 = ResourceFactory(is_allocatable=False, name="Naomi")
        resource_5 = ResourceFactory(is_allocatable=False, name="Pauline")
        resource_6 = ResourceFactory(is_allocatable=False, name="Zeus")

        allocation = AllocationFactory()
        allocation.resources.add(resource_6, resource_1, resource_2, resource_5, resource_4, resource_3)

        self.assertEqual(resource_1, allocation.get_parent_resource)

    @skip("Currently the setting ALLOCATION_RESOURCE_ORDERING is broken.")
    # @override_settings(ALLOCATION_RESOURCE_ORDERING=["-is_allocatable", "name"])
    @patch(
        "coldfront.core.allocation.models.ALLOCATION_RESOURCE_ORDERING", ["requires_payment", "-is_allocatable", "name"]
    )
    def test_multiple_resources_first_by_custom_order_is_returned(self):
        resource_1 = ResourceFactory(requires_payment=False, is_allocatable=True, name="Daniel")
        resource_2 = ResourceFactory(requires_payment=False, is_allocatable=True, name="Zuri")
        resource_3 = ResourceFactory(requires_payment=False, is_allocatable=False, name="Alexander")
        resource_4 = ResourceFactory(requires_payment=True, is_allocatable=False, name="Naomi")
        resource_5 = ResourceFactory(requires_payment=True, is_allocatable=False, name="Pauline")
        resource_6 = ResourceFactory(requires_payment=True, is_allocatable=False, name="Zeus")

        allocation = AllocationFactory()

        allocation.resources.add(resource_3, resource_6, resource_4, resource_1, resource_2, resource_5)

        self.assertEqual(resource_1, allocation.get_parent_resource)
