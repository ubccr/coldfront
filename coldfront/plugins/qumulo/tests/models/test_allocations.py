from coldfront.core.allocation.models import Allocation

from django.test import TestCase


class TestAllocations(TestCase):

    def setUp(self) -> None:
        
        return super().setUp()

    def test_active_storage_allocations_queryset(self):
        active_storage_allocations = Allocation.objects.active_storage()
        filtered_allocations = Allocation.objects.filter(
            status__name="Active", resources__name="Storage2"
        )
        self.assertQuerysetEqual(active_storage_allocations, filtered_allocations)

        should_contain_rw_allocations = active_storage_allocations.filter(
            resources__name="rw"
        )
        self.assertFalse(should_contain_rw_allocations.exists())

        should_contain_ro_allocations = active_storage_allocations.filter(
            resources__name="ro"
        )
        self.assertFalse(should_contain_ro_allocations.exists())

    def test_consumption_allocations_queryset(self):
        consumption_allocations = Allocation.objects.consumption()
        filtered_allocations = Allocation.objects.filter(
            allocationattribute__allocation_attribute_type__name="service_rate",
            allocationattribute__value="consumption",
        )
        self.assertQuerysetEqual(consumption_allocations, filtered_allocations)

    def test_parents_allocations_queryset(self):
        parents_allocations = Allocation.objects.parents()
        filtered_allocations = Allocation.objects.filter(parent_links=None)
        self.assertQuerysetEqual(parents_allocations, filtered_allocations)
