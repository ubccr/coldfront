# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.core.management.base import BaseCommand

from coldfront.core.allocation.models import (
    AllocationAttributeType,
    AllocationChangeStatusChoice,
    AllocationStatusChoice,
    AllocationUserStatusChoice,
    AttributeType,
)


class Command(BaseCommand):
    help = "Add default allocation related choices"

    def handle(self, *args, **options):
        for attribute_type in ("Date", "Float", "Int", "Text", "Yes/No", "No", "Attribute Expanded Text"):
            AttributeType.objects.get_or_create(name=attribute_type)

        for choice in (
            "Active",
            "Denied",
            "Expired",
            "New",
            "Paid",
            "Payment Pending",
            "Payment Requested",
            "Payment Declined",
            "Renewal Requested",
            "Revoked",
            "Unpaid",
        ):
            AllocationStatusChoice.objects.get_or_create(name=choice)

        for choice in (
            "Pending",
            "Approved",
            "Denied",
        ):
            AllocationChangeStatusChoice.objects.get_or_create(name=choice)

        for choice in ("Active", "Error", "Removed", "PendingEULA", "DeclinedEULA"):
            AllocationUserStatusChoice.objects.get_or_create(name=choice)

        for name, attribute_type, has_usage, is_private, is_required, is_changeable in (
            ("Cloud Account Name", "Text", False, False, False, False),
            ("CLOUD_USAGE_NOTIFICATION", "Yes/No", False, True, False, False),
            ("Core Usage (Hours)", "Int", True, False, False, False),
            ("Accelerator Usage (Hours)", "Int", True, False, False, False),
            ("Cloud Storage Quota (TB)", "Float", True, False, False, False),
            ("EXPIRE NOTIFICATION", "Yes/No", False, True, False, False),
            ("freeipa_group", "Text", False, False, False, False),
            ("Is Course?", "Yes/No", False, True, False, False),
            ("Paid", "Float", False, False, False, False),
            ("Paid Cloud Support (Hours)", "Float", True, True, False, False),
            ("Paid Network Support (Hours)", "Float", True, True, False, False),
            ("Paid Storage Support (Hours)", "Float", True, True, False, False),
            ("Purchase Order Number", "Int", False, True, False, False),
            ("send_expiry_email_on_date", "Date", False, True, False, False),
            ("slurm_account_name", "Text", False, False, False, False),
            ("slurm_specs", "Attribute Expanded Text", False, True, False, False),
            ("slurm_specs_attriblist", "Text", False, True, False, False),
            ("slurm_user_specs", "Attribute Expanded Text", False, True, False, False),
            ("slurm_user_specs_attriblist", "Text", False, True, False, False),
            ("Storage Quota (GB)", "Int", False, False, False, False),
            ("Storage_Group_Name", "Text", False, False, False, False),
            ("SupportersQOS", "Yes/No", False, False, False, False),
            ("SupportersQOSExpireDate", "Date", False, False, False, False),
        ):
            AllocationAttributeType.objects.get_or_create(
                name=name,
                attribute_type=AttributeType.objects.get(name=attribute_type),
                has_usage=has_usage,
                is_private=is_private,
                is_required=is_required,
                is_changeable=is_changeable,
            )
