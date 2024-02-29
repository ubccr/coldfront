from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (
    Resource,
    ResourceType,
    AttributeType,
    ResourceAttribute,
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
            ('used_tb', 'Float'),
            ('file_count', 'Int'),
            ('allocated_tb', 'Float'),
            # ('Core Count', 'Int'),
            # ('expiry_time', 'Int'),
            # ('fee_applies', 'Yes/No'),
            # ('Node Count', 'Int'),
            # ('Owner', 'Text'),
            ('quantity_default_value', 'Int'),
            ('quantity_label', 'Text'),
            ('xdmod_resource', 'Text'),
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

        default_value_type = ResourceAttributeType.objects.get(name='quantity_default_value')
        label_type = ResourceAttributeType.objects.get(name='quantity_label')

        for name, desc, is_public, rtype, parent_name, default_value in (
            ('Tier 0', 'Bulk - Lustre', True, storage_tier, None, 1),
            ('Tier 1', 'Enterprise - Isilon', True, storage_tier, None, 1),
            ('Tier 2', 'CEPH storage', True, storage_tier, None, 1),
            ('Tier 3', 'Attic Storage - Tape', True, storage_tier, None, 20),
            ('holylfs04/tier0', 'Holyoke data center lustre storage', True, storage, 'Tier 0', 1),
            ('holylfs05/tier0', 'Holyoke data center lustre storage', True, storage, 'Tier 0', 1),
            ('nesetape/tier3', 'Cold storage for past projects', True, storage, 'Tier 3', 20),
            ('holy-isilon/tier1', 'Tier1 storage with snapshots and disaster recovery copy', True, storage, 'Tier 1', 1),
            ('bos-isilon/tier1', 'Tier1 storage for on-campus storage mounting', True, storage, 'Tier 1', 1),
            ('holystore01/tier0', 'Luster storage under Tier0', True, storage, 'Tier 0', 1),
            ('b-nfs02-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('b-nfs03-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('b-nfs04-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('b-nfs05-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('b-nfs06-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('b-nfs07-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('b-nfs08-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('b-nfs09-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('h-nfs16-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('h-nfs17-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('h-nfs18-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
            ('h-nfs19-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1),
        ):

            resource_defaults = {
                'description':desc, 'is_public':is_public, 'resource_type':rtype,
            }
            if parent_name:
                resource_defaults['parent_resource'] = Resource.objects.get(name=parent_name)

            resource_obj, _ = Resource.objects.update_or_create(
                name=name, defaults=resource_defaults)

            resource_obj.resourceattribute_set.update_or_create(
                resource_attribute_type=default_value_type,
                defaults={'value': default_value}
            )

            quantity_label = "Quantity in TB"
            if default_value == 20:
                quantity_label += " in 20T increments"

            resource_obj.resourceattribute_set.update_or_create(
                resource_attribute_type=label_type,
                defaults={'value': quantity_label}
            )
