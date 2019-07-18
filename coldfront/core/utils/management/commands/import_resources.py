import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (AttributeType, Resource,
                                              ResourceAttribute,
                                              ResourceAttributeType,
                                              ResourceType)

base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding resources ...')

        AttributeType.objects.all().delete()
        ResourceType.objects.all().delete()
        ResourceAttributeType.objects.all().delete()
        ResourceType.objects.all().delete()
        Resource.objects.all().delete()
        ResourceAttribute.objects.all().delete()

        with open(os.path.join(base_dir, 'local_data/R1_attribute_types.tsv')) as file:
            for name in file:
                attribute_type_obj, created = AttributeType.objects.get_or_create(
                    name=name.strip())
                # print(attribute_type_obj, created)

        with open(os.path.join(base_dir, 'local_data/R2_resource_types.tsv')) as file:
            for line in file:
                name, description = line.strip().split('\t')
                resource_type_obj, created = ResourceType.objects.get_or_create(
                    name=name.strip(), description=description.strip())
                # print(resource_type_obj, created)

        with open(os.path.join(base_dir, 'local_data/R3_resource_attributes_types.tsv')) as file:
            for line in file:
                attribute_type_name, resource_type_name, name, required = line.strip().split('\t')

                resource_attribute_type_obj, created = ResourceAttributeType.objects.get_or_create(
                    attribute_type=AttributeType.objects.get(
                        name=attribute_type_name),
                    name=name,
                    is_required=bool(required))
                # print(resource_attribute_type_obj, created)

        with open(os.path.join(base_dir, 'local_data/R4_resources.tsv')) as file:
            for line in file:
                # print(line)
                resource_type_name, name, description, parent_name = line.strip().split('\t')
                resource_obj, created = Resource.objects.get_or_create(
                    resource_type=ResourceType.objects.get(name=resource_type_name),
                    name=name,
                    description=description.strip())

                if parent_name != 'None':
                    parent_resource_obj = Resource.objects.get(name=parent_name)
                    resource_obj.parent_resource = parent_resource_obj
                    resource_obj.save()

                # print(resource_obj, created)
        with open(os.path.join(base_dir, 'local_data/R5_resource_attributes.tsv')) as file:
            for line in file:
                if not line.strip():
                    continue
                resource_type_name, resource_attribute_type_name, resource_attribute_type_type_name, resource_name, value = line.strip().split('\t')

                if resource_attribute_type_name == 'slurm_specs':
                    value = 'QOS+=' + value + ':Fairshare=100'

                if resource_attribute_type_name == 'Access':
                    if value == 'Public':
                        is_public = True
                    else:
                        is_public = False
                    resource_obj = Resource.objects.get(name=resource_name)
                    resource_obj.is_public = is_public
                    resource_obj.save()

                elif resource_attribute_type_name == 'Status':
                    if value == 'Active':
                        is_available = True
                    else:
                        is_available = False
                    resource_obj = Resource.objects.get(name=resource_name)
                    resource_obj.is_available = is_available
                    resource_obj.save()

                elif resource_attribute_type_name == 'AllowedGroups':
                    resource_obj = Resource.objects.get(name=resource_name)
                    for group in value.split(','):
                        group_obj, _ = Group.objects.get_or_create(name=group.strip())

                        resource_obj.allowed_groups.add(group_obj)
                    resource_obj.save()

                else:

                    # print('resource_name', resource_name)
                    resource_attribute_obj, created = ResourceAttribute.objects.get_or_create(
                        resource_attribute_type=ResourceAttributeType.objects.get(name=resource_attribute_type_name, attribute_type__name=resource_attribute_type_type_name),
                        resource=Resource.objects.get(name=resource_name),
                        value=value.strip())


        resource_obj = Resource.objects.get(name='UB-HPC')
        for children_resource in ['Industry-scavenger', 'Chemistry-scavenger', 'Physics-scavenger', 'MAE-scavenger']:
            children_resource_obj = Resource.objects.get(name=children_resource)
            resource_obj.linked_resources.add(children_resource_obj)


        for unsubscribable in ['Industry-scavenger', 'Chemistry-scavenger', 'Physics-scavenger', 'MAE-scavenger', 'Physics', 'Chemistry', 'MAE']:
            resource_obj = Resource.objects.get(name=unsubscribable)
            resource_obj.is_allocatable = False
            resource_obj.save()



        print('Finished adding resources.')
