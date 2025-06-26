from django.test import TestCase, Client
from django.utils.timezone import now

from coldfront.plugins.qumulo.utils.billing_result_set import BillingResultSet
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
)
from coldfront.core.allocation.models import (
    AllocationAttributeType,
    AllocationStatusChoice,
    AllocationAttribute,
    AllocationAttributeUsage,
)

from faker.generator import random


class TestBillingResultSet(TestCase):
    def setUp(self):
        self.client = Client()
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        self.default_form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "Uncle Pennybags",
            "billing_exempt": "No",
            "department_number": "Time Travel Services",
            "billing_cycle": "monthly",
            "service_rate": "general",
        }

        self.new_alloc = create_allocation(
            project=self.project, user=self.user, form_data=self.default_form_data
        )

        self.new_alloc.status = AllocationStatusChoice.objects.get(name="Active")
        self.new_alloc.end_date = "2025-08-30"
        self.new_alloc.created = "2025-03-01"
        self.new_alloc.start_date = "2025-03-01"
        self.new_alloc.save()
        subsidized_attribute = AllocationAttributeType.objects.get(name="subsidized")
        AllocationAttribute.objects.create(
            allocation=self.new_alloc,
            allocation_attribute_type=subsidized_attribute,
            value="No",
        )
        storage_quota = self.new_alloc.allocationattribute_set.get(
            allocation_attribute_type__name="storage_quota"
        )
        [
            AllocationAttributeUsage.history.create(
                history_date=now().replace(month=5, day=day),
                allocation_attribute=storage_quota,
                value=round(random.uniform(4e12, 6e12)),
            )
            for day in range(1, 32)
        ]

        self.out_of_date_alloc = create_allocation(
            project=self.project, user=self.user, form_data=self.default_form_data
        )

        self.out_of_date_alloc.status = AllocationStatusChoice.objects.get(
            name="Active"
        )
        self.out_of_date_alloc.end_date = "2024-06-30"
        self.out_of_date_alloc.start_date = "2024-03-01"
        self.out_of_date_alloc.save()

        return super().setUp()

    def test_monthly_billing_cycle_result_set(self):
        listl = BillingResultSet.retrieve_billing_result_set(
            "monthly", "2025-05-01", "2025-05-31"
        )
        count = len([l for l in listl if isinstance(l, dict)])
        expected_usage = AllocationAttributeUsage.history.filter(
            allocation_attribute__allocation=self.new_alloc,
            allocation_attribute__allocation_attribute_type__name="storage_quota",
            history_date__date="2025-05-31",
        ).values("value")
        expected_dict = {
            "billing_cycle": "monthly",
            "cost_center": "Uncle Pennybags",
            "subsidized": "No",
            "billing_exempt": "No",
            "pi": "test",
            "usage": expected_usage[0]["value"],
        }

        self.assertDictEqual(listl[0], expected_dict)
        self.assertEqual(count, 1)
