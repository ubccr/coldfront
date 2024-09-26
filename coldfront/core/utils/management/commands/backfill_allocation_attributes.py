from coldfront.core.allocation.models import AllocationAttribute, AllocationAttributeType, Allocation
from coldfront.core.resource.models import Resource

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-at',
            '--allocation_attribute_type',
            help='Allocation attribute type the new allocation attribute should have',
            required=True
        )
        parser.add_argument(
            '-ia',
            '--internal_allocation_attribute',
            help='Allocation attribute within the allocation class whose value we need',
            required=True
        )
        parser.add_argument(
            '-r',
            '--resource',
            help='Allocations containing this resource that should be backfilled',
            required=True
        )

    def handle(self, *args, **options):
        allocation_attribute_type = options.get('allocation_attribute_type')
        internal_allocation_attribute = options.get('internal_allocation_attribute')
        resource = options.get('resource')

        resource_obj = Resource.objects.filter(name=resource)
        if not resource_obj.exists():
            print('This resource does not exist')
            return
        resource_obj = resource_obj[0]

        allocation_attribute_type_obj = AllocationAttributeType.objects.filter(name=allocation_attribute_type)
        if not allocation_attribute_type_obj.exists():
            print('This allocation attribute type does not exist')
            return
        allocation_attribute_type_obj = allocation_attribute_type_obj[0]

        if resource_obj not in allocation_attribute_type_obj.get_linked_resources():
            print('This resource is not linked to this allocation attribute type')
            return
        
        if not hasattr(Allocation, internal_allocation_attribute):
            print('This internal allocation attribute does not exist')
            return

        count = 0
        allocation_objs = Allocation.objects.filter(resources = resource_obj)
        for allocation_obj in allocation_objs:
            value = getattr(allocation_obj, internal_allocation_attribute)
            allocation_attribute_exists = AllocationAttribute.objects.filter(
                allocation_attribute_type=allocation_attribute_type_obj, allocation=allocation_obj
            ).exists()
            if allocation_attribute_exists or not value:
                continue

            AllocationAttribute.objects.create(
                allocation=allocation_obj,
                allocation_attribute_type=allocation_attribute_type_obj,
                value=value
            )

            count += 1

        print(f'Created {count} allocation attributes')
