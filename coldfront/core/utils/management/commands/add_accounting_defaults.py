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
                # TODO: For legacy reasons, 'Savio' and 'Vector' are left
                # TODO: un-capitalized. Update them and references to them.
                ('Savio Compute', 'Savio cluster compute access'),
                ('Vector Compute', 'Vector cluster compute access'),
                ('ABC Compute', 'ABC cluster compute access'),
            ],
            'LRC_ONLY': [
                ('ALICE Compute', 'ALICE cluster compute access'),
                ('ALSACC Compute', 'ALSACC cluster compute access'),
                ('BALDUR Compute', 'BALDUR cluster compute access'),
                ('CATAMOUNT Compute', 'CATAMOUNT cluster compute access'),
                ('COSMIC Compute', 'COSMIC cluster compute access'),
                ('CUMULUS Compute', 'CUMULUS cluster compute access'),
                ('DIRAC Compute', 'DIRAC cluster compute access'),
                ('ETNA Compute', 'ETNA cluster compute access'),
                ('EXPLORER Compute', 'EXPLORER cluster compute access'),
                ('HBAR Compute', 'HBAR cluster compute access'),
                ('JBEI Compute', 'JBEI cluster compute access'),
                ('JCAP Compute', 'JCAP cluster compute access'),
                ('JGI Compute', 'JGI cluster compute access'),
                ('LAWRENCIUM Compute', 'LAWRENCIUM cluster compute access'),
                ('MHG Compute', 'MHG cluster compute access'),
                ('MUSIGNY Compute', 'MUSIGNY cluster compute access'),
                ('NANO Compute', 'NANO cluster compute access'),
                ('NATGAS Compute', 'NATGAS cluster compute access'),
                ('SCS Compute', 'SCS cluster compute access'),
                ('VOLTAIRE Compute', 'VOLTAIRE cluster compute access'),
                ('VULCAN Compute', 'VULCAN cluster compute access'),
                ('XMAS Compute', 'XMAS cluster compute access'),
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
