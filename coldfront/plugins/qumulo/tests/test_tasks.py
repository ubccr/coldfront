from django.test import TestCase, Client

from unittest.mock import patch, MagicMock

from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
    enumerate_directory_contents,
)
from coldfront.plugins.qumulo.tasks import (
    poll_ad_group,
    poll_ad_groups,
    conditionally_update_storage_allocation_status,
    conditionally_update_storage_allocation_statuses,
    ResetAcl,
)
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations

from coldfront.core.allocation.models import Allocation, AllocationStatusChoice
from coldfront.core.resource.models import Resource

from qumulo.lib.request import RequestError

import datetime
from django.utils import timezone


@patch("coldfront.plugins.qumulo.tasks.QumuloAPI")
class TestPollAdGroup(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        return super().setUp()

    def test_poll_ad_group_set_status_to_active_on_success(
        self, qumulo_api_mock: MagicMock
    ) -> None:

        acl_allocation: Allocation = Allocation.objects.create(
            project=self.project,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get_or_create(name="Pending")[0],
        )

        poll_ad_group(acl_allocation=acl_allocation)

        self.assertEqual(acl_allocation.status.name, "Active")

    def test_poll_ad_group_set_status_does_nothing_on_failure(
        self, qumulo_api_mock: MagicMock
    ) -> None:
        acl_allocation: Allocation = Allocation.objects.create(
            project=self.project,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get_or_create(name="Pending")[0],
        )

        get_ad_object_mock: MagicMock = (
            qumulo_api_mock.return_value.rc.ad.distinguished_name_to_ad_account
        )
        get_ad_object_mock.side_effect = [
            RequestError(status_code=404, status_message="Not found"),
        ]

        poll_ad_group(acl_allocation=acl_allocation)

        self.assertEqual(acl_allocation.status.name, "Pending")

    def test_poll_ad_group_set_status_to_denied_on_expiration(
        self, qumulo_api_mock: MagicMock
    ) -> None:
        acl_allocation: Allocation = Allocation.objects.create(
            project=self.project,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get_or_create(name="Pending")[0],
            created=timezone.now() - datetime.timedelta(hours=2),
        )

        get_ad_object_mock: MagicMock = (
            qumulo_api_mock.return_value.rc.ad.distinguished_name_to_ad_account
        )
        get_ad_object_mock.side_effect = [
            RequestError(status_code=404, status_message="Not found"),
        ]

        poll_ad_group(
            acl_allocation=acl_allocation,
            expiration_seconds=60 * 60,
        )

        self.assertEqual(acl_allocation.status.name, "Expired")


@patch("coldfront.plugins.qumulo.tasks.QumuloAPI")
class TestPollAdGroups(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]

        return super().setUp()

    def test_poll_ad_groups_runs_poll_ad_group_for_each_pending_allocation(
        self, qumulo_api_mock: MagicMock
    ) -> None:
        acl_allocation_a: Allocation = Allocation.objects.create(
            project=self.project,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get_or_create(name="Pending")[0],
        )
        resource_a = Resource.objects.get(name="rw")
        acl_allocation_a.resources.add(resource_a)

        acl_allocation_b: Allocation = Allocation.objects.create(
            project=self.project,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get_or_create(name="Pending")[0],
        )
        resource_b = Resource.objects.get(name="ro")
        acl_allocation_b.resources.add(resource_b)

        acl_allocation_c: Allocation = Allocation.objects.create(
            project=self.project,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get_or_create(name="New")[0],
        )
        acl_allocation_c.resources.add(resource_b)

        with patch("coldfront.plugins.qumulo.tasks.poll_ad_group") as poll_ad_group_mock:
            poll_ad_groups()

            self.assertEqual(poll_ad_group_mock.call_count, 2)


class TestUpdateStorageAllocationPendingStatus(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]
        self.form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "general",
        }

        return super().setUp()

    def test_conditionally_update_storage_allocation_status_sets_status_to_new_on_success(
        self,
    ) -> None:
        allocation = create_allocation(
            project=self.project, user=self.user, form_data=self.form_data
        )

        conditionally_update_storage_allocation_status(allocation)

        got_allocation = Allocation.objects.get(pk=allocation.pk)

        self.assertEqual(got_allocation.status.name, "New")

    def test_conditionally_update_storage_allocation_status_does_nothing_when_acls_are_pending(
        self,
    ) -> None:
        allocation = create_allocation(
            project=self.project, user=self.user, form_data=self.form_data
        )
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="ro"
        )

        acl_allocation.status = AllocationStatusChoice.objects.get(name="Pending")
        acl_allocation.save()

        conditionally_update_storage_allocation_status(allocation)

        got_allocation = Allocation.objects.get(pk=allocation.pk)

        self.assertEqual(got_allocation.status.name, "Pending")


