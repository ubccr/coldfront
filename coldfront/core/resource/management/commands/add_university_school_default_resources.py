from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (ResourceType, Resource)
from coldfront.core.school.models import School
from coldfront.core.utils.common import import_from_settings
import os
import json
from pathlib import Path
GENERAL_RESOURCE_NAME = import_from_settings('GENERAL_RESOURCE_NAME')
app_commands_dir = os.path.dirname(__file__)

DEFAULT_SCHOOL_RESOURCES_JSON_PATH = os.path.join(
    os.path.dirname(__file__),
    '..', 'data', 'school_resources.json'
)

class Command(BaseCommand):
    help = 'Add University and School Default Resources'

    def add_arguments(self, parser):
        # add a --json-file-path flag, with a sane default
        parser.add_argument(
            '--json-file-path',
            type=str,
            default=DEFAULT_SCHOOL_RESOURCES_JSON_PATH,
            help='Filesystem path to school_resources.json'
        )

    def handle(self, *args, **options):
        json_file_path = options['json_file_path']
        self.add_general_university_resource()
        self.add_school_resources(json_file_path)

    def add_general_university_resource(self):
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

    def add_school_resources(self, json_file_path=DEFAULT_SCHOOL_RESOURCES_JSON_PATH):
        ## Load school_resources.json file ##
        json_path = Path(json_file_path)
        text = json_path.read_text(encoding="utf-8")
        resources = json.loads(text)

        ## Add resources
        for rec in resources:
            # resolve foreign keys
            rt = ResourceType.objects.get(name=rec["resource_type"])
            # School resource's parent is always Univeristy GENERAL_RESOURCE
            parent_resource_obj = Resource.objects.get(
                name=GENERAL_RESOURCE_NAME)
            school = School.objects.get(description=rec["school"])
            Resource.objects.get_or_create(
                resource_type=rt,
                parent_resource=parent_resource_obj,
                name=rec["name"],
                description=rec["description"],
                school=school,
                is_available=rec["is_available"],
                is_public=rec["is_public"],
                is_allocatable=rec["is_allocatable"],
            )