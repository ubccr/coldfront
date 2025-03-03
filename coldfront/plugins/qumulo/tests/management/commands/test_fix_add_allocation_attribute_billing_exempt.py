import os
from io import StringIO

from django.test import TestCase

from coldfront.plugins.qumulo.tests.utils.mock_data import build_models
from django.core.management import call_command
from coldfront.core.allocation.models import (
    AttributeType,
    AllocationAttributeType,
)


STORAGE2_PATH = os.environ.get("STORAGE2_PATH")


class TestAddBillingExempt(TestCase):
    def setUp(self) -> None:
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        return super().setUp()

    def test_invalid_default_value(self):
        out = StringIO()
        call_command(
            "fix_add_allocation_attribute_billing_exempt",
            "-d",
            "no",
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("[Error] Invalid: ", output)
        self.assertIn("Invalid Value", output)

    def test_invalid_to_add_billing_exempt(self):
        out = StringIO()
        AllocationAttributeType.objects.update_or_create(
            name="exempt",
            defaults={
                "attribute_type": AttributeType.objects.get(name="Yes/No"),
                "is_required": True,
                "is_private": False,
                "is_changeable": False,
            },
        )
        call_command(
            "fix_add_allocation_attribute_billing_exempt",
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("[Error] Invalid: ", output)
        self.assertIn("Allocation Attribute Types conflict", output)
        self.assertNotIn("Successfully added", output)

    def test_successfully_added(self):
        out = StringIO()
        call_command(
            "fix_add_allocation_attribute_billing_exempt",
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("[Info] Validation Pass", output)
        self.assertIn("[Info] Successfully added", output)
        self.assertNotIn("[Error] Failed to add", output)

    def test_set_default_value(self):
        out = StringIO()
        call_command(
            "fix_add_allocation_attribute_billing_exempt",
            "--default_value",
            "Yes",
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("[Info] Validation Pass", output)
        self.assertIn("[Info] Successfully added", output)
