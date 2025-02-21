"""Unit tests for the allocation models"""

from django.test import TestCase
from django.core.exceptions import ValidationError

from coldfront.core.test_helpers.factories import setup_models, AllocationFactory

UTIL_FIXTURES = [
        "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]


class AllocationModelTests(TestCase):
    """tests for Allocation model"""
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Set up allocation to test model properties and methods"""
        setup_models(cls)

    def test_allocation_str(self):
        """test that allocation str method returns correct string"""
        allocation_str = '%s (%s)' % (
            self.storage_allocation.get_parent_resource.name,
            self.storage_allocation.project.pi
        )
        self.assertEqual(str(self.storage_allocation), allocation_str)


    def test_allocation_usage_property(self):
        """Test that allocation usage property displays correctly"""
        self.assertEqual(self.storage_allocation.usage, 10)

    def test_allocation_usage_property_na(self):
        """Create allocation with no usage. Usage property should return None"""
        allocation = AllocationFactory()
        self.assertIsNone(allocation.usage)

class AllocationAttributeModelTests(TestCase):
    """Tests for allocationattribute models"""
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Set up allocationattribute to test model properties and methods"""
        setup_models(cls)
        cls.allocationattribute = cls.storage_allocation.allocationattribute_set.get(
            allocation_attribute_type__name='Storage Quota (TB)'
        )

    def test_allocationattribute_clean_no_error(self):
        """cleaning a numeric value for an int or float AllocationAttributeType produces no error"""
        self.allocationattribute.value = "1000"
        self.allocationattribute.clean()

    def test_allocationattribute_clean_nonnumeric_error(self):
        """cleaning a non-numeric value for int or float AllocationAttributeTypes returns an informative error message"""

        self.allocationattribute.value = "1000TB"
        with self.assertRaisesMessage(ValidationError, 'Value must be entirely numeric. Please remove any non-numeric characters.'):
            self.allocationattribute.clean()
