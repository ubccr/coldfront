from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (AttributeType,
                                            ResourceAttributeType,
                                            ResourceType)


class Command(BaseCommand):
    help = 'Add default resource related choices'

    def handle(self, *args, **options):

        for attribute_type in ('Active/Inactive', 'Date', 'Int', 'Public/Private', 'Text', 'Yes/No'):
            AttributeType.objects.get_or_create(name=attribute_type)

        for resource_attribute_type, attribute_type in (
            ('Access', 'Public/Private'),
            ('AllowedGroups', 'Text'),
            ('Core Count', 'Int'),
            ('expiry_time', 'Int'),
            ('fee_applies', 'Yes/No'),
            ('Node Count', 'Int'),
            ('Owner', 'Text'),
            ('quantity_default_value', 'Int'),
            ('quantity_label', 'Text'),
            ('ServiceEnd', 'Date'),
            ('ServiceStart', 'Date'),
            ('slurm_cluster', 'Text'),
            ('slurm_specs', 'Text'),
            ('Status', 'Public/Private'),
        ):
            ResourceAttributeType.objects.get_or_create(
                name=resource_attribute_type, attribute_type=AttributeType.objects.get(name=attribute_type))

        for resource_type, description in (
            ('Cloud', 'Cloud Computing'),
            ('Cluster', 'Cluster servers'),
            ('Cluster Partition', 'Cluster Partition '),
            ('Server', 'Extra servers providing various services'),
            ('Software License', 'Software license purchased by users'),
            ('Storage', 'NAS storage'),
        ):
            ResourceType.objects.get_or_create(
                name=resource_type, description=description)
