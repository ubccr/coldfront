from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AttributeType
from coldfront.core.resource.models import Resource
from coldfront.core.resource.models import ResourceType
from django.core.management.base import BaseCommand
from flags.state import flag_enabled
import logging

"""An admin command that creates database objects needed for
accounting."""


class Command(BaseCommand):

    help = 'Creates database objects needed for accounting.'
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        resource_type, _ = ResourceType.objects.get_or_create(
            name='Cluster', description='Cluster servers')

        # Create 'Cluster'-type resources based on flags (i.e., BRC has one set
        # of clusters, while LRC has another).
        resource_fields_by_flag_name = {
            'BRC_ONLY': [
                ('Savio Compute', 'Savio cluster compute access'),
                ('Vector Compute', 'Vector cluster compute access'),
                ('ABC Compute', 'ABC cluster compute access'),
            ],
            'LRC_ONLY': [
                ('Lawrencium Compute', 'Lawrencium cluster compute access'),
            ],
        }
        resources = []
        for flag_name, resource_fields in resource_fields_by_flag_name.items():
            if flag_enabled(flag_name):
                resources.extend(resource_fields)
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
        allocation_attribute_type.is_private = False
        allocation_attribute_type.save()

        # Each Allocation has at most one '{cluster_name} Allocation Type'
        # attribute of type Text.
        attribute_type, _ = AttributeType.objects.get_or_create(name='Text')
        cluster_names_by_flag_name = {
            'BRC_ONLY': 'Savio',
            'LRC_ONLY': 'Lawrencium',
        }
        for flag_name, cluster_name in cluster_names_by_flag_name.items():
            if flag_enabled(flag_name):
                allocation_attribute_type, _ = \
                    AllocationAttributeType.objects.get_or_create(
                        attribute_type=attribute_type,
                        name=f'{cluster_name} Allocation Type')
                allocation_attribute_type.is_required = False
                allocation_attribute_type.is_unique = True
                allocation_attribute_type.save()
