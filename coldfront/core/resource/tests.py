from django.test import TestCase

from coldfront.config.defaults import RESOURCE_DEFAULTS as defaults
from coldfront.core.test_helpers.utils import CommandTestBase
from coldfront.core.resource.models import (
    ResourceType,
    ResourceAttributeType,
)


class ResourceCommandTests(CommandTestBase):
    """tests for Resource commands"""

    def test_add_resource_defaults_basic(self):
        """Test that add_resource_defaults adds resource defaults"""
        self.assertEqual(ResourceAttributeType.objects.count(), 0)
        self.assertEqual(ResourceType.objects.count(), 0)
        self.call_command('add_resource_defaults')
        self.assertEqual(
            ResourceAttributeType.objects.count(), len(defaults['resourceattrtypes'])
        )
        self.assertEqual(ResourceType.objects.count(), len(defaults['resourcetypes']))
