import os
import csv
import re
import hashlib
from datetime import datetime, timezone

from django.db import connection
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock

from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
    AllocationAttributeType,
    AllocationLinkage,
)
from coldfront.plugins.qumulo.tasks import ingest_quotas_with_daily_usage
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
)

from coldfront.plugins.qumulo.utils.prepaid_billing import PrepaidBilling

STORAGE2_PATH = os.environ.get("STORAGE2_PATH")

REPORT_COLUMNS = [
    "fields",
    "spreadsheet_key",
    "add_only",
    "auto_complete",
    "internal_service_delivery_id",
    "submit",
    "company",
    "internal_service_provider",
    "currency",
    "document_date",
    "memo",
    "row_id",
    "internal_service_delivery_line_id",
    "internal_service_delivery_line_number",
    "item_description",
    "spend_category",
    "quantity",
    "unit_of_measure",
    "unit_cost",
    "extended_amount",
    "requester",
    "delivery_date",
    "memo_filesets",
    "cost_center",
    "prepaid_expiration",
    "prepaid_time",
    "fund",
    "spacer_1",
    "spacer_2",
    "spacer_3",
    "usage",
    "rate",
    "unit",
]


def construct_allocation_form_data(quota_tb: int, service_rate_category: str):
    form_data = {
        "storage_name": f"{quota_tb}tb-{service_rate_category}",
        "storage_quota": str(quota_tb),
        "protocols": ["smb"],
        "storage_filesystem_path": f"{STORAGE2_PATH}/{quota_tb}tb-{service_rate_category}",
        "storage_export_path": f"{STORAGE2_PATH}/{quota_tb}tb-{service_rate_category}",
        "rw_users": ["test"],
        "ro_users": ["test1"],
        "storage_ticket": "ITSD-1234",
        "cost_center": "CC0000123",
        "department_number": "CH000123",
        "billing_cycle": "monthly",
        "service_rate": service_rate_category,
    }
    return form_data


def construct_suballocation_form_data(quota_tb: int, parent_allocation: Allocation):
    form_data = {
        "parent_allocation_name": parent_allocation.get_attribute("storage_name"),
        "storage_name": f"{quota_tb}tb-suballocation",
        "storage_quota": str(quota_tb),
        "protocols": ["smb"],
        "storage_filesystem_path": f"{parent_allocation.get_attribute('storage_filesystem_path')}/Active/{quota_tb}tb-suballocation",
        "storage_export_path": f"{parent_allocation.get_attribute('storage_export_path')}/Active/{quota_tb}tb-suballocation",
        "rw_users": ["test"],
        "ro_users": ["test1"],
        "storage_ticket": "ITSD-1234",
        "cost_center": parent_allocation.get_attribute("cost_center"),
        "prepaid_billing_date": "2025-01-01",
        "prepaid_time": 5,
        "department_number": parent_allocation.get_attribute("department_number"),
        "billing_cycle": parent_allocation.get_attribute("billing_cycle"),
        "service_rate": parent_allocation.get_attribute("service_rate"),
    }
    return form_data


def construct_usage_data_in_json(filesystem_path: str, quota: str, usage: str):
    quota_in_json = {
        "id": "100",
        "path": f"{filesystem_path}",
        "limit": f"{quota}",
        "capacity_usage": f"{usage}",
    }
    return quota_in_json


def mock_get_quota_service_rate_categories():
    allocation_attributes = [
        (5, "subscription"),
        (100, "subscription"),
        (500, "subscription"),
        (500, "subscription_500tb"),
    ]
    return allocation_attributes


def mock_get_names_quotas_usages():
    names_quotas_usages = [
        ("5tb-subscription", "5000000000000", "1"),
        ("100tb-subscription", "100000000000000", "20"),
        ("500tb-subscription", "500000000000000", "200000000000000"),
        ("500tb-subscription_500tb", "500000000000000", "2"),
    ]
    return names_quotas_usages


