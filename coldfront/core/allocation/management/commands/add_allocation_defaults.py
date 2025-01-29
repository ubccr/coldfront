from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (AttributeType,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationChangeStatusChoice,
                                              AllocationUserAttributeType,
                                              AllocationUserStatusChoice)


class Command(BaseCommand):
    help = 'Add default allocation related choices'

    def handle(self, *args, **options):

        for attribute_type in (
            'Date', 'Float', 'Int', 'Text', 'Yes/No', 'No', 'Attribute Expanded Text',
            'Boolean'
        ):
            AttributeType.objects.get_or_create(name=attribute_type)

        for choice, description in (
            ('Active', 'Allocation is active and in use'),
            ('Denied', 'Allocation request was denied'),
            ('Expired', 'Allocation has expired'),
            ('Inactive', 'Allocation is defunct and no longer exists'),
            ('New', 'Allocation has been requested'),
            ('Pending Deactivation', 'Allocation is slated for deactivation'),
            ('In Progress', 'Allocation request is being processed'),
            ('On Hold', 'Allocation request is on hold'),
            ('Pending Activation', 'Allocation is in the process of being set up and not yet ready for use/billing'),
            # UBCCR Defaults
            # 'Paid', 'Payment Pending', 'Payment Requested',
            # 'Payment Declined', 'Revoked', 'Renewal Requested', 'Unpaid',
        ):
            choice_obj, created = AllocationStatusChoice.objects.get_or_create(name=choice)
            choice_obj.description = description
            choice_obj.save()

        for choice in ('Pending', 'Approved', 'Denied',):
            AllocationChangeStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Active', 'Error', 'Removed', ):
            AllocationUserStatusChoice.objects.get_or_create(name=choice)

        for name, attribute_type, is_private, is_changeable in (
            ('slurm_specs', 'Attribute Expanded Text', False, True),
        ):
            AllocationUserAttributeType.objects.update_or_create(
                name=name,
                defaults={
                    'attribute_type': AttributeType.objects.get(name=attribute_type),
                    'is_private': is_private,
                }
            )

        for name, attribute_type, has_usage, is_private in (
            # FASRC defaults
            ('Storage Quota (TB)', 'Float', True, False),
            ('Quota_In_Bytes', 'Int', True, False),
            ('UseStarFishZone', 'Yes/No', False, True),
            ('Offer Letter', 'Float', False, True),
            ('RequiresPayment', 'Boolean', False, True),
            ('Offer Letter Code', 'Text', False, True),
            ('Expense Code', 'Text', False, True),
            ('Subdirectory', 'Text', False, False),
            ('Heavy IO',  'Yes/No', False, False),
            ('Mounted',  'Yes/No', False, False),
            ('High Security', 'Yes/No', False, False),
            ('DUA', 'Yes/No', False, False),
            ('External Sharing', 'Yes/No', False, False),
            ('FairShare', 'Float', False, False),
            ('NormShares', 'Float', False, False),
            ('EffectvUsage', 'Float', False, False),
            ('RawUsage', 'Int', False, False),
            # UBCCR defaults
            ('Cloud Account Name', 'Text', False, False),
            # ('CLOUD_USAGE_NOTIFICATION', 'Yes/No', False, True),
            ('Core Usage (Hours)', 'Float', True, False),
            # ('Accelerator Usage (Hours)', 'Int', True, False),
            # ('Cloud Storage Quota (TB)', 'Float', True, False),
            # ('EXPIRE NOTIFICATION', 'Yes/No', False, True),
            # ('freeipa_group', 'Text', False, False),
            # ('Is Course?', 'Yes/No', False, True),
            ('Paid', 'Float', False, False),
            # ('Paid Cloud Support (Hours)', 'Float', True, True),
            # ('Paid Network Support (Hours)', 'Float', True, True),
            # ('Paid Storage Support (Hours)', 'Float', True, True),
            # ('Purchase Order Number', 'Int', False, True),
            # ('send_expiry_email_on_date', 'Date', False, True),
            ('slurm_account_name', 'Text', False, False),
            ('slurm_specs', 'Attribute Expanded Text', False, True),
            # ('slurm_specs_attriblist', 'Text', False, True),
            # ('slurm_user_specs', 'Attribute Expanded Text', False, True),
            # ('slurm_user_specs_attriblist', 'Text', False, True),
            # ('Storage Quota (GB)', 'Int', False, False),
            ('Storage_Group_Name', 'Text', False, False),
            # ('SupportersQOS', 'Yes/No', False, False),
            # ('SupportersQOSExpireDate', 'Date', False, False),
        ):
            AllocationAttributeType.objects.update_or_create(
                name=name,
                defaults={
                    'attribute_type': AttributeType.objects.get(name=attribute_type),
                    'has_usage': has_usage,
                    'is_private': is_private,
                }
            )
