# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

import datetime
import pickle

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttributeUsage,
    AllocationStatusChoice,
)
from coldfront.core.project.models import Project
from coldfront.core.test_helpers.factories import (
    AllocationAttributeFactory,
    AllocationAttributeTypeFactory,
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


class AllocationModelSetUsageTests(TestCase):
    def test_aattribute_type__name_not_found_do_nothing(self):
        """When this Allocation has no associated AllocationAttribute with an associated AllocationAttributeType.name equal to type_name then do nothing."""
        name_to_set_usage_of = "Name A"
        not_name_to_set_usage_of = "Name B"
        allocation = AllocationFactory()
        allocation_attribute_type = AllocationAttributeTypeFactory(name=not_name_to_set_usage_of, has_usage=True)

        # This will create an associated AllocationAttributeUsage when save()'d
        allocation_attribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=allocation_attribute_type
        )

        usages = AllocationAttributeUsage.objects.filter(allocation_attribute=allocation_attribute)
        self.assertEqual(len(usages), 1)
        usage_to_not_change: AllocationAttributeUsage = usages[0]
        before_usage_to_not_change_value = usage_to_not_change.value

        # since this set_usage() should just be a nop, nothing should change
        before_pickled_allocation = pickle.dumps(allocation.refresh_from_db())
        before_pickled_allocation_attribute_type = pickle.dumps(allocation_attribute_type.refresh_from_db())
        before_pickled_allocation_attribute = pickle.dumps(allocation_attribute.refresh_from_db())
        before_pickled_usage_b = pickle.dumps(usage_to_not_change.refresh_from_db())

        new_different_value = (
            (before_usage_to_not_change_value * 0.75) if not before_usage_to_not_change_value == 0 else 1
        )

        allocation.set_usage(name_to_set_usage_of, new_different_value)

        usage_to_not_change.refresh_from_db()
        self.assertEqual(usage_to_not_change.value, before_usage_to_not_change_value)

        after_pickled_allocation = pickle.dumps(allocation.refresh_from_db())
        after_pickled_allocation_attribute_type = pickle.dumps(allocation_attribute_type.refresh_from_db())
        after_pickled_allocation_attribute = pickle.dumps(allocation_attribute.refresh_from_db())
        after_pickled_usage_b = pickle.dumps(usage_to_not_change.refresh_from_db())

        self.assertEqual(before_pickled_allocation, after_pickled_allocation)
        self.assertEqual(before_pickled_allocation_attribute_type, after_pickled_allocation_attribute_type)
        self.assertEqual(before_pickled_allocation_attribute, after_pickled_allocation_attribute)
        self.assertEqual(before_pickled_usage_b, after_pickled_usage_b)

    def test_aattribute_type__name_found_but_has_no_usage_do_nothing(self):
        """When this Allocation has an associated AllocationAttribute but with an associated AllocationAttributeType.name equal to type_name but its has_usage is False, do nothing."""
        type_name = "Example Name"
        new_value = 0.56
        not_type_name = "Not Example Name"
        allocation = AllocationFactory()
        allocation_attribute_type = AllocationAttributeTypeFactory(name=not_type_name, has_usage=False)
        allocation_attribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=allocation_attribute_type
        )

        before_pickled_allocation = pickle.dumps(allocation.refresh_from_db())
        before_pickled_allocation_attribute_type = pickle.dumps(allocation_attribute_type.refresh_from_db())
        before_pickled_allocation_attribute = pickle.dumps(allocation_attribute.refresh_from_db())

        allocation.set_usage(type_name, new_value)

        after_pickled_allocation = pickle.dumps(allocation.refresh_from_db())
        after_pickled_allocation_attribute_type = pickle.dumps(allocation_attribute_type.refresh_from_db())
        after_pickled_allocation_attribute = pickle.dumps(allocation_attribute.refresh_from_db())

        self.assertFalse(AllocationAttributeUsage.objects.filter(allocation_attribute=allocation_attribute).exists())

        self.assertEqual(before_pickled_allocation, after_pickled_allocation)
        self.assertEqual(before_pickled_allocation_attribute_type, after_pickled_allocation_attribute_type)
        self.assertEqual(before_pickled_allocation_attribute, after_pickled_allocation_attribute)

    def test_aattribute_type__name_found_and_has_usage_but_has_no_aattributeusage_new_aattributeusage_object_created(
        self,
    ):
        """When this Allocation has an associated AllocationAttribute with an associated AllocationAttributeType.name equal to type_name
        and its has_usage is True but the AllocationAttribute has no associated AllocationAttributeUsage,
        then create a new  AllocationAttributeUsage and set its value to value."""
        type_name = "This is a super cool type name!"
        new_value = 0.87

        allocation = AllocationFactory()
        allocation_attribute_type = AllocationAttributeTypeFactory(name=type_name, has_usage=True)
        allocation_attribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=allocation_attribute_type
        )

        # Make sure that the default AllocationAttributeUsage created by AllocationAttribute is removed
        AllocationAttributeUsage.objects.all().delete()

        sanity_check_value_of_allocation_attribute_usages = 0
        number_of_allocation_attribute_usages = AllocationAttributeUsage.objects.filter(
            allocation_attribute=allocation_attribute
        ).count()
        self.assertEqual(sanity_check_value_of_allocation_attribute_usages, number_of_allocation_attribute_usages)

        allocation.set_usage(type_name, new_value)

        usages_belonging_to_allocation_attribute = AllocationAttributeUsage.objects.filter(
            allocation_attribute=allocation_attribute
        )
        new_number_of_allocation_attribute_usages = usages_belonging_to_allocation_attribute.count()
        expected_number_of_allocation_attribute_usages = 1
        self.assertEqual(new_number_of_allocation_attribute_usages, expected_number_of_allocation_attribute_usages)

        usage = usages_belonging_to_allocation_attribute[0]

        self.assertEqual(usage.value, new_value)

    def test_aattribute_type__name_found_and_has_usage_but_has_aattributeusage_object_not_created(self):
        """When this Allocation has an associated AllocationAttribute with an associated AllocationAttributeType.name equal to type_name
        and its has_usage is True and the AllocationAttribute has an associated AllocationAttributeUsage,
        then set the value of that AllocationAttributeUsage to value."""
        type_name = "<name>"
        new_value = 758787.245228374

        allocation = AllocationFactory()
        allocation_attribute_type = AllocationAttributeTypeFactory(name=type_name, has_usage=True)
        allocation_attribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=allocation_attribute_type
        )

        sanity_check_value_of_allocation_attribute_usages = 1
        before_usages = AllocationAttributeUsage.objects.filter(allocation_attribute=allocation_attribute)
        before_num_of_usages = before_usages.count()
        self.assertEqual(sanity_check_value_of_allocation_attribute_usages, before_num_of_usages)

        before_pk = before_usages[0].pk

        allocation.set_usage(type_name, new_value)

        after_usages = AllocationAttributeUsage.objects.filter(allocation_attribute=allocation_attribute)
        new_number_of_allocation_attribute_usages = after_usages.count()
        expected_number_of_allocation_attribute_usages = 1
        self.assertEqual(new_number_of_allocation_attribute_usages, expected_number_of_allocation_attribute_usages)

        after_usage = after_usages[0]
        after_pk = after_usage.pk

        self.assertEqual(after_usage.value, new_value)
        self.assertEqual(before_pk, after_pk)
