import os

from venv import logger
from django.test import TestCase, Client

import unittest
from unittest import mock
from unittest.mock import patch, MagicMock

from coldfront.core.allocation.models import (
    AllocationAttribute,
    AllocationAttributeType,
)

from coldfront.plugins.qumulo.utils import qumulo_api
from coldfront.plugins.qumulo.tasks import ingest_quotas_with_daily_usage
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
)

from qumulo.lib.request import RequestError


def coldfront_allocations() -> str:
    return {
      "/storage2/fs1/sleong": {"limit": "100000000000000"},
      "/storage2/fs1/prewitt_test": {"limit": "1099511627776"},
      "/storage2/fs1/tychele_test": {"limit": "109951162777600"},
      "/storage2/fs1/tychele_test/Active/tychele_suballoc_test": {"limit": "109951162777600"},
      "/storage2/fs1/prewitt_test/Active/prewitt_test_2_a": {"limit": "1099511627776"},
      "/storage2/fs1/prewitt_test_2": {"limit": "1099511627776"},
      "/storage2/fs1/jian_test": {"limit": "10995116277760"},
      "/storage2/fs1/hong.chen_test": {"limit": "5497558138880"},
      "/storage2/fs1/i2_test": {"limit": "109951162777600"},
      "/storage2/fs1/swamidass_test": {"limit": "24189255811072"},
      "/storage2/fs1/prewitt_test_3": {"limit": "5497558138880"},
      "/storage2/fs1/hong.chen_test/Active/hong.chen_suballocation": {"limit": "5497558138880"},
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
      "/SYSTEMS/c2_headnodes": {"limit": "100000000000"},
      "/storage2/fs1/btc": {"limit": "549755813888000"},
      "/storage2/fs1/daryls2_test": {"limit": "5497558138880"},
      "/storage2/fs1/lima": {"limit": "5497558138880"},
      "/storage2/fs1/epigenome": {"limit": "549755813888000"},
      "/storage2/fs1/slenze": {"limit": "5497558138880"},
      "/storage2/fs1/cmasteller": {"limit": "5497558138880"},
      "/storage2/fs1/maihe": {"limit": "5497558138880"},
      "/storage2/fs1/rvmartin": {"limit": "549755813888000"},
      "/storage2/fs1/englands": {"limit": "5497558138880"},
      "/storage2/fs1/shao.j": {"limit": "5497558138880"},
      "/storage2/fs1/molly.schroeder": {"limit": "5497558138880"},
      "/storage2/fs1/debabratapatra": {"limit": "5497558138880"},
      "/storage2/fs1/cifarelli": {"limit": "5497558138880"},
      "/storage2/fs1/engineering": {"limit": "5497558138880"},
      "/storage2/fs1/likai.chen": {"limit": "5497558138880"},
      "/storage2/fs1/mmahjoub": {"limit": "5497558138880"},
      "/storage2/fs1/btc/Active/zipfelg": {"limit": "549755813888000"},
      "/storage2/fs1/sinclair.deborah": {"limit": "5497558138880"},
      "/storage2/fs1/meers": {"limit": "5497558138880"},
      "/storage2/fs1/shawp": {"limit": "5497558138880"},
      "/storage2/fs1/cao.yang": {"limit": "5497558138880"},
      "/storage2/fs1/vtieppofrancio": {"limit": "5497558138880"},
      "/storage2/fs1/elyn": {"limit": "5497558138880"},
      "/storage2/fs1/chsieh": {"limit": "5497558138880"},
      "/storage2/fs1/rfugina": {"limit": "5497558138880"},
      "/storage2/fs1/xmartin": {"limit": "5497558138880"},
      "/storage2/fs1/yixin.chen": {"limit": "5497558138880"},
      "/storage2/fs1/ger": {"limit": "5497558138880"},
      "/storage2/fs1/prewitt_test/Active/john.prewitt.third": {"limit": "1099511627776"},
      "/storage2/fs1/rouse": {"limit": "5497558138880"},
      "/storage2/fs1/w.qian": {"limit": "5497558138880"},
      "/storage2/fs1/epigenome/Active/hprc": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/alberthkim": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/yeli": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/btc-strahlej": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/stegh": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/rubin_j": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/mathios": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/bhuvic.patel": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/yanoh": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/ruit": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/t.eric": {"limit": "549755813888000"},
      "/storage2/fs1/prewitt_test/Active/john.prewitt4": {"limit": "1099511627776"},
      "/storage2/fs1/btc/Active/hongchen": {"limit": "549755813888000"},
      "/storage2/fs1/btc/Active/dang": {"limit": "549755813888000"},
      "/storage2/fs1/dspencer": {"limit": "54975581388800"},
      "/storage2/fs1/ris_snowflake_backup": {"limit": "5497558138880"},
      "/storage2/fs1/jmding": {"limit": "5497558138880"},
      "/storage2/fs1/jmding/Active/x.zhichen": {"limit": "5497558138880"},
      "/storage2/fs1/jmding/Active/j.shiyu": {"limit": "5497558138880"},
      "/storage2/fs1/abrummett": {"limit": "5497558138880"},
      "/storage2/fs1/daryls3": {"limit": "6597069766656"},
      "/storage2/fs1/daryls3/Active/teamfolder": {"limit": "6597069766656"},
      "/storage2/fs1/kdandurand": {"limit": "5497558138880"},
      "/storage2/fs1/vtieppofrancio/Active/Human Subjects Research": {"limit": "5497558138880"},
      "/storage2/fs1/kirilloff": {"limit": "5497558138880"}
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
                "capacity_usage": "37089837494272"
            },
            {
                "id": "34717218",
                "path": "/storage2/fs1/prewitt_test/",
                "limit": "1099511627776",
                "capacity_usage": "61440"
            },
            {
                "id": "36270003",
                "path": "/storage2/fs1/tychele_test/",
                "limit": "109951162777600",
                "capacity_usage": "57344"
            },
            {
                "id": "36290003",
                "path": "/storage2/fs1/tychele_test/Active/tychele_suballoc_test/",
                "limit": "109951162777600",
                "capacity_usage": "4096"
            },
            {
                "id": "36850003",
                "path": "/storage2/fs1/prewitt_test/Active/prewitt_test_2_a/",
                "limit": "1099511627776",
                "capacity_usage": "4096"
            },
            {
                "id": "36860003",
                "path": "/storage2/fs1/prewitt_test_2/",
                "limit": "1099511627776",
                "capacity_usage": "16384"
            },
            {
                "id": "37000005",
                "path": "/storage2/fs1/jian_test/",
                "limit": "10995116277760",
                "capacity_usage": "16384"
            },
            {
                "id": "38760894",
                "path": "/storage2/fs1/hong.chen_test/",
                "limit": "5497558138880",
                "capacity_usage": "40960"
            },
            {
                "id": "38760895",
                "path": "/storage2/fs1/i2_test/",
                "limit": "109951162777600",
                "capacity_usage": "20480"
            },
            {
                "id": "39720243",
                "path": "/storage2/fs1/swamidass_test/",
                "limit": "24189255811072",
                "capacity_usage": "16384"
            },
            {
                "id": "39720382",
                "path": "/storage2/fs1/prewitt_test_3/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "42020003",
                "path": "/storage2/fs1/hong.chen_test/Active/hong.chen_suballocation/",
                "limit": "5497558138880",
                "capacity_usage": "4096"
            },
            {
                "id": "42030003",
                "path": "/storage2/fs1/engineering_test/",
                "limit": "5497558138880",
                "capacity_usage": "307247931392"
            },
            {
                "id": "42030004",
                "path": "/storage2/fs1/sleong_summer/",
                "limit": "5497558138880",
                "capacity_usage": "715557855232"
            },
            {
                "id": "42050003",
                "path": "/storage2/fs1/wexler_test/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "42080003",
                "path": "/storage2/fs1/alex.holehouse_test/",
                "limit": "38482906972160",
                "capacity_usage": "16384"
            },
            {
                "id": "42080004",
                "path": "/storage2/fs1/wucci/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "42130003",
                "path": "/storage2/fs1/amlai/",
                "limit": "5497558138880",
                "capacity_usage": "4198400"
            },
            {
                "id": "43010004",
                "path": "/storage2/fs1/jin810_test/",
                "limit": "109951162777600",
                "capacity_usage": "27430019072"
            },
            {
                "id": "43010005",
                "path": "/storage2/fs1/dinglab_test/",
                "limit": "109951162777600",
                "capacity_usage": "16384"
            },
            {
                "id": "43050003",
                "path": "/storage2/fs1/wucci_test/",
                "limit": "109951162777600",
                "capacity_usage": "16384"
            },
            {
                "id": "43070003",
                "path": "/storage2/fs1/gtac-mgi_test2/",
                "limit": "5497558138880",
                "capacity_usage": "1477898227712"
            },
            {
                "id": "52929566",
                "path": "/storage2/fs1/mweil_test/",
                "limit": "5497558138880",
                "capacity_usage": "1436366471168"
            },
            {
                "id": "52929567",
                "path": "/storage2/fs1/amlai_test2/",
                "limit": "16492674416640",
                "capacity_usage": "997732352"
            },
            {
                "id": "52929568",
                "path": "/storage2/fs1/tychele_test2/",
                "limit": "109951162777600",
                "capacity_usage": "16384"
            },
            {
                "id": "59261672",
                "path": "/SYSTEMS/c2_headnodes/",
                "limit": "100000000000",
                "capacity_usage": "4096"
            },
            {
                "id": "59542211",
                "path": "/storage2/fs1/btc/",
                "limit": "549755813888000",
                "capacity_usage": "19199531061248"
            },
            {
                "id": "59660033",
                "path": "/storage2/fs1/daryls2_test/",
                "limit": "5497558138880",
                "capacity_usage": "24576"
            },
            {
                "id": "59660050",
                "path": "/storage2/fs1/lima/",
                "limit": "5497558138880",
                "capacity_usage": "992269512704"
            },
            {
                "id": "60070040",
                "path": "/storage2/fs1/epigenome/",
                "limit": "549755813888000",
                "capacity_usage": "208678040436736"
            },
            {
                "id": "60070105",
                "path": "/storage2/fs1/slenze/",
                "limit": "5497558138880",
                "capacity_usage": "1045441581056"
            },
            {
                "id": "61890004",
                "path": "/storage2/fs1/cmasteller/",
                "limit": "5497558138880",
                "capacity_usage": "3420031524864"
            },
            {
                "id": "61890005",
                "path": "/storage2/fs1/maihe/",
                "limit": "5497558138880",
                "capacity_usage": "878341009408"
            },
            {
                "id": "64050003",
                "path": "/storage2/fs1/rvmartin/",
                "limit": "549755813888000",
                "capacity_usage": "3005194760192"
            },
            {
                "id": "64200003",
                "path": "/storage2/fs1/englands/",
                "limit": "5497558138880",
                "capacity_usage": "12005720064"
            },
            {
                "id": "64450003",
                "path": "/storage2/fs1/shao.j/",
                "limit": "5497558138880",
                "capacity_usage": "240298074112"
            },
            {
                "id": "64550003",
                "path": "/storage2/fs1/molly.schroeder/",
                "limit": "5497558138880",
                "capacity_usage": "4016470769664"
            },
            {
                "id": "65120003",
                "path": "/storage2/fs1/debabratapatra/",
                "limit": "5497558138880",
                "capacity_usage": "1203736469504"
            },
            {
                "id": "65120004",
                "path": "/storage2/fs1/cifarelli/",
                "limit": "5497558138880",
                "capacity_usage": "1069997703168"
            },
            {
                "id": "67009033",
                "path": "/storage2/fs1/engineering/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "67710045",
                "path": "/storage2/fs1/likai.chen/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "67920016",
                "path": "/storage2/fs1/mmahjoub/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "68000005",
                "path": "/storage2/fs1/btc/Active/zipfelg/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "68024702",
                "path": "/storage2/fs1/sinclair.deborah/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "69020003",
                "path": "/storage2/fs1/meers/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "69020004",
                "path": "/storage2/fs1/shawp/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "69080003",
                "path": "/storage2/fs1/cao.yang/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "69080004",
                "path": "/storage2/fs1/vtieppofrancio/",
                "limit": "5497558138880",
                "capacity_usage": "20480"
            },
            {
                "id": "69140003",
                "path": "/storage2/fs1/elyn/",
                "limit": "5497558138880",
                "capacity_usage": "20480"
            },
            {
                "id": "69280003",
                "path": "/storage2/fs1/chsieh/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "69280012",
                "path": "/storage2/fs1/rfugina/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "69460003",
                "path": "/storage2/fs1/xmartin/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "69460004",
                "path": "/storage2/fs1/yixin.chen/",
                "limit": "5497558138880",
                "capacity_usage": "538255843328"
            },
            {
                "id": "69460005",
                "path": "/storage2/fs1/ger/",
                "limit": "5497558138880",
                "capacity_usage": "21024497664"
            },
            {
                "id": "73020003",
                "path": "/storage2/fs1/prewitt_test/Active/john.prewitt.third/",
                "limit": "1099511627776",
                "capacity_usage": "4096"
            },
            {
                "id": "74040003",
                "path": "/storage2/fs1/rouse/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "74040004",
                "path": "/storage2/fs1/w.qian/",
                "limit": "5497558138880",
                "capacity_usage": "30986240"
            },
            {
                "id": "74070003",
                "path": "/storage2/fs1/epigenome/Active/hprc/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74740003",
                "path": "/storage2/fs1/btc/Active/alberthkim/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74750003",
                "path": "/storage2/fs1/btc/Active/yeli/",
                "limit": "549755813888000",
                "capacity_usage": "16665915707392"
            },
            {
                "id": "74760003",
                "path": "/storage2/fs1/btc/Active/btc-strahlej/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74770003",
                "path": "/storage2/fs1/btc/Active/stegh/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74770004",
                "path": "/storage2/fs1/btc/Active/rubin_j/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74770005",
                "path": "/storage2/fs1/btc/Active/mathios/",
                "limit": "549755813888000",
                "capacity_usage": "2298337992704"
            },
            {
                "id": "74780003",
                "path": "/storage2/fs1/btc/Active/bhuvic.patel/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74780004",
                "path": "/storage2/fs1/btc/Active/yanoh/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74790003",
                "path": "/storage2/fs1/btc/Active/ruit/",
                "limit": "549755813888000",
                "capacity_usage": "235277299712"
            },
            {
                "id": "74800003",
                "path": "/storage2/fs1/btc/Active/t.eric/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74820003",
                "path": "/storage2/fs1/prewitt_test/Active/john.prewitt4/",
                "limit": "1099511627776",
                "capacity_usage": "4096"
            },
            {
                "id": "74830003",
                "path": "/storage2/fs1/btc/Active/hongchen/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74840003",
                "path": "/storage2/fs1/btc/Active/dang/",
                "limit": "549755813888000",
                "capacity_usage": "4096"
            },
            {
                "id": "74850003",
                "path": "/storage2/fs1/dspencer/",
                "limit": "54975581388800",
                "capacity_usage": "14795144687616"
            },
            {
                "id": "74860003",
                "path": "/storage2/fs1/ris_snowflake_backup/",
                "limit": "5497558138880",
                "capacity_usage": "37263634432"
            },
            {
                "id": "75970003",
                "path": "/storage2/fs1/jmding/",
                "limit": "5497558138880",
                "capacity_usage": "24576"
            },
            {
                "id": "75990003",
                "path": "/storage2/fs1/jmding/Active/x.zhichen/",
                "limit": "5497558138880",
                "capacity_usage": "4096"
            },
            {
                "id": "76000003",
                "path": "/storage2/fs1/jmding/Active/j.shiyu/",
                "limit": "5497558138880",
                "capacity_usage": "4096"
            },
            {
                "id": "77340788",
                "path": "/storage2/fs1/abrummett/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "79710003",
                "path": "/storage2/fs1/daryls3/",
                "limit": "6597069766656",
                "capacity_usage": "20480"
            },
            {
                "id": "79730003",
                "path": "/storage2/fs1/daryls3/Active/teamfolder/",
                "limit": "6597069766656",
                "capacity_usage": "4096"
            },
            {
                "id": "79770003",
                "path": "/storage2/fs1/kdandurand/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            },
            {
                "id": "80790003",
                "path": "/storage2/fs1/vtieppofrancio/Active/Human Subjects Research/",
                "limit": "5497558138880",
                "capacity_usage": "4096"
            },
            {
                "id": "80800003",
                "path": "/storage2/fs1/kirilloff/",
                "limit": "5497558138880",
                "capacity_usage": "16384"
            }
        ],
        "paging": {
            "next": ""
        },
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

    def test_qumulo_result_set_page_limit_should_be_set(self) -> None:
        page_limit = qumulo_api.QumuloAPI.get_result_set_page_limit()
        self.assertIsNotNone(page_limit)

    @unittest.skip("Until we have a chance to propagte the ENV variable.")
    @mock.patch.dict(os.environ, {"QUMULO_RESULT_SET_PAGE_LIMIT": ""})
    def test_qumulo_result_set_page_limit_should_raise_an_exception_if_not_set(self) -> None:
        with self.assertRaises(TypeError):
            qumulo_api.QumuloAPI.get_result_set_page_limit()

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
            self.assertEqual(allocation_attribute_usage.history.count(), 1)

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
            self.assertEqual(allocation_attribute_usage.history.first().value, usage)
            self.assertGreater(allocation_attribute_usage.history.count(), 1)
