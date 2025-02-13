from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (AttributeType,
                                              AllocationAttributeType,
                                              AllocationStatusChoice,
                                              AllocationUserStatusChoice,
                                              AllocationUserRequestStatusChoice,
                                              AllocationChangeStatusChoice,
                                              AllocationUserRoleChoice)


class Command(BaseCommand):
    help = 'Add default allocation related choices'

    def handle(self, *args, **options):

        for attribute_type in ('Date', 'Float', 'Int', 'Text', 'Yes/No',
            'Attribute Expanded Text', 'True/False'):
            AttributeType.objects.get_or_create(name=attribute_type)

        for choice in ('Active', 'Denied', 'Expired',
                       'New', 'Paid', 'Payment Pending',
                       'Payment Requested', 'Payment Declined',
                       'Renewal Requested', 'Revoked', 'Unpaid',
                       'Billing Information Submitted',):
            AllocationStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Pending', 'Approved', 'Denied',):
            AllocationChangeStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Active', 'Error', 'Removed', 'Pending - Add', 'Pending - Remove',
                       'Eligible', 'Disabled', 'Retired'):
            AllocationUserStatusChoice.objects.get_or_create(name=choice)

        for choice in ('Approved', 'Pending', 'Denied', ):
            AllocationUserRequestStatusChoice.objects.get_or_create(name=choice)

        for choice, is_user_default, is_manager_default in (
            ('read/write', True, True),
            ('read only', False, False)
        ):
            AllocationUserRoleChoice.objects.get_or_create(
                name=choice, is_user_default=is_user_default, is_manager_default=is_manager_default)

        for name, attribute_type, has_usage, is_private in (
            ('Cloud Account Name', 'Text', False, False),
            ('CLOUD_USAGE_NOTIFICATION', 'Yes/No', False, True),
            ('Core Usage (Hours)', 'Int', True, False),
            ('Accelerator Usage (Hours)', 'Int', True, False),            
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
            ('slurm_specs', 'Attribute Expanded Text', False, True),
            ('slurm_specs_attriblist', 'Text', False, True),
            ('slurm_user_specs', 'Attribute Expanded Text', False, True),
            ('slurm_user_specs_attriblist', 'Text', False, True),
            ('Storage Quota (GB)', 'Int', False, False),
            ('Storage Quota (TB)', 'Int', False, False),
            ('Storage_Group_Name', 'Text', False, False),
            ('SupportersQOS', 'Yes/No', False, False),
            ('SupportersQOSExpireDate', 'Date', False, False),
            ('Account Number', 'Text', False, False),
            ('Sub-Account Number', 'Text', False, False),
            ('Applications', 'Text', False, True),
            ('Has DL Workflow', 'Yes/No', False, True),
            ('Has GPU Workflow', 'Yes/No', False, True),
            ('Billing: Account Number', 'Text', False, True),
            ('Billing: Fiscal Office', 'Text', False, True),
            ('Billing: Sub-Account Number', 'Text', False, True),
            ('Contact: IT Pro Contact', 'Text', False, True),
            ('Contact: Phone Number', 'Text', False, True),
            ('Contact: Primary Contact', 'Text', False, True),
            ('Contact: Requestor', 'Text', False, True),
            ('Contact: Secondary Contact', 'Text', False, True),
            ('Department: Department Full Name', 'Text', False, True),
            ('Department: Department Primary Campus', 'Text', False, True),
            ('Department: Department Short Name', 'Text', False, True),
            ('Department: Group Name', 'Text', False, True),
            ('Policies: Accepted Best Practices', 'True/False', False, True),
            ('Policies: Accepted Terms of Service', 'True/False', False, True),
            ('Policies:Accepted Data Management Responsibilities', 'True/False', False, True),
            ('Storage: Admin Group', 'Text', False, True),
            ('Storage: Data Domains', 'Text', False, True),
            ('Storage: Data Management Plan', 'Text', False, True),
            ('Storage: Official End Date', 'Date', False, True),
            ('Storage: Storage Quota (GB)', 'Int', False, False),
            ('Storage: Use Indefinitely', 'True/False', False, True),
            ('Storage: Users Group', 'Text', False, True),
            ('Use Type', 'Text', False, True),
            ('Will Exceed Limits', 'Yes/No', False, True),
            ('Allocated Quantity', 'Int', False, False),
            ('Center Identifier', 'Text', False, True),
            ('GID', 'Int', False, True),
            ('LDAP Group', 'Text', False, True),
            ('SMB Enabled', 'Yes/No', False, False),
            ('Slate Project Directory', 'Text', False, False),
        ):
            AllocationAttributeType.objects.get_or_create(name=name, attribute_type=AttributeType.objects.get(
                name=attribute_type), has_usage=has_usage, is_private=is_private)
