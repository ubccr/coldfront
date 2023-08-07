"""Unit tests for the allocation models"""

from django.test import TestCase

from coldfront.core.test_helpers.factories import setup_models, AllocationFactory

UTIL_FIXTURES = [
        "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

class AllocationModelTests(TestCase):
    """tests for Allocation model"""
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Set up project to test model properties and methods"""
        setup_models(cls)

    def test_allocation_str(self):
        """test that allocation str method returns correct string"""
        allocation_str = '%s (%s)' % (
            self.proj_allocation.get_parent_resource.name,
            self.proj_allocation.project.pi
        )

        self.assertEqual(str(self.proj_allocation), allocation_str)

    def test_allocation_usage_property(self):
        """Test that allocation usage property displays correctly"""
        self.assertEqual(self.proj_allocation.usage, 10)

    def test_allocation_usage_property_na(self):
        """Create allocation with no usage. Usage property should return None"""
        allocation = AllocationFactory()
        self.assertIsNone(allocation.usage)
