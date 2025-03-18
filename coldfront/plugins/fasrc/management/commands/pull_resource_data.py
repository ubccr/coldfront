import logging
from django.core.management.base import BaseCommand

from coldfront.core.resource.models import Resource, ResourceAttributeType
from coldfront.plugins.isilon.utils import IsilonConnection
from coldfront.plugins.lfs.utils import update_lfs_usages
from coldfront.plugins.sftocf.utils import (
    StarFishServer, StarFishRedash, STARFISH_SERVER
)


logger = logging.getLogger(__name__)

def update_resource_attr_types_from_dict(resource, res_attr_type_dict):
    for attr_name, attr_val in res_attr_type_dict.items():
        if attr_val:
            attr_type_obj = ResourceAttributeType.objects.get(name=attr_name)
            resource.resourceattribute_set.update_or_create(
                resource_attribute_type=attr_type_obj,
                defaults={'value': attr_val}
            )

class Command(BaseCommand):
    """Pull data from starfish and save to ResourceAttribute objects
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            dest='source',
            default='rest_api',
            help='Do not make any changes to Starfish, just print what changes would be slated',
        )

    def handle(self, *args, **options):
        source = options['source']
        if source == 'rest_api':
            sf = StarFishServer(STARFISH_SERVER)
            volumes = sf.get_volume_attributes()
            volumes = [
                {
                    'name': vol['vol'],
                    'attrs': {
                        'capacity_tb': vol['total_capacity']/(1024**4),
                        'free_tb': vol['free_space']/(1024**4),
                        'file_count': vol['number_of_files'],
                    }
                }
                for vol in volumes
            ]

        elif source == 'redash':
            sf = StarFishRedash(STARFISH_SERVER)
            volumes = sf.get_vol_stats()
            volumes = [
                {
                    'name': vol['volume_name'],
                    'attrs': {
                        'capacity_tb': vol['capacity_TB'],
                        'free_tb': vol['free_TB'],
                        'used_tb': vol['used_physical_TB'],
                        'file_count': vol['regular_files'],
                    }
                }
                for vol in volumes
            ]
        else:
            raise ValueError('source must be "rest_api" or "redash"')

        # collect user and lab counts, allocation sizes for each volume
        resources = Resource.objects.filter(resource_type__name='Storage')
        # update all tier 0 resources
        update_lfs_usages()
        for resource in resources:
            resource_name = resource.name.split('/')[0]
            if 'isilon' in resource.name:
                isilon_api = IsilonConnection(resource_name)
                isilon_capacity_tb = isilon_api.to_tb(isilon_api.total_space)
                isilon_free_tb = isilon_api.to_tb(isilon_api.unused_space)
                isilon_allocated_tb = isilon_api.to_tb(isilon_api.allocated_space)
                isilon_used_tb = isilon_api.to_tb(isilon_api.used_space)
                attr_pairs = {
                    'capacity_tb': isilon_capacity_tb,
                    'allocated_tb': isilon_allocated_tb,
                    'free_tb': isilon_free_tb,
                    'used_tb': isilon_used_tb,
                }
                update_resource_attr_types_from_dict(resource, attr_pairs)
            elif 'Tier 0' in resource.parent_resource.name:
                pass
            else:
                try:
                    volume = [v for v in volumes if v['name'] == resource_name][0]
                except:
                    logger.debug('resource not found in starfish: %s', resource)
                    continue
                update_resource_attr_types_from_dict(resource, volume['attrs'])
