from django.test import TestCase, Client

from coldfront.core.allocation.models import (
    AllocationAttribute,
    AllocationStatusChoice,
)
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
)
from coldfront.plugins.qumulo.management.commands.migrate_allocation_attributes import Command

from datetime import date
from dateutil.relativedelta import relativedelta




class TestMigrateAllocationAttributes(TestCase):
    def calculate_past_date(self):
        current = date.today()
        past = current - relativedelta(months=3)
        return past
    
    def setUp(self):
        self.client = Client()

        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        self.prepaid_form_data = {
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
            "service_rate": "subscription",
            "billing_cycle": "prepaid",
            "prepaid_time": 6,
            "prepaid_billing_date": self.calculate_past_date(),
        }
        self.monthly_form_data = {
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
            "service_rate": "subscription",
            "billing_cycle": "monthly",
        }

        self.no_billing_form_data = {
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
            "service_rate": "subscription",
        }

        self.client.force_login(self.user)

    def test_billing_cycle_is_default_value(self):
        monthly_allocation = create_allocation(
            self.project, self.user, self.monthly_form_data
        )
        monthly_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        monthly_allocation.save()
        
        Command._migrate_allocation_attribute(self, "billing_cycle", "monthly")

        billing_cycle_query = AllocationAttribute.objects.filter(
            allocation=monthly_allocation,allocation_attribute_type__name="billing_cycle"
        )
        billing_cycle_value = AllocationAttribute.objects.get(
            allocation=monthly_allocation,
            allocation_attribute_type__name="billing_cycle",
        ).value
        
        self.assertEqual(billing_cycle_query.count(), 1)
        self.assertEqual(billing_cycle_value, "monthly")
    
    def test_billing_cycle_is_not_default_value(self):
        prepaid_allocation = create_allocation(
            self.project, self.user, self.prepaid_form_data
        )
        prepaid_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        prepaid_allocation.save()

        Command._migrate_allocation_attribute(self, "billing_cycle", "monthly")

        billing_cycle_query = AllocationAttribute.objects.filter(
            allocation=prepaid_allocation,allocation_attribute_type__name="billing_cycle"
        )
        billing_cycle_value = AllocationAttribute.objects.get(
            allocation=prepaid_allocation,
            allocation_attribute_type__name="billing_cycle",
        ).value
        
        self.assertEqual(billing_cycle_query.count(), 1)
        self.assertEqual(billing_cycle_value, "prepaid")
    
    def test_no_billing_cycle(self):
        allocation = create_allocation(
            self.project, self.user, self.no_billing_form_data
        )
        allocation.status = AllocationStatusChoice.objects.get(name="Active")
        allocation.save()
        Command._migrate_allocation_attribute(self, "billing_cycle", "monthly")

        billing_cycle_query = AllocationAttribute.objects.filter(
            allocation=allocation,allocation_attribute_type__name="billing_cycle"
        )
        billing_cycle_value = AllocationAttribute.objects.get(allocation=allocation,allocation_attribute_type__name="billing_cycle",).value
        
        self.assertEqual(billing_cycle_query.count(), 1)
        self.assertEqual(billing_cycle_value, "monthly")
        
        





