from django.core.management.base import BaseCommand

from coldfront.core.resource.models import (
    ResourceType,
    AttributeType,
    ResourceAttributeType,
)
from coldfront.config.defaults import RESOURCE_DEFAULTS as defaults


class Command(BaseCommand):
    help = 'Add default resource related choices'

    def handle(self, *args, **options):

        for attribute_type in defaults['attrtypes']:
            AttributeType.objects.get_or_create(name=attribute_type)

        for resource_attribute_type, attribute_type in defaults['resourceattrtypes']:
            ResourceAttributeType.objects.get_or_create(
                name=resource_attribute_type, attribute_type=AttributeType.objects.get(name=attribute_type))

        for resource_type, description in defaults['resourcetypes']:
            ResourceType.objects.get_or_create(
                name=resource_type, description=description)
