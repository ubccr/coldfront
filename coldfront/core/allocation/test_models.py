"""Unit tests for the allocation models"""

from django.test import TestCase

from coldfront.core.test_helpers.factories import AllocationFactory, ResourceFactory


class AllocationModelTests(TestCase):
    """tests for Allocation model"""

    @classmethod
    def setUpTestData(cls):
        """Set up project to test model properties and methods"""
        cls.allocation = AllocationFactory()
        cls.allocation.resources.add(ResourceFactory(name='holylfs07/tier1'))

    def test_allocation_str(self):
        """test that allocation str method returns correct string"""
        allocation_str = '%s (%s)' % (
            self.allocation.get_parent_resource.name,
            self.allocation.project.pi
        )
        self.assertEqual(str(self.allocation), allocation_str)
