from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (ResourceType, Resource)
from coldfront.core.school.models import School
from coldfront.core.utils.common import import_from_settings


GENERAL_RESOURCE_NAME = import_from_settings('GENERAL_RESOURCE_NAME')


class Command(BaseCommand):
    help = 'Add University and School Default Resources'

    def handle(self, *args, **options):
        self.add_genearl_university_resource()
        self.add_school_resources()


    def add_genearl_university_resource(self):
        # Generic University Cluster
        resource_type, parent_resource, name, description, school, is_available, is_public, is_allocatable = \
            ('Cluster', None, GENERAL_RESOURCE_NAME,
             'University Academic Cluster', None, True, True, True)
        resource_type_obj = ResourceType.objects.get(name=resource_type)
        if parent_resource is not None:
            parent_resource_obj = Resource.objects.get(
                name=parent_resource)
        else:
            parent_resource_obj = None

        Resource.objects.get_or_create(
            resource_type=resource_type_obj,
            parent_resource=parent_resource_obj,
            name=name,
            description=description,
            school=school,
            is_available=is_available,
            is_public=is_public,
            is_allocatable=is_allocatable
        )

    def add_school_resources(self):
        resources = [
            # Tandon
            ('Generic', None, 'Tandon', 'Tandon-wide-resources',
             School.objects.get(description='Tandon School of Engineering'),
             True, False, True),
            ('Generic', None, 'Tandon-GPU-Adv', 'Advanced GPU resource',
             School.objects.get(description='Tandon School of Engineering'),
             True, False, True),

            # CDS
            ('Generic', None, 'CDS', 'CDS-wide-resources', School.objects.get(description='Center for Data Science'),
             True, False, True),
            ('Generic', None, 'CDS-GPU-Prio', 'Priority GPU resource',
             School.objects.get(description='Center for Data Science'), True, False, True),  # sfoster
        ]
        for resource in resources:
            resource_type, parent_resource, name, description, school, is_available, is_public, is_allocatable = resource
            resource_type_obj = ResourceType.objects.get(name=resource_type)
            if parent_resource is not None:
                parent_resource_obj = Resource.objects.get(
                    name=parent_resource)
            else:
                parent_resource_obj = None

            Resource.objects.get_or_create(
                resource_type=resource_type_obj,
                parent_resource=parent_resource_obj,
                name=name,
                description=description,
                school=school,
                is_available=is_available,
                is_public=is_public,
                is_allocatable=is_allocatable
            )
