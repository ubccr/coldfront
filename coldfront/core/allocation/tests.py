import unittest

from django.db.models import Count
from django.test import TestCase, Client
from django.urls import reverse, reverse_lazy
from django.contrib.auth import get_user_model

from coldfront.core.allocation.models import Allocation, AllocationAttribute, AllocationAttributeUsage


class AllocationQC(unittest.TestCase):
    def check_resource_quotas(self):
        zero_quotas = AllocationAttribute.objects.filter(allocation_attribute_type__in=[1,5], value=0)
        self.assertEqual(zero_quotas.count(), 0)
                                                         
    def check_resource_counts(self):
        over_one = Allocation.objects.annotate(resource_count=Count('resources')).filter(resource_count__gt=1)
        print(over_one)
        self.assertEqual(over_one.count(), 0)


class AllocationViewTest(TestCase):
    fixtures = [
                "coldfront/core/test_helpers/test_data/test_fixtures/poisson_fixtures.json",
                "coldfront/core/test_helpers/test_data/test_fixtures/admin_fixtures.json",
                "coldfront/core/test_helpers/test_data/test_fixtures/all_res_choices.json",
                "coldfront/core/test_helpers/test_data/test_fixtures/field_of_science.json",
                "coldfront/core/test_helpers/test_data/test_fixtures/project_choices.json",
                ]

    def setUp(self):
        user = get_user_model().objects.get(username="gvanrossum")
        self.c = Client()
        self.c.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
        # did_login_succeed = self.c.login(username='gvanrossum', password="python")
        # self.assertTrue(did_login_succeed)

    def test_allocation_list_template(self):
        """Confirm that allocation-list renders correctly
        """
        response = self.c.get("/allocation/")
        # response = self.client.get(reverse_lazy('allocation-list'))
        self.assertEqual(response.status_code, 200)


class AllocationDetailViewTest(TestCase):

    fixtures = [
                "coldfront/core/test_helpers/test_data/test_fixtures/poisson_fixtures.json",
                "coldfront/core/test_helpers/test_data/test_fixtures/admin_fixtures.json",
                "coldfront/core/test_helpers/test_data/test_fixtures/all_res_choices.json",
                "coldfront/core/test_helpers/test_data/test_fixtures/field_of_science.json",
                "coldfront/core/test_helpers/test_data/test_fixtures/project_choices.json",
                ]

    def setUp(self):
        """create an AllocationDetailView to test
        """
        user = get_user_model().objects.get(username="gvanrossum")
        self.c = Client()
        self.c.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    def test_allocation_detail_template_value_render(self):
        """Confirm that quota_tb and usage_tb are correctly rendered in the generated
        AllocationDetailView
        """
        response = self.c.get('/allocation/1/')
        self.assertEqual(response.status_code, 200)
        # check that allocation_quota_tb has value
        self.assertEqual(response.context['allocation_quota_bytes'], 109951162777600)
        # check that allocation_usage_tb has value
        self.assertEqual(response.context['allocation_usage_bytes'], 10995116277760)
