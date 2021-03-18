from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (AttributeType,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUserStatusChoice)


class Command(BaseCommand):
    help = 'Add default allocation related choices'

    def handle(self, *args, **options):

        for attribute_type in ('Date', 'Float', 'Int', 'Text', 'Yes/No'):
            AttributeType.objects.get_or_create(name=attribute_type)

        for choice in ('Active', 'Inactive', 'Denied', 'Expired',
                       'New', 'Paid', 'Payment Pending',
                       'Payment Requested', 'Payment Declined',
                       'Renewal Requested', 'Revoked', 'Unpaid',):
            AllocationStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Active', 'Inactive', 'Error', 'Removed'):
            AllocationUserStatusChoice.objects.get_or_create(name=choice)

        for name, attribute_type, has_usage, is_private in (
            ('Storage Quota (TB)', 'Float', True, False),
            ('Paid', 'Float', False, False),
            ('Storage Quota (GB)', 'Int', False, False),
            ('Storage_Group_Name', 'Text', False, False),
            ('Tier 0 - $50/TB/yr', 'Text', False, False),
            ('Tier 1 - $250/TB/yr', 'Text', False, False),
            ('Tier 2 - $100/TB/yr', 'Text', False, False),
            ('Tier 3 - $8/TB/yr', 'Text', False, False),
            ('Tier 0', 'Text', False, False),
            ('Tier 1', 'Text', False, False),
            ('Tier 2', 'Text', False, False),
            ('Tier 3', 'Text', False, False),

        ):
            AllocationAttributeType.objects.get_or_create(name=name, attribute_type=AttributeType.objects.get(
                name=attribute_type), has_usage=has_usage, is_private=is_private)
