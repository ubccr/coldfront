from venv import logger
from django.test import TestCase, Client

from unittest.mock import patch, MagicMock

from coldfront.core.allocation.models import (
    AllocationAttribute,
    AllocationAttributeType,
)
from coldfront.plugins.qumulo.tasks import ingest_quotas_with_daily_usage
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
)

from qumulo.lib.request import RequestError


def coldfront_allocations() -> str:
    return {
        "/storage2/fs1/sleong/": {"limit": "100000000000000"},
        "/storage2/fs1/prewitt_test/": {"limit": "1099511627776"},
        "/storage2/fs1/tychele_test": {"limit": "109951162777600"},
        "/storage2/fs1/tychele_test/Active/tychele_suballoc_test": {
            "limit": "109951162777600"
        },
        "/storage2/fs1/prewitt_test/Active/prewitt_test_2_a": {
            "limit": "1099511627776"
        },
        "/storage2/fs1/prewitt_test_2": {"limit": "1099511627776"},
        "/storage2/fs1/jian_test": {"limit": "10995116277760"},
        "/storage2/fs1/hong.chen_test": {"limit": "5497558138880"},
        "/storage2/fs1/i2_test": {"limit": "109951162777600"},
        "/storage2/fs1/swamidass_test": {"limit": "24189255811072"},
        "/storage2/fs1/prewitt_test_3": {"limit": "5497558138880"},
        "/storage2/fs1/hong.chen_test/Active/hong.chen_suballocation": {
            "limit": "5497558138880"
        },
        "/storage2/fs1/engineering_test": {"limit": "5497558138880"},
        "/storage2/fs1/sleong_summer": {"limit": "5497558138880"},
        "/storage2/fs1/wexler_test": {"limit": "5497558138880"},
        "/storage2/fs1/alex.holehouse_test": {"limit": "38482906972160"},
        "/storage2/fs1/wucci": {"limit": "5497558138880"},
        "/storage2/fs1/amlai": {"limit": "5497558138880"},
        "/storage2/fs1/jin810_test": {"limit": "109951162777600"},
        "/storage2/fs1/dinglab_test": {"limit": "109951162777600"},
        "/storage2/fs1/wucci_test": {"limit": "109951162777600"},
        "/storage2/fs1/gtac-mgi_test2": {"limit": "5497558138880"},
        "/storage2/fs1/mweil_test": {"limit": "5497558138880"},
        "/storage2/fs1/amlai_test2": {"limit": "16492674416640"},
        "/storage2/fs1/tychele_test2": {"limit": "109951162777600"},
    }


def mock_get_quotas() -> str:
    return {
        "quotas": [
            {
                "id": "111111111",
                "path": "/storage2/fs1/not_found_in_coldfront/",
                "limit": "20000000000000",
                "capacity_usage": "1",
            },
            {
                "id": "18600003",
                "path": "/storage2/fs1/sleong/",
                "limit": "100000000000000",
                "capacity_usage": "37089736126464",
            },
            {
                "id": "34717218",
                "path": "/storage2/fs1/prewitt_test/",
                "limit": "1099511627776",
                "capacity_usage": "53248",
            },
            {
                "id": "36270003",
                "path": "/storage2/fs1/tychele_test/",
                "limit": "109951162777600",
                "capacity_usage": "57344",
            },
            {
                "id": "36290003",
                "path": "/storage2/fs1/tychele_test/Active/tychele_suballoc_test/",
                "limit": "109951162777600",
                "capacity_usage": "4096",
            },
            {
                "id": "36850003",
                "path": "/storage2/fs1/prewitt_test/Active/prewitt_test_2_a/",
                "limit": "1099511627776",
                "capacity_usage": "4096",
            },
            {
                "id": "36860003",
                "path": "/storage2/fs1/prewitt_test_2/",
                "limit": "1099511627776",
                "capacity_usage": "16384",
            },
            {
                "id": "37000005",
                "path": "/storage2/fs1/jian_test/",
                "limit": "10995116277760",
                "capacity_usage": "16384",
            },
            {
                "id": "38760894",
                "path": "/storage2/fs1/hong.chen_test/",
                "limit": "5497558138880",
                "capacity_usage": "40960",
            },
            {
                "id": "38760895",
                "path": "/storage2/fs1/i2_test/",
                "limit": "109951162777600",
                "capacity_usage": "20480",
            },
            {
                "id": "39720243",
                "path": "/storage2/fs1/swamidass_test/",
                "limit": "24189255811072",
                "capacity_usage": "16384",
            },
            {
                "id": "39720382",
                "path": "/storage2/fs1/prewitt_test_3/",
                "limit": "5497558138880",
                "capacity_usage": "16384",
            },
            {
                "id": "42020003",
                "path": "/storage2/fs1/hong.chen_test/Active/hong.chen_suballocation/",
                "limit": "5497558138880",
                "capacity_usage": "4096",
            },
            {
                "id": "42030003",
                "path": "/storage2/fs1/engineering_test/",
                "limit": "5497558138880",
                "capacity_usage": "307242479616",
            },
            {
                "id": "42030004",
                "path": "/storage2/fs1/sleong_summer/",
                "limit": "5497558138880",
                "capacity_usage": "713363001344",
            },
            {
                "id": "42050003",
                "path": "/storage2/fs1/wexler_test/",
                "limit": "5497558138880",
                "capacity_usage": "16384",
            },
            {
                "id": "42080003",
                "path": "/storage2/fs1/alex.holehouse_test/",
                "limit": "38482906972160",
                "capacity_usage": "16384",
            },
            {
                "id": "42080004",
                "path": "/storage2/fs1/wucci/",
                "limit": "5497558138880",
                "capacity_usage": "16384",
            },
            {
                "id": "42130003",
                "path": "/storage2/fs1/amlai/",
                "limit": "5497558138880",
                "capacity_usage": "4198400",
            },
            {
                "id": "43010004",
                "path": "/storage2/fs1/jin810_test/",
                "limit": "109951162777600",
                "capacity_usage": "16384",
            },
            {
                "id": "43010005",
                "path": "/storage2/fs1/dinglab_test/",
                "limit": "109951162777600",
                "capacity_usage": "16384",
            },
            {
                "id": "43050003",
                "path": "/storage2/fs1/wucci_test/",
                "limit": "109951162777600",
                "capacity_usage": "16384",
            },
            {
                "id": "43070003",
                "path": "/storage2/fs1/gtac-mgi_test2/",
                "limit": "5497558138880",
                "capacity_usage": "1477898227712",
            },
            {
                "id": "52929566",
                "path": "/storage2/fs1/mweil_test/",
                "limit": "5497558138880",
                "capacity_usage": "1436366471168",
            },
            {
                "id": "52929567",
                "path": "/storage2/fs1/amlai_test2/",
                "limit": "16492674416640",
                "capacity_usage": "997732352",
            },
            {
                "id": "52929568",
                "path": "/storage2/fs1/tychele_test2/",
                "limit": "109951162777600",
                "capacity_usage": "18083368955904",
            },
        ],
        "paging": {"next": ""},
    }


