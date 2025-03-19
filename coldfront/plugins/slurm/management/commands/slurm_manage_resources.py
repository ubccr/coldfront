import logging
import os
import re
from functools import reduce
from cProfile import Profile

from django.core.management.base import BaseCommand, CommandError

from coldfront.core.resource.models import ResourceType, ResourceAttribute, ResourceAttributeType, AttributeType, Resource
from coldfront.core.project.models import Project
from coldfront.plugins.slurm.utils import slurm_get_nodes_info
from django.utils.datetime_safe import datetime

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
            print(f"File at {file_path} does not exist. Cant simulate output.")
        except IOError as e:
            print(f"An error occurred: {e}")


    def add_arguments(self, parser):
        parser.add_argument("-e", "--environment", help="Environment, use dev to simulate output")
        parser.add_argument('--profile', action='store_true', default=False)

    def handle(self, *args, **options):
        if options.get('profile', False):
            profiler = Profile()
            profiler.runcall(self._handle, *args, **options)
            profiler.print_stats()
        else:
            self._handle(*args, **options)

    def _handle(self, *args, **options):
        def calculate_gpu_count(gres_value):
            if 'null' in gres_value:
                return 0
            gpu_list = gres_value.split(',')
            return reduce(lambda x, y: x + y,[int(gpu_info.split(':')[2].replace('(S','')) for gpu_info in gpu_list])

        def calculate_cpu_count(row):
            if row.get('S:C:T', None) is None:
                return 0
            cpu_count = row.get('S:C:T').split(':')[1]
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

        env = options['environment']  or 'production'
        if 'dev' in env:
            output = self.get_output_from_file(os.path.join(os.getcwd(), 'coldfront/plugins/slurm/management/commands/sinfo.txt'))
        else:
            output = slurm_get_nodes_info()
        print(f'Running on {env} mode')
        project_list = Project.objects.all()
        compute_node, compute_node_created = ResourceType.objects.get_or_create(name='Compute Node', description='Compute Node')
        partition_resource_type, partition_created = ResourceType.objects.get_or_create(name='Cluster Partition', description='Cluster Partition')
        int_attribute_type = AttributeType.objects.get(name='Int')
        text_attribute_type = AttributeType.objects.get(name='Text')
        gpu_count_attribute_type, gpu_count_created = ResourceAttributeType.objects.get_or_create(name='GPU Count', defaults={'attribute_type': int_attribute_type})
        core_count_attribute_type, core_count_created = ResourceAttributeType.objects.get_or_create(name='Core Count', defaults={'attribute_type': int_attribute_type})
        features_attribute_type, features_created = ResourceAttributeType.objects.get_or_create(name='Features', defaults={'attribute_type': text_attribute_type})
        owner_attribute_type, owner_created = ResourceAttributeType.objects.get_or_create(name='Owner', defaults={'attribute_type': text_attribute_type})
        service_end_attribute_type, service_end_created = ResourceAttributeType.objects.get_or_create(name='ServiceEnd', defaults={'attribute_type': text_attribute_type})
        processed_resources = set()
        bulk_process_resource_attribute = []
        bulk_update_resource = []
        for row in output:
            new_resource, compute_node_created_created = Resource.objects.get_or_create(name=row['nodelist'], defaults={'is_allocatable':False, 'resource_type':compute_node})
            Resource.objects.get_or_create(name=row['partition'], defaults={'resource_type':partition_resource_type})
            bulk_process_resource_attribute.append(ResourceAttribute(resource_attribute_type=gpu_count_attribute_type, resource=new_resource, value=calculate_gpu_count(row['gres'])))
            bulk_process_resource_attribute.append(ResourceAttribute(resource_attribute_type=core_count_attribute_type, resource=new_resource, value=calculate_cpu_count(row)))
            bulk_process_resource_attribute.append(ResourceAttribute(resource_attribute_type=features_attribute_type, resource=new_resource, value=row.get('avail_features', '(null)')))
            bulk_process_resource_attribute.append(ResourceAttribute(resource_attribute_type=owner_attribute_type, resource=new_resource, value=calculate_owner_value(project_list, row)))
            if new_resource.is_available is False:
                bulk_update_resource.append(Resource(name=row['nodelist'], is_available=True))
                bulk_process_resource_attribute.append(ResourceAttribute(resource=new_resource, value=' ', resource_attribute_type=service_end_attribute_type))
            processed_resources.add(new_resource.name)
        ResourceAttribute.objects.bulk_create(bulk_process_resource_attribute, update_conflicts=True, unique_fields=[], update_fields=['value'])
        Resource.objects.bulk_create(bulk_update_resource, update_conflicts=True, unique_fields=[],  update_fields=['is_available'])
        bulk_process_resource_attribute = []
        bulk_update_resource = []
        for resource_to_delete in Resource.objects.exclude(name__in=list(processed_resources)).filter(is_available=True, resource_type=compute_node):
            bulk_update_resource.append(Resource(name=resource_to_delete.name, is_available=False))
            bulk_process_resource_attribute.append(ResourceAttribute(resource=resource_to_delete, value=str(datetime.now()), resource_attribute_type=service_end_attribute_type))
        ResourceAttribute.objects.bulk_create(bulk_process_resource_attribute, update_conflicts=True, unique_fields=[], update_fields=['value'])
        Resource.objects.bulk_create(bulk_update_resource, update_conflicts=True, unique_fields=[], update_fields=['is_available'])