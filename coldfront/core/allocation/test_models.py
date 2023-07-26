"""Unit tests for the allocation models"""

from django.test import TestCase

from coldfront.config.defaults import ALLOCATION_DEFAULTS as defaults
from coldfront.core.allocation.models import AllocationStatusChoice, AllocationAttributeType
from coldfront.core.test_helpers.factories import AllocationFactory, ResourceFactory
from coldfront.core.test_helpers.utils import CommandTestBase


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


class AllocationCommandTests(CommandTestBase):
    """tests for Allocation commands"""

    def test_add_allocation_defaults_basic(self):
        """Test that add_allocation_defaults adds allocation defaults"""
        self.assertEqual(AllocationStatusChoice.objects.count(), 0)
        self.assertEqual(AllocationAttributeType.objects.count(), 0)
        self.call_command('add_allocation_defaults')
        self.assertEqual(
            AllocationStatusChoice.objects.count(),
            len(defaults['statuschoices'])
        )
        self.assertEqual(
            AllocationAttributeType.objects.count(),
            len(defaults['allocationattrtypes'])
        )
