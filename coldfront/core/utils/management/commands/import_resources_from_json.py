import os
import json
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (AttributeType, Resource,
                                            ResourceAttribute,
                                            ResourceAttributeType,
                                            ResourceType)

from django.utils.dateparse import parse_datetime
from pprint import pprint
base_dir = settings.BASE_DIR


class Command(BaseCommand):

    def handle(self, *args, **options):
        print('Adding resources ...')
        with open('resource.json') as fp:
            data = json.load(fp)
            count = 0
            for ele in data:
                pprint(ele)
                if ele['model'] == 'resource.attributetype':
                    pk = ele['pk']
                    created = parse_datetime(ele['fields']['created'])
                    modified = parse_datetime(ele['fields']['modified'])
                    name = ele['fields']['name']

                    AttributeType.objects.create(
                        id=pk,
                        created=created,
                        modified=modified,
                        name=name)
                    count += 1
                elif ele['model'] == 'resource.resourcetype':
                    pk = ele['pk']
                    created = parse_datetime(ele['fields']['created'])
                    modified = parse_datetime(ele['fields']['modified'])
                    name = ele['fields']['name']
                    description = ele['fields']['description']

                    ResourceType.objects.create(
                        id=pk,
                        created=created,
                        modified=modified,
                        name=name,
                        description=description
                    )

                    count += 1
                elif ele['model'] == 'resource.resourceattributetype':
                    pk = ele['pk']
                    created = parse_datetime(ele['fields']['created'])
                    modified = parse_datetime(ele['fields']['modified'])
                    attribute_type = ele['fields']['attribute_type']
                    name = ele['fields']['name']
                    is_required = bool(ele['fields']['is_required'])
                    is_unique_per_resource = bool(
                        ele['fields']['is_unique_per_resource'])
                    is_value_unique = bool(ele['fields']['is_value_unique'])
                    ResourceAttributeType.objects.create(
                        id=pk,
                        created=created,
                        modified=modified,
                        attribute_type_id=attribute_type,
                        name=name,
                        is_required=is_required,
                        is_unique_per_resource=is_unique_per_resource,
                        is_value_unique=is_value_unique
                    )

                    count += 1
                elif ele['model'] == 'resource.resource':
                    pk = ele['pk']
                    created = parse_datetime(ele['fields']['created'])
                    modified = parse_datetime(ele['fields']['modified'])
                    parent_resource = (ele['fields']['parent_resource']) if bool(
                        ele['fields']['parent_resource']) else None
                    resource_type = ele['fields']['resource_type']
                    name = ele['fields']['name']
                    description = ele['fields']['description']
                    is_available = bool(ele['fields']['is_available'])
                    is_public = bool(ele['fields']['is_public'])
                    is_allocatable = bool(ele['fields']['is_allocatable'])
                    requires_payment = False
                    resource_obj = Resource.objects.create(
                        id=pk,
                        created=created,
                        modified=modified,
                        resource_type_id=resource_type,
                        name=name,
                        description=description,
                        is_available=is_available,
                        is_public=is_public,
                        is_allocatable=is_allocatable,
                        requires_payment=False
                    )
                    if parent_resource:
                        resource_obj.parent_resource = Resource.objects.get(
                            id=parent_resource)
                        resource_obj.save()

                    count += 1
                elif ele['model'] == 'resource.resourceattribute':
                    pk = ele['pk']
                    created = parse_datetime(ele['fields']['created'])
                    modified = parse_datetime(ele['fields']['modified'])
                    resource_attribute_type = ele['fields']['resource_attribute_type']
                    resource = ele['fields']['resource']
                    value = ele['fields']['value']

                    ResourceAttribute.objects.create(
                        id=pk,
                        created=created,
                        modified=modified,
                        resource_attribute_type_id=resource_attribute_type,
                        resource_id=resource,
                        value=value
                    )
                    count += 1

            print(len(data), count)

        with open('resource.json') as fp:
            data = json.load(fp)
            count = 0
            for ele in data:
                if ele['model'] == 'resource.resource':
                    pk = ele['pk']
                    resource_obj = Resource.objects.get(id=pk)
                    if ele['fields']['allowed_groups']:
                        for group in ele['fields']['allowed_groups']:
                            resource_obj.allowed_groups.add(group)
                        resource_obj.save()

                    if ele['fields']['allowed_users']:
                        for group in ele['fields']['allowed_users']:
                            resource_obj.allowed_users.add(group)
                        resource_obj.save()

                    if ele['fields']['linked_resources']:
                        for group in ele['fields']['linked_resources']:
                            resource_obj.linked_resources.add(group)
                        resource_obj.save()
