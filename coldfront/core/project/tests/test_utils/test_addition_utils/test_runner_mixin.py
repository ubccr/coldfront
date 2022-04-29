from coldfront.core.allocation.models import AllocationAttributeType


class TestRunnerMixin(object):
    """A mixin for testing AllocationAdditionRequest-related runners."""

    def assert_allocation_service_units_values(self, allocation,
                                               expected_value,
                                               expected_usage):
        """Assert that the given Allocation has an AllocationAttribute
        with type 'Service Units' and the given expected value and the
        given expected usage."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        kwargs = {
            'allocation_attribute_type': allocation_attribute_type,
        }
        attributes = allocation.allocationattribute_set.filter(**kwargs)
        self.assertEqual(attributes.count(), 1)
        attribute = attributes.first()
        self.assertEqual(str(expected_value), attribute.value)
        self.assertEqual(
            expected_usage, attribute.allocationattributeusage.value)

    def assert_allocation_user_service_units_values(self, allocation_user,
                                                    expected_value,
                                                    expected_usage):
        """Assert that the given AllocationUser has an
        AllocationUserAttribute with type 'Service Units' and the given
        expected value and the given expected usage."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        kwargs = {
            'allocation_attribute_type': allocation_attribute_type,
        }
        attributes = allocation_user.allocationuserattribute_set.filter(
            **kwargs)
        self.assertEqual(attributes.count(), 1)
        attribute = attributes.first()
        self.assertEqual(str(expected_value), attribute.value)
        self.assertEqual(
            expected_usage, attribute.allocationuserattributeusage.value)
