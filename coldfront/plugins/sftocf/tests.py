from unittest import mock
from unittest.mock import patch, Mock

from django.test import TestCase
from django.contrib.auth import get_user_model

from coldfront.core.utils.fasrc import read_json
from coldfront.plugins.sftocf.utils import (
    StarFishServer,
    AsyncQuery,
    AllocationQueryMatch,
    RedashDataPipeline,
    RedashDataPipeline,
)
from coldfront.core.test_helpers.factories import (setup_models,
                                            UserFactory,
                                            ProjectFactory,
                                            ResourceFactory,
                                            AllocationAttributeFactory,
                                            AllocationAttributeTypeFactory,
                                            AllocationFactory)

UTIL_FIXTURES = [
        "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

class IntegrationTests(TestCase):
    fixtures = UTIL_FIXTURES
    pref = './coldfront/plugins/sftocf/tests/testdata/'

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests.
        """
        setup_models(cls)


class UtilTests(TestCase):
    fixtures = UTIL_FIXTURES
    pref = './coldfront/plugins/sftocf/tests/testdata/'
    dummy_user_usage = [
        {'size_sum': 1046274, 'lab_path': 'C/LABS/poisson_lab', 'vol_name': 'holylfs10', 'user_name': 'sdpoisson'},
        {'size_sum': 20498274, 'lab_path': 'C/LABS/poisson_lab', 'vol_name': 'holylfs10', 'user_name': 'ljbortkiewicz'},
        {'size_sum': 20498274, 'lab_path': 'C/LABS/gordon_lab', 'vol_name': 'holylfs10', 'user_name': 'aalice'}]
    dummy_allocation_usage = [
        {'vol_name': 'holylfs10', 'group_name': 'poisson_lab', 'user_name': 'sdpoisson', 'path': 'C/LABS/poisson_lab', 'total_size': 10749750250},
        {'vol_name': 'holylfs10', 'group_name': 'gordon_lab', 'user_name': 'aalice', 'path': 'C/LABS/gordon_lab', 'total_size': 10749750250}
    ]

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests.
        """
        setup_models(cls)
        aalice = UserFactory(username='aalice', is_staff=False, is_superuser=False)
        UserFactory(username='snewcomb', is_staff=False, is_superuser=False)
        gordon_lab = ProjectFactory(pi=aalice, title="gordon_lab")
        gordon_alloc = AllocationFactory(project=gordon_lab)
        gordon_alloc.resources.add(ResourceFactory(name='holylfs10/tier1', id=1))
        subdir = AllocationAttributeTypeFactory(name='Subdirectory')
        AllocationAttributeFactory(allocation=cls.proj_allocation,
                            allocation_attribute_type=AllocationAttributeTypeFactory(name='Subdirectory'),
                            value='C/LABS/poisson_lab'
                        )

        AllocationAttributeFactory(allocation=gordon_alloc,
                            allocation_attribute_type=subdir,
                            value='C/LABS/gordon_lab'
                        )
