from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
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
            'Public/Private', 'Text', 'Yes/No',
            'Attribute Expanded Text',
            'Float',
        ):
            AttributeType.objects.get_or_create(name=attribute_type)

        for resource_attribute_type, attribute_type in (
            #FASRC
            ('capacity_tb', 'Float'),
            ('free_tb', 'Float'),
            ('used_tb', 'Float'),
            ('file_count', 'Int'),
            ('allocated_tb', 'Float'),
            ('ChangeableAllocations', 'Yes/No'),
            ('CPU Count', 'Int'),
            ('GPU Count', 'Int'),
            ('Features', 'Text'),
            # UBCCR
            ('Core Count', 'Int'),
            # ('expiry_time', 'Int'),
            # ('fee_applies', 'Yes/No'),
            ('Node Count', 'Int'),
            ('Owner', 'Text'),
            ('quantity_default_value', 'Int'),
            ('quantity_label', 'Text'),
            ('xdmod_resource', 'Text'),
            # ('eula', 'Text'),
            # ('OnDemand','Yes/No'),
            # ('ServiceEnd', 'Date'),
            # ('ServiceStart', 'Date'),
            ('slurm_cluster', 'Text'),
            ('slurm_specs', 'Attribute Expanded Text'),
            # ('slurm_specs_attriblist', 'Text'),
            # ('Status', 'Public/Private'),
            # ('Vendor', 'Text'),
            # ('Model', 'Text'),
            # ('SerialNumber', 'Text'),
            # ('RackUnits', 'Int'),
            # ('InstallDate', 'Date'),
            # ('WarrantyExpirationDate', 'Date'),
        ):
            ResourceAttributeType.objects.update_or_create(
                name=resource_attribute_type,
                defaults={"attribute_type": AttributeType.objects.get(name=attribute_type)}
            )

        for resource_type, description in (
            ('Storage', 'Network Storage'),
            ('Storage Tier', 'Storage Tier',),
            ('Cloud', 'Cloud Computing'),
            ('Cluster', 'Cluster servers'),
            ('Cluster Partition', 'Cluster Partition'),
            ('Compute Node', 'Compute Node'),
            # ('Server', 'Extra servers providing various services'),
            # ('Software License', 'Software license purchased by users'),
            # ('Storage', 'NAS storage'),
        ):
            ResourceType.objects.get_or_create(
                name=resource_type,
                defaults={'description': description},
            )


        storage_tier = ResourceType.objects.get(name='Storage Tier')
        storage = ResourceType.objects.get(name='Storage')

        default_value_type = ResourceAttributeType.objects.get(name='quantity_default_value')
        label_type = ResourceAttributeType.objects.get(name='quantity_label')

        for name, desc, is_public, rtype, parent_name, default_value, reqspayment, is_allocatable in (
            ('Tier 0', 'Bulk - Lustre', True, storage_tier, None, 1, True, True),
            ('Tier 1', 'Enterprise - Isilon', True, storage_tier, None, 1, True, True),
            ('Tier 2', 'CEPH storage', True, storage_tier, None, 1, True, True),
            ('Tier 3', 'Attic Storage - Tape', True, storage_tier, None, 20, True, True),
            ('holylfs04/tier0', 'Holyoke data center lustre storage', True, storage, 'Tier 0', 1, True, True),
            ('holylfs05/tier0', 'Holyoke data center lustre storage', True, storage, 'Tier 0', 1, True, True),
            ('holylfs06/tier0', 'Holyoke data center lustre storage', True, storage, 'Tier 0', 1, True, True),
            ('nesetape/tier3', 'Cold storage for past projects', True, storage, 'Tier 3', 20, True, True),
            ('holy-isilon/tier1', 'Tier1 storage with snapshots and disaster recovery copy', True, storage, 'Tier 1', 1, True, True),
            ('bos-isilon/tier1', 'Tier1 storage for on-campus storage mounting', True, storage, 'Tier 1', 1, True, True),
            ('holystore01/tier0', 'Luster storage under Tier0', True, storage, 'Tier 0', 1, True, True),
            ('b-nfs02-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('b-nfs03-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('b-nfs04-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('b-nfs05-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('b-nfs06-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('b-nfs07-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('b-nfs08-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('b-nfs09-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs11-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs12-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs13-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs14-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs15-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs16-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs17-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs18-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('h-nfs19-p/tier2', 'Tier2 CEPH storage', True, storage, 'Tier 2', 1, True, True),
            ('boslfs02', 'complimentary lab storage', True, storage, 'Tier 0', 1, False, False),
            ('holylabs', 'complimentary lab storage', True, storage, 'Tier 0', 1, False, False),
        ):

            resource_defaults = {
                'description': desc,
                'is_public': is_public,
                'resource_type': rtype,
                'requires_payment': reqspayment,
                'is_allocatable': is_allocatable,
            }
            if parent_name:
                resource_defaults['parent_resource'] = Resource.objects.get(name=parent_name)

            resource_obj, _ = Resource.objects.update_or_create(
                name=name, defaults=resource_defaults)

            resource_obj.resourceattribute_set.update_or_create(
                resource_attribute_type=default_value_type,
                defaults={'value': default_value}
            )

            resource_obj.resourceattribute_set.update_or_create(
                resource_attribute_type=default_value_type,
                defaults={'value': default_value}
            )

            quantity_label = "TB"
            if default_value == 20:
                quantity_label += " in 20T increments"

            resource_obj.resourceattribute_set.update_or_create(
                resource_attribute_type=label_type,
                defaults={'value': quantity_label}
            )
