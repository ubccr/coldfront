from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AttributeType
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceType
from django.core.management.base import BaseCommand
import logging

"""An admin command that creates database objects needed for
accounting."""


class Command(BaseCommand):

    help = 'Creates database objects needed for accounting.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        resource_type, _ = ResourceType.objects.get_or_create(
            name='Cluster', description='Cluster servers')
        resources = [
            ('Savio Compute', 'Savio cluster compute access'),
            ('Vector Compute', 'Vector cluster compute access'),
        ]
        for name, description in resources:
            # Allocations to a cluster must have the corresponding Resource.
            try:
                resource = Resource.objects.get(name=name)
            except Resource.DoesNotExist:
                resource = Resource.objects.create(
                    name=name, resource_type=resource_type)
            resource.description = description
            # Each Project can only have one Allocation to this Resource.
            resource.is_unique_per_project = True
            resource.save()

        # Each Allocation has at most one 'Service Units' attribute of
        # type Decimal.
        attribute_type, _ = AttributeType.objects.get_or_create(name='Decimal')
        allocation_attribute_type, _ = \
            AllocationAttributeType.objects.get_or_create(
                name='Service Units', attribute_type=attribute_type)
        allocation_attribute_type.has_usage = True
        allocation_attribute_type.is_unique = True
        allocation_attribute_type.save()

        # Each Allocation has at most one 'Savio Allocation Type' attribute of
        # type Text.
        attribute_type, _ = AttributeType.objects.get_or_create(name='Text')
        allocation_attribute_type, _ = \
            AllocationAttributeType.objects.get_or_create(
                name='Savio Allocation Type', attribute_type=attribute_type)
        # TODO: Set is_required to True.
        allocation_attribute_type.is_required = False
        allocation_attribute_type.is_unique = True
        allocation_attribute_type.save()

        # Create attributes with type 'Savio Allocation Type'.
        allocation_attribute, _ = AllocationAttribute.objects.get_or_create(
            allocation_attribute_type=allocation_attribute_type)
