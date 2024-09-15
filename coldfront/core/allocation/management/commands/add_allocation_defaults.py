from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (
    AttributeType,
    AllocationAttributeType,
    AllocationStatusChoice,
    AllocationChangeStatusChoice,
    AllocationUserStatusChoice
)
from coldfront.config.defaults import ALLOCATION_DEFAULTS as defaults

class Command(BaseCommand):
    help = 'Add default allocation related choices'

    def handle(self, *args, **options):

        for attribute_type in defaults['attrtypes']:
            AttributeType.objects.get_or_create(name=attribute_type)

        for choice in defaults['statuschoices']:
            AllocationStatusChoice.objects.get_or_create(name=choice)

        for choice in defaults['changestatuschoices']:
            AllocationChangeStatusChoice.objects.get_or_create(name=choice)

        for choice in defaults['allocationuserstatuschoices']:
            AllocationUserStatusChoice.objects.get_or_create(name=choice)

        for name, attribute_type, has_usage, is_private in defaults['allocationattrtypes']:
            AllocationAttributeType.objects.get_or_create(
                name=name,
                attribute_type=AttributeType.objects.get(name=attribute_type),
                has_usage=has_usage,
                is_private=is_private,
            )
