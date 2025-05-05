from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (ResourceType, Resource)
from coldfront.core.school.models import School
from coldfront.core.utils.common import import_from_settings
import os
import json
from pathlib import Path
GENERAL_RESOURCE_NAME = import_from_settings('GENERAL_RESOURCE_NAME')
app_commands_dir = os.path.dirname(__file__)


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
        ## Load school_resources.json file ##
        parent_dir = os.path.dirname(app_commands_dir)
        json_file_path = os.path.join(parent_dir, 'data', 'school_resources.json')
        json_path = Path(json_file_path)
        text = json_path.read_text(encoding="utf-8")
        resources = json.loads(text)

        ## Add resources
        for rec in resources:
            # resolve foreign keys
            rt = ResourceType.objects.get(name=rec["resource_type"])
            parent = None
            if rec["parent_resource"]:
                parent = Resource.objects.get(name=rec["parent_resource"])
            school = School.objects.get(description=rec["school"])

            Resource.objects.get_or_create(
                resource_type=rt,
                parent_resource=parent,
                name=rec["name"],
                description=rec["description"],
                school=school,
                is_available=rec["is_available"],
                is_public=rec["is_public"],
                is_allocatable=rec["is_allocatable"],
            )