def mock_get_multiple_quotas() -> str:
    usages_in_json = []
    json_id = 100
    for name, quota, usage in mock_get_names_quotas_usages():
        usage_in_json = construct_usage_data_in_json(
            f"{STORAGE2_PATH}/{name}", quota, usage
        )
        usage_in_json[id] = json_id
        usages_in_json.append(usage_in_json)
        json_id += 1

    return {
        "quotas": usages_in_json,
    }


def mock_get_quota() -> str:
    name = "15tb-consumption"
    quota = "15000000000000"
    usage = "10995116277760"
    suballocation_name = "5tb-suballocation"
    suballocation_quota = "5000000000000"
    suballocation_usage = "5497558138880"
    usage_in_json = [
        {
            "id": "101",
            "path": f"{STORAGE2_PATH}/{name}/",
            "limit": f"{quota}",
            "capacity_usage": f"{usage}",
        },
        {
            "id": "102",
            "path": f"{STORAGE2_PATH}/{name}/Active/{suballocation_name}",
            "limit": f"{suballocation_quota}",
            "capacity_usage": f"{suballocation_usage}",
        },
    ]

    return {
        "quotas": usage_in_json,
    }


class TestPrepaidBilling(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        self.storage_filesystem_path_attribute_type = (
            AllocationAttributeType.objects.get(name="storage_filesystem_path")
        )
        self.storage_quota_attribute_type = AllocationAttributeType.objects.get(
            name="storage_quota"
        )
        return super().setUp()

    def test_header_return_csv(self):
        prepaid_billing = PrepaidBilling(
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        header = prepaid_billing.get_report_header()
        self.assertTrue(re.search("^Submit Internal Service Delivery(,){27}", header))
        self.assertEqual(
            hashlib.md5(header.encode("utf-8")).hexdigest(),
            "368fd336dff3d8824ce9012799774c51",
        )

    def test_query_return_sql_statement(self):
        prepaid_billing = PrepaidBilling(
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        args = dict()
        args["document_date"] = datetime.today().strftime("%m/%d/%Y")
        args["billing_month"] = prepaid_billing.billing_month
        args["delivery_date"] = prepaid_billing.delivery_date
        self.assertTrue(
            re.search("^\s*SELECT\s*", prepaid_billing.get_query(args, "prepaid"))
        )

    @patch("coldfront.plugins.qumulo.tasks.QumuloAPI")
    def test_create_multiple_allocations_ingest_usages_generate_billing_report(
        self, qumulo_api_mock: MagicMock
    ) -> None:
        qumulo_api = MagicMock()
        qumulo_api.get_all_quotas_with_usage.return_value = mock_get_multiple_quotas()
        qumulo_api_mock.return_value = qumulo_api

        quota_service_rate_categories = mock_get_quota_service_rate_categories()

        for quota, service_rate_category in quota_service_rate_categories:
            allocation = create_allocation(
                project=self.project,
                user=self.user,
                form_data=construct_allocation_form_data(quota, service_rate_category),
            )

            allocation.status = AllocationStatusChoice.objects.get(name="Active")
            allocation.save()

        storage2_allocations = Allocation.objects.filter(
            resources__name="Storage2", status__name__in=["Active"]
        )
        self.assertEqual(len(storage2_allocations), len(quota_service_rate_categories))

        ingest_quotas_with_daily_usage()
        prepaid_billing = PrepaidBilling(
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        prepaid_billing.generate_prepaid_billing_report()

        filename = prepaid_billing.get_filename()
        with open(filename) as csvreport:
            data = list(csv.reader(csvreport))

        header = prepaid_billing.get_report_header()
        num_lines_header = len(header.splitlines())
        print("Numer of lines of the report header: %s" % num_lines_header)
        self.assertEqual(num_lines_header, 5)

        billing_entries = []
        for index in range(num_lines_header, len(data)):
            billing_entries.append(data[index])

        row_num_index = REPORT_COLUMNS.index("spreadsheet_key")
        billing_amount_index = REPORT_COLUMNS.index("extended_amount")
        fileset_memo_index = REPORT_COLUMNS.index("memo_filesets")
        for index in range(0, len(billing_entries)):
            row_num = billing_entries[index][row_num_index]
            self.assertEqual(str(index + 1), row_num)
            billing_amount = billing_entries[index][billing_amount_index].replace(
                '"', ""
            )
            fileset_memo = billing_entries[index][fileset_memo_index].replace('"', "")

            # Confirm the billing amounts of each test cases
            # hardcoded
            if fileset_memo == "5tb-subscription":
                self.assertEqual(float(billing_amount) - 634.0, 0)
            elif fileset_memo == "100tb-subscription":
                self.assertEqual(float(billing_amount) - 634.0, 0)
            elif fileset_memo == "500tb-subscription":
                self.assertEqual(float(billing_amount) - 3170.0, 0)
            elif fileset_memo == "500tb-subscription_500tb":
                self.assertEqual(float(billing_amount) - 2643.0, 0)
            elif fileset_memo == "500tb-condo":
                self.assertEqual(float(billing_amount) - 529.0, 0)
            else:
                print(fileset_memo, billing_amount)
                self.assertFalse(True)

        os.remove(filename)

    @patch("coldfront.plugins.qumulo.tasks.QumuloAPI")
    def test_create_a_suballocation_ingest_usage_and_generate_billing_report(
        self, qumulo_api_mock: MagicMock
    ) -> None:
        qumulo_api = MagicMock()
        qumulo_api.get_all_quotas_with_usage.return_value = mock_get_quota()
        qumulo_api_mock.return_value = qumulo_api

        allocation = create_allocation(
            project=self.project,
            user=self.user,
            form_data=construct_allocation_form_data(100, "subscription"),
        )

        allocation.status = AllocationStatusChoice.objects.get(name="Active")
        allocation.save()

        suballocation = create_allocation(
            project=self.project,
            user=self.user,
            form_data=construct_suballocation_form_data(10, allocation),
            parent=allocation,
        )

        suballocation.status = AllocationStatusChoice.objects.get(name="Active")
        suballocation.save()

        # Confirm creating 2 Storage2 allocations, 1 parent and 1 child
        num_storage2_allocations = len(
            Allocation.objects.filter(resources__name="Storage2")
        )
        self.assertEqual(2, num_storage2_allocations)

        # Confirm the existence of the sub allocation
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*)
                FROM allocation_allocationlinkage_children alc
                JOIN allocation_allocation a
                    ON alc.allocation_id = a.id
            """
            )
            rows = cursor.fetchall()

        self.assertEqual(1, rows[0][0])

        allocation_linkages = AllocationLinkage.objects.all()
        num_linkages = len(allocation_linkages)
        self.assertEqual(1, num_linkages)

        num_suballocations = 0
        for linkage in allocation_linkages:
            num_suballocations += len(linkage.children.all())

        self.assertEqual(1, num_suballocations)

        ingest_quotas_with_daily_usage()
        prepaid_billing = PrepaidBilling(
            datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        prepaid_billing.generate_prepaid_billing_report()

        filename = prepaid_billing.get_filename()
        with open(filename) as csvreport:
            data = list(csv.reader(csvreport))

        num_lines_header = len(prepaid_billing.get_report_header().splitlines())

        billing_entries = []
        for index in range(num_lines_header, len(data)):
            billing_entries.append(data[index])

        row_num_index = REPORT_COLUMNS.index("spreadsheet_key")
        billing_amount_index = REPORT_COLUMNS.index("extended_amount")
        fileset_memo_index = REPORT_COLUMNS.index("memo_filesets")
        for index in range(0, len(billing_entries)):
            row_num = billing_entries[index][row_num_index]
            self.assertEqual(str(index + 1), row_num)
            billing_amount = billing_entries[index][billing_amount_index].replace(
                '"', ""
            )
            fileset_memo = billing_entries[index][fileset_memo_index].replace('"', "")

            # Confirm no billing entry for the sub allocation
            self.assertEqual(fileset_memo, "100tb-subscription")

        os.remove(filename)
