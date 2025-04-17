import logging
import re
from functools import reduce
from django.utils import timezone

from django.core.management.base import BaseCommand
from simple_history.utils import bulk_update_with_history, bulk_create_with_history

from coldfront.core.resource.models import ResourceType, ResourceAttribute, ResourceAttributeType, Resource
from coldfront.core.project.models import Project
from coldfront.plugins.slurm.utils import slurm_get_nodes_info

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Manage slurm resources from sinfo output'

    def get_output_from_file(self, file_path):
        try:
            keys = None
            with open(file_path, 'r') as output_file:
                for line in output_file:
                    if keys is None:
                        keys = re.sub(r'\s+', ' ', line).strip().lower().split(' ')
                    else:
                        values = re.sub(r'\s+', ' ', line).strip().split(' ')
                        yield dict(zip(keys, values))
        except FileNotFoundError:
            logger.error(f"File at {file_path} does not exist. Cant simulate output.")
        except IOError as e:
            logger.error(f"An error occurred: {e}")

    def add_arguments(self, parser):
        parser.add_argument("-e", "--environment", help="Environment, use dev to simulate output")

    def handle(self, *args, **options):
        def calculate_gpu_count(gres_value):
            if 'null' in gres_value:
                return 0
            gpu_list = gres_value.split('),')
            return reduce(lambda x, y: x + y,[int(gpu_info.split(':')[2].replace('(S','')) for gpu_info in gpu_list])

        def calculate_cpu_count(row):
            if row.get('s:c:t', None) is None:
                return 0
            cpu_count = row.get('s:c:t').split(':')[1]
            return int(cpu_count)

        def calculate_owner_value(project_list, row):
            owner_name = ''
            project_name_list = [project.title for project in project_list]
            owner_lists = row.get('groups', '').split(',')
            owner_project = [name_owner for name_owner in owner_lists if name_owner in project_name_list]
            if len(owner_project) > 0:
                return owner_project[0]
            if {'cluster_users', 'slurm-admin'}.issubset(set(owner_lists)):
                return'FASRC'
            return owner_name

        output = slurm_get_nodes_info()
        modify_history_date = timezone.now()
        project_list = Project.objects.all()
        current_cluster = Resource.objects.get(resource_type__name='Cluster')
        compute_node = ResourceType.objects.get(name='Compute Node')
        attribute_type_name_list = ['GPU Count', 'Core Count', 'Features', 'Owner', 'ServiceEnd']
        partition_resource_type = ResourceType.objects.get(name='Cluster Partition')
        gpu_count_attribute_type = ResourceAttributeType.objects.get(name='GPU Count')
        core_count_attribute_type = ResourceAttributeType.objects.get(name='Core Count')
        features_attribute_type = ResourceAttributeType.objects.get(name='Features')
        owner_attribute_type = ResourceAttributeType.objects.get(name='Owner')
        service_end_attribute_type = ResourceAttributeType.objects.get(name='ServiceEnd')
        existing_resource_attributes = list(
            ResourceAttribute.objects.filter(
                resource_attribute_type__name__in=attribute_type_name_list,
                resource__resource_type__name='Compute Node'
            ).values_list('pk', 'resource__name', 'resource_attribute_type__name')
        )
        existing_resource_attributes_check = [f'{resource_att[1]} {resource_att[2]}'  for resource_att in existing_resource_attributes]
        existing_resource_attributes_pk_map = {f'{resource_att[1]} {resource_att[2]}': resource_att[0] for resource_att in existing_resource_attributes}
        processed_resources = set()
        bulk_update_resource_attribute = []
        bulk_create_resource_attribute = []
        bulk_update_resource = []
        processed_resource_attribute = []
        for row in output:
            new_resource, compute_node_created = Resource.objects.get_or_create(
                name=row['nodelist'],
                defaults={
                    'is_allocatable':False,
                    'resource_type':compute_node,
                    'parent_resource':current_cluster
                }
            )
            Resource.objects.get_or_create(name=row['partition'], defaults={'resource_type':partition_resource_type})

            gpu_count = ResourceAttribute(resource_attribute_type=gpu_count_attribute_type, resource=new_resource, value=calculate_gpu_count(row['gres']))
            gpu_count_key = f"{row['nodelist']} {gpu_count_attribute_type.name}"
            if gpu_count_key in existing_resource_attributes_check:
                gpu_count.pk = existing_resource_attributes_pk_map[gpu_count_key]
                bulk_update_resource_attribute.append(gpu_count)
            else:
                if gpu_count_key not in processed_resource_attribute:
                    bulk_create_resource_attribute.append(gpu_count)
                    processed_resource_attribute.append(gpu_count_key)

            core_count = ResourceAttribute(resource_attribute_type=core_count_attribute_type, resource=new_resource, value=calculate_cpu_count(row))
            core_count_key = f"{row['nodelist']} {core_count_attribute_type.name}"
            if core_count_key in existing_resource_attributes_check:
                core_count.pk = existing_resource_attributes_pk_map[core_count_key]
                bulk_update_resource_attribute.append(core_count)
            else:
                if core_count_key not in processed_resource_attribute:
                    bulk_create_resource_attribute.append(core_count)
                    processed_resource_attribute.append(core_count_key)

            features = ResourceAttribute(resource_attribute_type=features_attribute_type, resource=new_resource, value=row.get('avail_features', '(null)'))
            features_key = f"{row['nodelist']} {features_attribute_type.name}"
            if features_key in existing_resource_attributes_check:
                features.pk = existing_resource_attributes_pk_map[features_key]
                bulk_update_resource_attribute.append(features)
            else:
                if features_key not in processed_resource_attribute:
                    bulk_create_resource_attribute.append(features)
                    processed_resource_attribute.append(features_key)

            owner = ResourceAttribute(
                resource_attribute_type=owner_attribute_type,
                resource=new_resource,
                value=calculate_owner_value(project_list, row)
            )
            owner_key = f"{row['nodelist']} {owner_attribute_type.name}"
            if owner_key in existing_resource_attributes_check:
                owner.pk = existing_resource_attributes_pk_map[owner_key]
                bulk_update_resource_attribute.append(owner)
            else:
                if owner_key not in processed_resource_attribute:
                    bulk_create_resource_attribute.append(owner)
                    processed_resource_attribute.append(owner_key)

            if new_resource.is_available is False:
                new_resource.is_available = True
                bulk_update_resource.append(new_resource)
                service_end_pk = existing_resource_attributes_pk_map[f"{row['nodelist']} {service_end_attribute_type.name}"]
                bulk_update_resource_attribute.append(
                    ResourceAttribute(
                        resource=new_resource, value=None,
                        resource_attribute_type=service_end_attribute_type,
                        pk=service_end_pk,
                        modified=modify_history_date
                    )
                )
            processed_resources.add(new_resource.name)
        try:
            logger.debug(f'Updating {len(bulk_update_resource_attribute)} ResourceAttribute records')
            bulk_update_with_history(
                bulk_update_resource_attribute, ResourceAttribute, ['value'],
                batch_size=500, default_change_reason='slurm_manage_resource command',
                default_date=modify_history_date
            )
            logger.debug(f'Updating {len(bulk_update_resource)} Resource records')
            bulk_update_with_history(
                bulk_update_resource, Resource, ['is_available'], batch_size=500,
                default_change_reason='slurm_manage_resource command', default_date=modify_history_date
            )
            logger.debug(f'Creating {len(bulk_create_resource_attribute)} ResourceAttribute records')
            bulk_create_with_history(bulk_create_resource_attribute, ResourceAttribute, batch_size=500, default_change_reason='slurm_manage_resource command')
        except Exception as e:
            logger.debug(f'Error processing resources info: {str(e)}')
            raise
        bulk_update_resource_attribute = []
        bulk_create_resource_attribute = []
        bulk_update_resource = []
        for resource_to_delete in Resource.objects.exclude(name__in=list(processed_resources)).filter(is_available=True, resource_type=compute_node):
            resource_to_delete.is_available = False
            bulk_update_resource.append(resource_to_delete)
            service_end = ResourceAttribute(resource=resource_to_delete, value=modify_history_date, resource_attribute_type=service_end_attribute_type)
            if f"{resource_to_delete.name} {service_end_attribute_type.name}" in existing_resource_attributes_check:
                service_end.pk = existing_resource_attributes_pk_map[f"{resource_to_delete.name} {service_end_attribute_type.name}"]
                bulk_update_resource_attribute.append(service_end)
            else:
                bulk_create_resource_attribute.append(service_end)
        try:
            logger.debug(f'Decommissioning {bulk_update_resource} Resource records')
            bulk_update_with_history(
                bulk_update_resource, Resource, ['is_available'], batch_size=500,
                default_change_reason='slurm_manage_resource command',  default_date=modify_history_date
            )
            logger.debug(f'Creating {len(bulk_create_resource_attribute)} ServiceEnd ResourceAttribute records')
            bulk_create_with_history(bulk_create_resource_attribute, ResourceAttribute, batch_size=500, default_change_reason='slurm_manage_resource command')
            logger.debug(f'Updating {len(bulk_update_resource_attribute)} ServiceEnd ResourceAttribute records')
            bulk_update_with_history(
                bulk_update_resource_attribute, ResourceAttribute, ['value'], batch_size=500,
                default_change_reason='slurm_manage_resource command', default_date=modify_history_date
            )
        except Exception as e:
            logger.error(f'Error cleaning up resources: {str(e)}')
            raise
