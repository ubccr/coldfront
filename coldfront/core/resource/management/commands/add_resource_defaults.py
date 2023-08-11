from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (
    Resource,
    ResourceType,
    AttributeType,
    ResourceAttributeType,
)


class Command(BaseCommand):
    help = 'Add default resource related choices'

    def handle(self, *args, **options):

        for attribute_type in (
            'Active/Inactive', 'Date', 'Int',
            'Public/Private', 'Text', 'Yes/No', 'Attribute Expanded Text',
            'Float',
        ):
            AttributeType.objects.get_or_create(name=attribute_type)

        for resource_attribute_type, attribute_type in (
            ('capacity_tb', 'Float'),
            ('free_tb', 'Float'),
            ('file_count', 'Int'),
            # ('Core Count', 'Int'),
            # ('expiry_time', 'Int'),
            # ('fee_applies', 'Yes/No'),
            # ('Node Count', 'Int'),
            # ('Owner', 'Text'),
            ('quantity_default_value', 'Int'),
            ('quantity_label', 'Text'),
            # ('eula', 'Text'),
            # ('OnDemand','Yes/No'),
            # ('ServiceEnd', 'Date'),
            # ('ServiceStart', 'Date'),
            # ('slurm_cluster', 'Text'),
            # ('slurm_specs', 'Attribute Expanded Text'),
            # ('slurm_specs_attriblist', 'Text'),
            # ('Status', 'Public/Private'),
            # ('Vendor', 'Text'),
            # ('Model', 'Text'),
            # ('SerialNumber', 'Text'),
            # ('RackUnits', 'Int'),
            # ('InstallDate', 'Date'),
            # ('WarrantyExpirationDate', 'Date'),
        ):
            ResourceAttributeType.objects.get_or_create(
                name=resource_attribute_type,
                attribute_type=AttributeType.objects.get(name=attribute_type)
            )

        for resource_type, description in (
            ('Storage', 'Network Storage'),
            ('Storage Tier', 'Storage Tier',),
            ('Cloud', 'Cloud Computing'),
            ('Cluster', 'Cluster servers'),
            # ('Cluster Partition', 'Cluster Partition '),
            # ('Compute Node', 'Compute Node'),
            # ('Server', 'Extra servers providing various services'),
            # ('Software License', 'Software license purchased by users'),
            # ('Storage', 'NAS storage'),
        ):
            ResourceType.objects.get_or_create(
                name=resource_type, description=description)


        storage_tier = ResourceType.objects.get(name='Storage Tier')
        storage = ResourceType.objects.get(name='Storage')
        for name, desc, is_public, rtype, parent in (
            (
                ('Tier 0', 'Bulk - Lustre', True, storage_tier, None),
                ('Tier 1', 'Enterprise - Isilon', True, storage_tier, None),
                ('Tier 3', 'Attic Storage - Tape', True, storage_tier, None),
            )
        ):
            Resource.objects.update_or_create(
                name=name,
                defaults={
                    'description':desc,
                    'is_public':is_public,
                    'resource_type':rtype,
                    'parent_resource': parent
                }
            )
