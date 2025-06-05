from django.test import TestCase, Client

from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
)
from coldfront.core.allocation.models import (
    AllocationStatusChoice,
    AllocationAttributeType,
    AllocationAttribute,
)
from coldfront.plugins.qumulo.management.commands.check_billing_cycles import (
    check_allocation_billing_cycle_and_prepaid_exp,
)

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar
import logging

logger = logging.getLogger(__name__)


class TestBillingCycleTypeUpdates(TestCase):
    def mock_get_attribute(name):
        attribute_dict = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_name": "baz",
            "storage_quota": 7,
            "storage_protocols": '["nfs"]',
        }
        return attribute_dict[name]

    def calculate_future_date(self):
        current = date.today()
        future = current + relativedelta(months=3)
        return future

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

        self.client.force_login(self.user)

    def expected_prepaid_expiration_calculation(allocation):
        prepaid_months = AllocationAttribute.objects.get(
            allocation=allocation,
            allocation_attribute_type__name="prepaid_time",
        ).value

        prepaid_billing_start = AllocationAttribute.objects.get(
            allocation=allocation,
            allocation_attribute_type__name="prepaid_billing_date",
        ).value
        prepaid_billing_start = datetime.strptime(prepaid_billing_start, "%Y-%m-%d")
        prepaid_months = int(prepaid_months)

        prepaid_until = prepaid_billing_start + relativedelta(months=prepaid_months)
        last_day_of_month = (prepaid_billing_start.day == calendar.monthrange(prepaid_billing_start.year, prepaid_billing_start.month)[1])

        if last_day_of_month == True:
            new_day = calendar.monthrange(prepaid_until.year, prepaid_until.month)[1]
            prepaid_until = prepaid_until.replace(day=new_day)

        return prepaid_until

    def test_billing_cycle_manager_past(self):
        prepaid_allocation = create_allocation(
            self.project, self.user, self.prepaid_form_data
        )
        prepaid_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        prepaid_allocation.save()

        check_allocation_billing_cycle_and_prepaid_exp()

        new_billing_cycle = AllocationAttribute.objects.get(
            allocation=prepaid_allocation,
            allocation_attribute_type__name="billing_cycle",
        ).value

        new_prepaid_expiration = AllocationAttribute.objects.get(
            allocation=prepaid_allocation,
            allocation_attribute_type__name="prepaid_expiration",
        ).value
        new_prepaid_expiration = datetime.strptime(
            new_prepaid_expiration, "%Y-%m-%d %H:%M:%S"
        )

        expected_prepaid_exp = (
            TestBillingCycleTypeUpdates.expected_prepaid_expiration_calculation(
                prepaid_allocation
            )
        )
        self.assertEqual(new_billing_cycle, "prepaid")
        self.assertEqual(new_prepaid_expiration, expected_prepaid_exp)

    def test_billing_cycle_manager_future(self):
        self.prepaid_form_data["prepaid_billing_date"] = self.calculate_future_date()
        # form data is submitted with prepaid selection, ideally it should switch to monthly on it's own but this
        # happens outside of billing_cycle_manager so it is set to "monthly" here
        self.prepaid_form_data["billing_cycle"] = "monthly"
        prepaid_future_allocation = create_allocation(
            self.project, self.user, self.prepaid_form_data
        )
        prepaid_future_allocation.status = AllocationStatusChoice.objects.get(
            name="Active"
        )
        prepaid_future_allocation.save()

        check_allocation_billing_cycle_and_prepaid_exp()

        new_billing_cycle = AllocationAttribute.objects.get(
            allocation=prepaid_future_allocation,
            allocation_attribute_type__name="billing_cycle",
        ).value

        self.assertEqual(new_billing_cycle, "monthly")

    def test_billing_cycle_manager_prepaid_today(self):
        self.prepaid_form_data["prepaid_billing_date"] = date.today()
        prepaid_present_allocation = create_allocation(
            self.project, self.user, self.prepaid_form_data
        )
        prepaid_present_allocation.status = AllocationStatusChoice.objects.get(
            name="Active"
        )
        prepaid_present_allocation.save()

        check_allocation_billing_cycle_and_prepaid_exp()

        new_billing_cycle = AllocationAttribute.objects.get(
            allocation=prepaid_present_allocation,
            allocation_attribute_type__name="billing_cycle",
        ).value

        new_prepaid_expiration = AllocationAttribute.objects.get(
            allocation=prepaid_present_allocation,
            allocation_attribute_type__name="prepaid_expiration",
        ).value

        new_service_rate = AllocationAttribute.objects.get(
            allocation=prepaid_present_allocation,
            allocation_attribute_type__name="service_rate",
        ).value
        new_prepaid_expiration = datetime.strptime(
            new_prepaid_expiration, "%Y-%m-%d %H:%M:%S"
        )

        expected_prepaid_exp = (
            TestBillingCycleTypeUpdates.expected_prepaid_expiration_calculation(
                prepaid_present_allocation
            )
        )
        self.assertEqual(new_billing_cycle, "prepaid")
        self.assertEqual(new_service_rate, "subscription")
        self.assertEqual(new_prepaid_expiration, expected_prepaid_exp)

    def test_billing_cycle_manager_expires_today(self):
        prepaid_allocation = create_allocation(
            self.project, self.user, self.prepaid_form_data
        )
        prepaid_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        prepaid_allocation.save()

        prepaid_expiration_attribute = AllocationAttributeType.objects.get(
            name="prepaid_expiration"
        )

        AllocationAttribute.objects.create(
            allocation=prepaid_allocation,
            allocation_attribute_type=prepaid_expiration_attribute,
            value=date.today(),
        )

        check_allocation_billing_cycle_and_prepaid_exp()

        new_billing_cycle = AllocationAttribute.objects.get(
            allocation=prepaid_allocation,
            allocation_attribute_type__name="billing_cycle",
        ).value

        self.assertEqual(new_billing_cycle, "monthly")

    def test_billing_cycle_manager_monthly(self):
        monthly_allocation = create_allocation(
            self.project, self.user, self.monthly_form_data
        )
        monthly_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        monthly_allocation.save()

        check_allocation_billing_cycle_and_prepaid_exp()

        new_billing_cycle = AllocationAttribute.objects.get(
            allocation=monthly_allocation,
            allocation_attribute_type__name="billing_cycle",
        ).value

        self.assertEqual(new_billing_cycle, "monthly")

    def test_prepaid_start_last_of_month(self):
        self.prepaid_form_data["prepaid_billing_date"] = "2025-03-31"
        prepaid_allocation = create_allocation(
            self.project, self.user, self.prepaid_form_data
        )
        prepaid_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        prepaid_allocation.save()

        check_allocation_billing_cycle_and_prepaid_exp()

        date_string = AllocationAttribute.objects.get(
            allocation=prepaid_allocation,
            allocation_attribute_type__name="prepaid_expiration",
        ).value
        date_format = "%Y-%m-%d"

        try:
            datetime.strptime(date_string, date_format)
        except:
            self.fail

    def test_prepaid_on_leap_year(self):
        self.prepaid_form_data["prepaid_billing_date"] = "2024-02-29"
        self.prepaid_form_data["prepaid_time"] = 1
        prepaid_allocation = create_allocation(
            self.project, self.user, self.prepaid_form_data
        )
        prepaid_allocation.status = AllocationStatusChoice.objects.get(name="Active")
        prepaid_allocation.save()

        check_allocation_billing_cycle_and_prepaid_exp()

        date_string = AllocationAttribute.objects.get(
            allocation=prepaid_allocation,
            allocation_attribute_type__name="prepaid_expiration",
        ).value
        date_format = "%Y-%m-%d"

        try:
            datetime.strptime(date_string, date_format)
        except:
            self.fail
           
        self.assertEqual(date_string,"2024-03-31 00:00:00")
