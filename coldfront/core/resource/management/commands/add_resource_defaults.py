from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (AttributeType,
                                            ResourceAttributeType,
                                            ResourceType, Resource)
from coldfront.core.school.models import School
from coldfront.core.utils.common import import_from_settings


GENERAL_RESOURCE_NAME = import_from_settings('GENERAL_RESOURCE_NAME')


class Command(BaseCommand):
    help = 'Add default resource related choices'

    def handle(self, *args, **options):

        for attribute_type in ('Active/Inactive', 'Date', 'Int', 
            'Public/Private', 'Text', 'Yes/No', 'Attribute Expanded Text'):
            AttributeType.objects.get_or_create(name=attribute_type)

        for resource_attribute_type, attribute_type in (
            ('Core Count', 'Int'),
            ('expiry_time', 'Int'),
            ('fee_applies', 'Yes/No'),
            ('Node Count', 'Int'),
            ('Owner', 'Text'),
            ('quantity_default_value', 'Int'),
            ('quantity_label', 'Text'),
            ('eula', 'Text'),
            ('OnDemand','Yes/No'),
            ('ServiceEnd', 'Date'),
            ('ServiceStart', 'Date'),
            ('slurm_cluster', 'Text'),
            ('slurm_specs', 'Attribute Expanded Text'),
            ('slurm_specs_attriblist', 'Text'),
            ('Status', 'Public/Private'),
            ('Vendor', 'Text'),
            ('Model', 'Text'),
            ('SerialNumber', 'Text'),
            ('RackUnits', 'Int'),
            ('InstallDate', 'Date'),
            ('WarrantyExpirationDate', 'Date'),
        ):
            ResourceAttributeType.objects.get_or_create(
                name=resource_attribute_type, attribute_type=AttributeType.objects.get(name=attribute_type))

        for resource_type, description in (
            ('Cloud', 'Cloud Computing'),
            ('Cluster', 'Cluster servers'),
            ('Cluster Partition', 'Cluster Partition '),
            ('Compute Node', 'Compute Node'),
            ('Server', 'Extra servers providing various services'),
            ('Software License', 'Software license purchased by users'),
            ('Storage', 'NAS storage'),
            ('Generic', 'Generic School'),
        ):
            ResourceType.objects.get_or_create(
                name=resource_type, description=description)

        self.add_university_and_generic_resources()

    def add_university_and_generic_resources(self):
        resources = [
            # Generic University Cluster
            ('Cluster', None, GENERAL_RESOURCE_NAME,
             'University Academic Cluster', None, True, True, True),

            # Generic
            ('Generic', None, 'Tandon', 'Tandon-wide-resources',
             School.objects.get(description='Tandon School of Engineering'),
             True, False, True),
            ('Generic', None, 'Tandon-GPU-Adv', 'Advanced GPU resource',
             School.objects.get(description='Tandon School of Engineering'),
             True, False, True),
            ('Generic', None, 'CDS', 'CDS-wide-resources', School.objects.get(description='Center for Data Science'),
             True, False, True),
            ('Generic', None, 'CDS-GPU-Prio', 'Priority GPU resource',
             School.objects.get(description='Center for Data Science'), True, False, True),  # sfoster
        ]
        for resource in resources:
            resource_type, parent_resource, name, description, school, is_available, is_public, is_allocatable = resource
            resource_type_obj = ResourceType.objects.get(name=resource_type)
            if parent_resource != None:
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