class TestIngestAllocationDailyUsages(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]
        self.quotas = mock_get_quotas()

        for index, (path, details) in enumerate(coldfront_allocations().items()):

            form_data = {
                "storage_filesystem_path": path,
                "storage_export_path": path,
                "storage_name": f"for_tester_{index}",
                "storage_quota": details.get("limit"),
                "protocols": ["nfs"],
                "rw_users": [f"user_{index}_rw"],
                "ro_users": [f"user_{index}_ro"],
                "storage_ticket": f"ITSD-{index}",
                "cost_center": "Uncle Pennybags",
                "department_number": "Time Travel Services",
                "service_rate": "general",
            }
            create_allocation(project=self.project, user=self.user, form_data=form_data)

        self.storage_filesystem_path_attribute_type = (
            AllocationAttributeType.objects.get(name="storage_filesystem_path")
        )
        self.storage_quota_attribute_type = AllocationAttributeType.objects.get(
            name="storage_quota"
        )

        return super().setUp()

    def test_after_allocation_create_usage_is_zero(self) -> None:

        # after allocations are created, expect usage to be zero
        for path in coldfront_allocations():
            allocation_attribute_usage = None
            try:
                storage_filesystem_path_attribute = AllocationAttribute.objects.get(
                    value=path,
                    allocation_attribute_type=self.storage_filesystem_path_attribute_type,
                )
                allocation = storage_filesystem_path_attribute.allocation
                storage_quota_attribute_type = AllocationAttribute.objects.get(
                    allocation=allocation,
                    allocation_attribute_type=self.storage_quota_attribute_type,
                )
                allocation_attribute_usage = (
                    storage_quota_attribute_type.allocationattributeusage
                )
            except AllocationAttribute.DoesNotExist:
                # When the storage_path_attribute for path is not found,
                # the allocation_attribute_usage should not exist.
                self.assertIsNone(allocation_attribute_usage)
                continue

            self.assertEqual(allocation_attribute_usage.value, 0)
            self.assertEqual(allocation_attribute_usage.history.first().value, 0)

    @patch("coldfront.plugins.qumulo.tasks.QumuloAPI")
    def test_after_getting_daily_usages_from_qumulo_api(
        self, qumulo_api_mock: MagicMock
    ) -> None:
        qumulo_api = MagicMock()
        qumulo_api.get_all_quotas_with_usage.return_value = mock_get_quotas()
        qumulo_api_mock.return_value = qumulo_api

        exceptionRaised = False
        try:
            ingest_quotas_with_daily_usage()
        except:
            exceptionRaised = True

        self.assertFalse(exceptionRaised)

        for qumulo_quota in self.quotas["quotas"]:

            allocation_attribute_usage = None
            try:
                try:
                    storage_filesystem_path_attribute = AllocationAttribute.objects.get(
                        value=qumulo_quota.get("path"),
                        allocation_attribute_type=self.storage_filesystem_path_attribute_type,
                    )
                except AllocationAttribute.DoesNotExist:
                    path = qumulo_quota.get("path")
                    if path[-1] != "/":
                        continue

                    storage_filesystem_path_attribute = AllocationAttribute.objects.get(
                        value=path[:-1],
                        allocation_attribute_type=self.storage_filesystem_path_attribute_type,
                    )

                allocation = storage_filesystem_path_attribute.allocation
                storage_quota_attribute = AllocationAttribute.objects.get(
                    allocation=allocation,
                    allocation_attribute_type=self.storage_quota_attribute_type,
                )

                allocation_attribute_usage = (
                    storage_quota_attribute.allocationattributeusage
                )
            except AllocationAttribute.DoesNotExist:
                # When the storage_path_attribute for path is not found,
                # the allocation_attribute_usage should not exist.
                self.assertIsNone(allocation_attribute_usage)
                continue

            usage = int(qumulo_quota.get("capacity_usage"))
            self.assertEqual(allocation_attribute_usage.value, usage)
            self.assertEqual(
                allocation_attribute_usage.history.first().value,
                usage,
            )