class TestStorageAllocationStatuses(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        build_data = build_models()

        self.project = build_data["project"]
        self.user = build_data["user"]
        self.form_data = {
            "storage_filesystem_path": "foo",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "general",
        }

        return super().setUp()

    def test_conditionally_update_storage_allocation_statuses_checks_all_pending_allocations(
        self,
    ):
        create_allocation(
            project=self.project, user=self.user, form_data=self.form_data
        )
        create_allocation(
            project=self.project, user=self.user, form_data=self.form_data
        )

        non_pending_allocation = create_allocation(
            project=self.project, user=self.user, form_data=self.form_data
        )
        non_pending_allocation.status = AllocationStatusChoice.objects.get(name="New")
        non_pending_allocation.save()

        with patch(
            "coldfront.plugins.qumulo.tasks.conditionally_update_storage_allocation_status"
        ) as conditionally_update_storage_allocation_status_mock:
            conditionally_update_storage_allocation_statuses()

            self.assertEqual(
                conditionally_update_storage_allocation_status_mock.call_count, 2
            )

@patch("coldfront.plugins.qumulo.tasks.QumuloAPI")
class TestResetAcl(TestCase):
    def setUp(self) -> None:
        self.form_data = {
            "storage_filesystem_path": "/storage2/fs1/test_allocation",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "general",
        }
        build_data = build_models()
        self.project = build_data["project"]
        self.user = build_data["user"]
        self.root_allocation = create_allocation(
            project=self.project,
            user=self.user,
            form_data=self.form_data
        )
        self._mockDirectoryExpectedValues()
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def _createSubAllocation(self):
        sub_form_data = {
            "storage_filesystem_path": "/this/path/should/filter",
            "storage_export_path": "bar",
            "storage_ticket": "ITSD-54321",
            "storage_name": "baz",
            "storage_quota": 7,
            "protocols": ["nfs"],
            "rw_users": ["test"],
            "ro_users": ["test1"],
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "general",
        }
        return create_allocation(
            project=self.project,
            user=self.user,
            form_data=sub_form_data,
            parent=self.root_allocation
        )

    def _mockDirectoryExpectedValues(self):
        self.mock_directory_expected_values = {}
        contents = enumerate_directory_contents('/fake/path')
        self.mock_directory_expected_values['total_entries'] = len(contents)
        expected_filter_count = 0
        for entry in contents:
            if not entry['path'].startswith('/this/path/should/filter'):
                expected_filter_count += 1
        self.mock_directory_expected_values['filtered_entries_count'] = \
                expected_filter_count

    def test_reset_acl_on_sub_allocation_has_no_exclude_paths(
        self, qumulo_api_mock: MagicMock
    ):
        sub_allocation = self._createSubAllocation()
        reset = ResetAcl(sub_allocation)
        self.assertEqual(0, len(reset.reset_exclude_paths))

    def test_root_sub_allocation_reset_acl_exclude_path(
        self, qumulo_api_mock: MagicMock
    ):
        sub_allocation = self._createSubAllocation()
        reset = ResetAcl(self.root_allocation)
        self.assertEqual(1, len(reset.reset_exclude_paths))
        self.assertEqual(
            sub_allocation.get_attribute('storage_filesystem_path'),
            reset.reset_exclude_paths[0]
        )

    def test_reset_acl_directory_contents_filter(
        self, qumulo_api_mock: MagicMock
    ):
        sub_allocation = self._createSubAllocation()
        reset = ResetAcl(self.root_allocation)
        reset.qumulo_api = MagicMock()
        reset.qumulo_api.rc.fs.enumerate_entire_directory.return_value = \
            enumerate_directory_contents('/pff')
        contents = reset._get_directory_contents('/this/should/get/ignored')
        self.assertEqual(
            self.mock_directory_expected_values['filtered_entries_count'],
            len(contents)
        )
