from django.core.management.base import BaseCommand

from coldfront.core.subscription.models import (AttributeType,
                                                SubscriptionAttributeType,
                                                SubscriptionStatusChoice,
                                                SubscriptionUserStatusChoice)


class Command(BaseCommand):
    help = 'Add default subscription related choices'

    def handle(self, *args, **options):

        for attribute_type in ('Date', 'Float', 'Int', 'Text', 'Yes/No'):
            AttributeType.objects.get_or_create(name=attribute_type)

        for choice in ('Active', 'Denied', 'Expired', 'New', 'Renewal Requested', 'Revoked', 'Unpaid',):
            SubscriptionStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Active', 'Error', 'Removed', ):
            SubscriptionUserStatusChoice.objects.get_or_create(name=choice)

        for name, attribute_type, has_usage, is_private in (
            ('Cloud Account Name', 'Text', False, False),
            ('CLOUD_USAGE_NOTIFICATION', 'Yes/No', False, True),
            ('Core Usage (Hours)', 'Int', True, False),
            ('Cloud Storage Quota (TB)', 'Float', True, False),
            ('EXPIRE NOTIFICATION', 'Yes/No', False, True),
            ('freeipa_group', 'Text', False, False),
            ('Is Course?', 'Yes/No', False, True),
            ('Paid', 'Float', False, False),
            ('Paid Cloud Support (Hours)', 'Float', True, True),
            ('Paid Network Support (Hours)', 'Float', True, True),
            ('Paid Storage Support (Hours)', 'Float', True, True),
            ('Purchase Order Number', 'Int', False, True),
            ('send_expiry_email_on_date', 'Date', False, True),
            ('slurm_account_name', 'Text', False, False),
            ('slurm_specs', 'Text', False, True),
            ('slurm_user_specs', 'Text', False, True),
            ('Storage Quota (GB)', 'Int', False, False),
            ('Storage_Group_Name', 'Text', False, False),
            ('SupportersQOS', 'Yes/No', False, False),
            ('SupportersQOSExpireDate', 'Date', False, False),
        ):
            SubscriptionAttributeType.objects.get_or_create(name=name, attribute_type=AttributeType.objects.get(
                name=attribute_type), has_usage=has_usage, is_private=is_private)
