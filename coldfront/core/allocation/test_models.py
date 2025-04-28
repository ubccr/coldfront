"""Unit tests for the allocation models"""

from django.test import TestCase
from django.core.exceptions import ValidationError

from coldfront.core.test_helpers.factories import (
    AllocationFactory,
    ResourceFactory,
    AllocationAttributeTypeFactory,
    AllocationAttributeFactory,
)


class AllocationModelTests(TestCase):
    """tests for Allocation model"""

    @classmethod
    def setUpTestData(cls):
        """Set up allocation to test model properties and methods"""
        cls.allocation = AllocationFactory()
        cls.allocation.resources.add(ResourceFactory(name='holylfs07/tier1'))

    def test_allocation_str(self):
        """test that allocation str method returns correct string"""
        allocation_str = '%s (%s)' % (
            self.allocation.get_parent_resource.name,
            self.allocation.project.pi
        )
        self.assertEqual(str(self.allocation), allocation_str)


class AllocationAttributeModelTests(TestCase):
    """Tests for allocationattribute models"""

    @classmethod
    def setUpTestData(cls):
        """Set up allocationattribute to test model properties and methods"""
        cls.allocation = AllocationFactory()
        cls.allocation.resources.add(ResourceFactory(name='holylfs07/tier1'))
        cls.allocationattribute = AllocationAttributeFactory(
            allocation=cls.allocation,
            value = 100,
            allocation_attribute_type=AllocationAttributeTypeFactory(
                name='Storage Quota (TB)'
            ),
        )

    def test_allocationattribute_clean_no_error(self):
        """cleaning numeric value for numeric AllocationAttributeType gives no error
        """
        self.allocationattribute.value = "1000"
        self.allocationattribute.clean()

    def test_allocationattribute_clean_nonnumeric_error(self):
        """cleaning non-numeric value for numeric AllocationAttributeType gives useful error message
        """
        self.allocationattribute.value = "1000TB"
        error = 'Value must be entirely numeric. Please remove any non-numeric characters.'
        with self.assertRaisesMessage(ValidationError, error):
            self.allocationattribute.clean()

    def test_allocationattribute_clean_nonnumeric_error2(self):
        """cleaning non-numeric value for numeric AllocationAttributeType gives useful error message
        """
        self.allocationattribute.value = "150%"
        error = 'Value must be entirely numeric. Please remove any non-numeric characters.'
        with self.assertRaisesMessage(ValidationError, error):
            self.allocationattribute.clean()
