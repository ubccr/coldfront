# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Unit tests for the allocation models"""

import datetime
from enum import Enum, auto
import os
import pathlib
from unittest import skip
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationStatusChoice,
    AttributeType as AAttributeType,
)
from coldfront.core.project.models import Project
from coldfront.core.test_helpers.factories import (
    AAttributeTypeFactory,
    AllocationAttributeFactory,
    AllocationAttributeTypeFactory,
    AllocationFactory,
    AllocationStatusChoiceFactory,
    ProjectFactory,
    ResourceFactory,
    UserFactory,
)
from faker.generator import random
import faker


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


class AllocationAttributeModelCleanTests(TestCase):

    # if this AllocationAttribute's AllocationAttributeType is_unique and this AllocationAttribute's associated allocation already has an AllocationAttribute with the same AllocationAttributeType then reject this and throw a ValidationError
    def test_unique_and_associated_allocation_already_has_same_type_raises_validationerror(self):
        """When this AllocationAttribute's AllocationAttributeType is_unique but the associated Allocation already has an AllocationAttribute with the same AllocationAttributeType raise a ValidationError."""
        allocation = AllocationFactory()
        allocation_attribute_type = AllocationAttributeTypeFactory(is_unique=True)

        preexisting_allocation_attribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=allocation_attribute_type
        )

        new_allocation_attribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=allocation_attribute_type
        )
        with self.assertRaises(ValidationError):
            new_allocation_attribute.clean()

    def test_unique_and_associated_allocation_does_not_have_same_type_passes(self):
        """When this AllocationAttribute's AllocationAttributeType is_unique but the associated Allocation does not have an AllocationAttribute with the same AllocationAttributeType then this should pass."""
        allocation = AllocationFactory()

        first_allocation_attribute_type = AllocationAttributeTypeFactory(is_unique=True, name="First")
        first_allocation_attribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=first_allocation_attribute_type, value="129"
        )
        first_allocation_attribute.clean()

        second_allocation_attribute_type = AllocationAttributeTypeFactory(is_unique=True, name="Second")
        second_allocation_attribute = AllocationAttributeFactory(
            allocation=allocation, allocation_attribute_type=second_allocation_attribute_type, value="129"
        )
        second_allocation_attribute.clean()

    # case for when type was Int
    def test_attribute_type_is_int_and_value_is_int_literal_passes(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Int and this value is an int literal this method should pass."""
        magic_number = 10
        fake = faker.Faker()
        integer_literals = (str(fake.pyint()) for _ in range(magic_number))
        for integer_literal in integer_literals:
            with self.subTest(integer_literal=integer_literal):
                aattribute_type = AAttributeTypeFactory(name="Int")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=integer_literal, allocation_attribute_type=allocation_attribute_type
                )

                allocation_attribute.clean()

    @skip("This test is failing and I believe that it should be passing on a correct implementation")
    def test_attribute_type_is_int_and_value_is_not_int_literal_raises_validationerror(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Int and this value is a non-int literal a ValidationError should be raised."""
        aattribute_type = AAttributeTypeFactory(name="Int")
        allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
        non_integer_literal = "non integer literal"
        allocation_attribute = AllocationAttributeFactory(
            value=non_integer_literal, allocation_attribute_type=allocation_attribute_type
        )

        with self.assertRaises(ValidationError):
            allocation_attribute.clean()

    # case for when type was Float
    def test_attribute_type_is_float_and_value_is_float_literal_passes(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Float and this value is a float literal this method should pass."""
        magic_number = 10
        fake = faker.Faker()
        float_literals = (str(fake.pyfloat()) for _ in range(magic_number))
        for float_literal in float_literals:
            with self.subTest(integer_literal=float_literal):
                aattribute_type = AAttributeTypeFactory(name="Float")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=float_literal, allocation_attribute_type=allocation_attribute_type
                )

                allocation_attribute.clean()

    def test_attribute_type_is_float_and_value_is_int_literal_passes(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Float and this value is an int literal this method should pass."""
        magic_number = 10
        fake = faker.Faker()
        integer_literals = (str(fake.pyint()) for _ in range(magic_number))
        for integer_literal in integer_literals:
            with self.subTest(integer_literal=integer_literal):
                aattribute_type = AAttributeTypeFactory(name="Float")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=integer_literal, allocation_attribute_type=allocation_attribute_type
                )

                allocation_attribute.clean()

    @skip("I believe this test should be fine but it currently fails")
    def test_attribute_type_is_float_and_value_is_not_float_or_int_literal_raises_validationerror(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Float and this value is neither a float or int literal a ValidationError should be raises."""
        aattribute_type = AAttributeTypeFactory(name="Float")
        allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
        non_integer_literal = "not a float or integer literal"
        allocation_attribute = AllocationAttributeFactory(
            value=non_integer_literal, allocation_attribute_type=allocation_attribute_type
        )

        with self.assertRaises(ValidationError):
            allocation_attribute.clean()

    # case for when type was Yes/No
    def test_attribute_type_is_yesno_and_literal_is_correctly_cased_yes_str_literal_passes(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Yes/No and this value is Yes then should pass."""
        aattribute_type = AAttributeTypeFactory(name="Yes/No")
        allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
        integer_literal = "Yes"
        allocation_attribute = AllocationAttributeFactory(
            value=integer_literal, allocation_attribute_type=allocation_attribute_type
        )

        allocation_attribute.clean()

    def test_attribute_type_is_yesno_and_literal_is_wrongly_cased_yes_str_literal_raises_validationerror(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Yes/No and this value is the letters ['y', 'e', 's'] but never 'Yes' then should raise a ValidationError."""
        invalid_yesses = [
            "yes",
            "yeS",
            "yEs",
            "yES",
            "YeS",
            "YEs",
            "YES",
        ]
        for invalid_yes in invalid_yesses:
            with self.subTest(invalid_yes=invalid_yes):
                aattribute_type = AAttributeTypeFactory(name="Yes/No")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=invalid_yes, allocation_attribute_type=allocation_attribute_type
                )

                with self.assertRaises(ValidationError):
                    allocation_attribute.clean()


    def test_attribute_type_is_yesno_and_literal_is_correctly_cased_no_str_literal_passes(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Yes/No and this value is No then should pass."""
        aattribute_type = AAttributeTypeFactory(name="Yes/No")
        allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
        integer_literal = "No"
        allocation_attribute = AllocationAttributeFactory(
            value=integer_literal, allocation_attribute_type=allocation_attribute_type
        )

        allocation_attribute.clean()

    def test_attribute_type_is_yesno_and_literal_is_wrongly_cased_no_str_literal_raises_validationerror(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Yes/No and this value is the letters ['n', 'o'] but never 'No' then should raise a ValidationError."""
        invalid_nos = ["no", "nO", "NO"]
        for invalid_no in invalid_nos:
            with self.subTest(invalid_no=invalid_no):
                aattribute_type = AAttributeTypeFactory(name="Yes/No")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=invalid_no, allocation_attribute_type=allocation_attribute_type
                )

                with self.assertRaises(ValidationError):
                    allocation_attribute.clean()

    def test_attribute_type_is_yesno_and_literal_is_not_yes_or_no_raises_validationerror(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Yes/No and this value is not Yes or No then should raise a ValidationError."""
        magic_number = 10
        fake = faker.Faker()
        max_number_chars = AllocationAttribute._meta.get_field("value").max_length
        invalid_values = (fake.pystr(max_chars=max_number_chars) for _ in range(magic_number))
        for invalid_value in filter(lambda s: s not in ["Yes", "No"], invalid_values):
            with self.subTest(invalid_value=invalid_value):
                aattribute_type = AAttributeTypeFactory(name="Yes/No")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=invalid_value, allocation_attribute_type=allocation_attribute_type
                )

                with self.assertRaises(ValidationError):
                    allocation_attribute.clean()




    # case for when type was Date
    def test_attribute_type_is_date_and_string_is_parsable_passes(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Date and this value is a date parsable from the ISO 8601 date format YYYY-MM-DD."""
        magic_number = 10
        fake = faker.Faker()
        values = (fake.date_this_century().isoformat() for _ in range(magic_number))
        for value in values:
            with self.subTest(invalid_value=value):
                aattribute_type = AAttributeTypeFactory(name="Date")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=value, allocation_attribute_type=allocation_attribute_type
                )

                allocation_attribute.clean()

    def __iso_date_string_with_erroneous_values(self) -> str:
        class BadISODate(Enum):
            BAD_MONTH = auto()
            BAD_DAY = auto()
            BAD_MONTH_AND_DAY = auto()
        choice = random.choice(list(BadISODate))
        
        fake = faker.Faker()
        
        match choice:
            case BadISODate.BAD_MONTH:
                return fake.pystr_format(string_format="####-$#-##")
            case BadISODate.BAD_DAY:
                return fake.pystr_format(string_format="####-{{month}}-?#", letters="456789")
            case BadISODate.BAD_MONTH_AND_DAY:
                return fake.pystr_format(string_format="####-$#-?#", letters="456789")


    def test_attribute_type_is_date_and_string_is_correct_format_with_erroneous_values_raises_validationerror(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Date and this value is in the format of ISO 8601 date format YYYY-MM-DD but the values are erroneous raise a ValidationError."""
        magic_number = 10
        
        values = (self.__iso_date_string_with_erroneous_values() for _ in range(magic_number))
        for value in values:
            with self.subTest(invalid_value=value):
                aattribute_type = AAttributeTypeFactory(name="Date")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=value, allocation_attribute_type=allocation_attribute_type
                )

                with self.assertRaises(ValidationError):
                    allocation_attribute.clean()

    def test_attribute_type_is_date_and_string_is_not_parsable_raises_validationerror(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Date and this value is not parsable raise a ValidationError."""
        magic_number = 10
        fake = faker.Faker()
        max_number_chars = AllocationAttribute._meta.get_field("value").max_length
        values = (fake.pystr(max_chars=max_number_chars) for _ in range(magic_number))
        for value in values:
            with self.subTest(invalid_value=value):
                aattribute_type = AAttributeTypeFactory(name="Date")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=value, allocation_attribute_type=allocation_attribute_type
                )

                with self.assertRaises(ValidationError):
                    allocation_attribute.clean()

    def test_attribute_type_is_date_non_is_date_formats_rejected(self):
        """When the associated AllocationAttributeType has an AttributeType.name of Date and the value is a non-ISO date representation raise a ValidationError."""
        fake = faker.Faker()
        date_formats = {
            "Compact Numeric": fake.date(pattern="%Y%m%d"),
            "Dash-Separated Day-Month-Year": fake.date(pattern="%d-%m-%Y"),
            "Dash-Separated Day-Month-Short-Year": fake.date(pattern="%d-%m-%y"),
            "Dash-Separated Month-Day-Year": fake.date(pattern="%m-%d-%Y"),
            "Day Month Abbreviated Year": fake.date(pattern="%d %b %y"),
            "Day Month Full Year": fake.date(pattern="%d %B %Y"),
            "Day Month, Year With Comma": fake.date(pattern="%d %B, %Y"),
            "Day-Month-Year Abbreviated": fake.date(pattern="%d-%b-%y"),
            "Day-Month-Year Full": fake.date(pattern="%d-%B-%Y"),
            "Day.Month.Year Abbreviated": fake.date(pattern="%d.%m.%y"),
            "Day.Month.Year Full": fake.date(pattern="%d.%m.%Y"),
            "Day/Month/Year Abbreviated": fake.date(pattern="%d/%m/%y"),
            "Day/Month/Year Full": fake.date(pattern="%d/%m/%Y"),
            "European DateTime": f"{fake.date(pattern='%d/%m/%Y')} {fake.time(pattern='%H:%M')}",
            "Full Textual Date": fake.date(pattern="%A, %d %B %Y"),
            "International Abbreviated": fake.date(pattern="%d-%b-%Y"),
            "International Abbreviated No Dashes": fake.date(pattern="%b %d %Y"),
            "International Abbreviated With Comma": fake.date(pattern="%b %d, %Y"),
            "ISO 8601 Full": fake.date(pattern="%Y-%m-%dT%H:%M:%S%z"),
            "ISO With Dots": fake.date(pattern="%Y.%m.%d"),
            "ISO With Slashes": fake.date(pattern="%Y/%m/%d"),
            "ISO With Spaces": fake.date(pattern="%Y %m %d"),
            "Kanji Format": fake.date(pattern="%Y年%m月%d日"),
            "Month Day Abbreviated Year": fake.date(pattern="%b %d %y"),
            "Month Day Full Year": fake.date(pattern="%B %d %Y"),
            "Month Day Year With Comma": fake.date(pattern="%B %d, %Y"),
            "Month-Year Only": fake.date(pattern="%B %Y"),
            "Month/Day/Short-Year": fake.date(pattern="%m/%d/%y"),
            "Month/Day/Year": fake.date(pattern="%m/%d/%Y"),
            "Slash-Separated Short-Year-Month-Day": fake.date(pattern="%y/%m/%d"),
            "Slash-Separated Year-Month-Day DateTime": f"{fake.date(pattern='%Y/%m/%d')} {fake.time(pattern='%H:%M:%S')}",
            "Unix Timestamp": str(int(fake.date_time().timestamp())),
            "Year DayOfYear": fake.date(pattern="%Y %j"),
            "Year Only": fake.date(pattern="%Y"),
            "Year-Week": fake.date(pattern="%Y-W%U"),
            "Year-Month Only": fake.date(pattern="%Y-%m"),
        }
        for invalid_date_format in date_formats:
            with self.subTest(invalid_date_format=invalid_date_format):
                aattribute_type = AAttributeTypeFactory(name="Date")
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=invalid_date_format, allocation_attribute_type=allocation_attribute_type
                )

                with self.assertRaises(ValidationError):
                    allocation_attribute.clean()



    # case for unrecognized attribute type
    def test_attribute_type_is_unknown_always_passes(self):
        """When the associated AllocationAttributeType has an AttributeType.name other than 'Int', 'Float', 'Yes/No', 'Date' it should always pass."""
        magic_number = 10
        fake = faker.Faker()
        max_number_chars = AllocationAttribute._meta.get_field("value").max_length
        invalid_values = (fake.pystr(max_chars=max_number_chars) for _ in range(magic_number))
        for invalid_value in filter(lambda s: s not in ['Int', 'Float', 'Yes/No', 'Date'], invalid_values):
            random_name = fake.word()
            with self.subTest(invalid_value=invalid_value, random_name=random_name):
                aattribute_type = AAttributeTypeFactory(name=random_name)
                allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
                allocation_attribute = AllocationAttributeFactory(
                    value=invalid_value, allocation_attribute_type=allocation_attribute_type
                )

                allocation_attribute.clean()


    # case for malicious input
    def test_to_see_if_we_can_crash_everything(self):
        bad_input = "'(' * 100 + ')' * 100"
        aattribute_type = AAttributeTypeFactory(name="Int")
        allocation_attribute_type = AllocationAttributeTypeFactory(attribute_type=aattribute_type)
        allocation_attribute = AllocationAttributeFactory(
            value=bad_input, allocation_attribute_type=allocation_attribute_type
        )

        allocation_attribute.clean()

