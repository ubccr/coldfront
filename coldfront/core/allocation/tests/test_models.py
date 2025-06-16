# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

import datetime
from django.utils import timezone

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils.safestring import SafeString

from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
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
        start_date: datetime.date = datetime.datetime(year=2023, month=11, day=2, tzinfo=timezone.get_current_timezone()).date()
        end_date: datetime.date = start_date + datetime.timedelta(days=40)

        actual_allocation: Allocation = AllocationFactory.build(
            status=self.expired_status, start_date=start_date, end_date=end_date, project=self.project
        )
        actual_allocation.full_clean()

    def test_status_is_expired_and_start_date_equals_end_date_no_error(self):
        """Test that an allocation with status 'expired' and start date equal to end date does not raise a validation error."""
        start_and_end_date: datetime.date = datetime.datetime(year=1997, month=4, day=20, tzinfo=timezone.get_current_timezone()).date()
        

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
        start_date: datetime.date = datetime.datetime(year=2001, month=5, day=3, tzinfo=timezone.get_current_timezone()).date()
        end_date: datetime.date = start_date + datetime.timedelta(days=160)

        actual_allocation: Allocation = AllocationFactory.build(
            status=self.active_status, start_date=start_date, end_date=end_date, project=self.project
        )
        actual_allocation.full_clean()

    def test_status_is_active_and_start_date_equals_end_date_no_error(self):
        """Test that an allocation with status 'active' and start date equal to end date does not raise a validation error."""
        start_and_end_date: datetime.date = datetime.datetime(year=2005, month=6, day=3, tzinfo=timezone.get_current_timezone()).date()

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
    count_invocations.invocation_count = getattr(count_invocations, "invocation_count", 0) + 1
    pass


def count_invocations_negative(*args, **kwargs):
    count_invocations_negative.invocation_count = getattr(count_invocations_negative, "invocation_count", 0) - 1
    pass


def list_of_same_expire_funcs(func: callable, size=NUMBER_OF_INVOCATIONS) -> list[str]:
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
    def setUp(self):
        count_invocations.invocation_count = 0
        count_invocations_negative.invocation_count = 0

    @classmethod
    def setUpTestData(cls):
        """Set up allocation to test clean method"""
        cls.active_status: AllocationStatusChoice = AllocationStatusChoiceFactory(name="Active")
        cls.expired_status: AllocationStatusChoice = AllocationStatusChoiceFactory(name="Expired")
        cls.other_status: AllocationStatusChoice = AllocationStatusChoiceFactory(name="Other")
        cls.project: Project = ProjectFactory()

    @override_settings(
        ALLOCATION_FUNCS_ON_EXPIRE=[
            get_dotted_path(allocation_func_on_expire_exception),
        ]
    )
    def test_on_expiration_calls_single_func_in_funcs_on_expire(self):
        """Test that the allocation save method calls the functions specified in ALLOCATION_FUNCS_ON_EXPIRE when it expires."""
        allocation = AllocationFactory(status=self.active_status)
        with self.assertRaises(AllocationFuncOnExpireException):
            allocation.status = self.expired_status
            allocation.save()

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=list_of_same_expire_funcs(count_invocations))
    def test_on_expiration_calls_multiple_funcs_in_funcs_on_expire(self):
        """Test that the allocation save method calls a function multiple times when ALLOCATION_FUNCS_ON_EXPIRE has multiple instances of it."""
        allocation = AllocationFactory(status=self.active_status)
        allocation.status = self.expired_status
        allocation.save()
        self.assertEqual(count_invocations.invocation_count, NUMBER_OF_INVOCATIONS)

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=list_of_different_expire_funcs())
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
            self.assertEqual(count_invocations.invocation_count, expected_positive_invocations)
            self.assertEqual(count_invocations_negative.invocation_count, expected_negative_invocations)
        else:
            expected_positive_invocations = NUMBER_OF_INVOCATIONS // 2
            expected_negative_invocations = -(NUMBER_OF_INVOCATIONS // 2)
            self.assertEqual(count_invocations.invocation_count, expected_positive_invocations)
            self.assertEqual(count_invocations_negative.invocation_count, expected_negative_invocations)

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_no_expire_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is not expired."""
        allocation = AllocationFactory(status=self.active_status)
        allocation.save()

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_allocation_changed_but_always_expired_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is always expired."""
        allocation = AllocationFactory(status=self.expired_status)
        allocation.justification = "This allocation is always expired."
        allocation.save()

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_allocation_changed_but_never_expired_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is never expired."""
        allocation = AllocationFactory(status=self.active_status)
        allocation.status = self.other_status
        allocation.save()

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_allocation_always_expired_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is always expired."""
        allocation = AllocationFactory(status=self.expired_status)
        allocation.justification = "This allocation is always expired."
        allocation.save()

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=list_of_same_expire_funcs(allocation_func_on_expire_exception, 1))
    def test_allocation_reactivated_no_funcs_on_expire_called(self):
        """Test that the allocation save method does not call any functions when the allocation is reactivated."""
        allocation = AllocationFactory(status=self.expired_status)
        allocation.status = self.active_status
        allocation.save()

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=[])
    def test_new_allocation_is_in_database(self):
        """Test that a new allocation is saved in the database."""
        allocation: Allocation = AllocationFactory(status=self.active_status)
        allocation.save()
        self.assertTrue(Allocation.objects.filter(id=allocation.id).exists())

    @override_settings(ALLOCATION_FUNCS_ON_EXPIRE=[])
    def test_multiple_new_allocations_are_in_database(self):
        """Test that multiple new allocations are saved in the database."""
        allocations = [AllocationFactory(status=self.active_status) for _ in range(25)]
        for allocation in allocations:
            self.assertTrue(Allocation.objects.filter(id=allocation.id).exists())


class AllocationModelExpiresInTests(TestCase):
    # going to skip ths until I know how datetimes should be handled
    ...
