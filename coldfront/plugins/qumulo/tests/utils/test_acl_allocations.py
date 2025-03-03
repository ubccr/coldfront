from django.test import TestCase, Client
from unittest.mock import MagicMock, patch, call

from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
)
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations
from coldfront.plugins.qumulo.utils.aces_manager import AcesManager

from coldfront.core.allocation.models import (
    Allocation,
    AllocationAttribute,
    AllocationStatusChoice,
)

from deepdiff import DeepDiff

import os
from dotenv import load_dotenv

load_dotenv(override=True)


class TestAclAllocations(TestCase):
    def setUp(self):
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
            "billing_exempt": "No",
            "department_number": "Time Travel Services",
            "billing_cycle": "monthly",
            "service_rate": "general",
        }

        self.client.force_login(self.user)

    def test_set_allocation_attributes_sets_allocation_attributes(self):
        test_allocation = Allocation.objects.create(
            project=self.project,
            justification="",
            quantity=1,
            status=AllocationStatusChoice.objects.get(name="Active"),
        )

        acl_allocations = AclAllocations(project_pk=self.project)
        acl_allocations.set_allocation_attributes(
            allocation=test_allocation, acl_type="ro", wustlkey="test"
        )

        all_allocation_attributes = AllocationAttribute.objects.all()

        self.assertEqual(len(all_allocation_attributes), 1)

    def test_remove_access_sets_only_base_acls(self):
        test_allocation = create_allocation(self.project, self.user, self.form_data)
        acl_allocations = AclAllocations.get_access_allocations(test_allocation)

        calls = []

        mock_acl_data = {
            "control": ["PRESENT"],
            "posix_special_permissions": [],
            "aces": AcesManager.default_aces.copy(),
        }

        for acl_allocation in acl_allocations:
            calls.append(
                call(
                    acl=mock_acl_data,
                    path=test_allocation.get_attribute("storage_filesystem_path"),
                )
            )

        with patch(
            "coldfront.plugins.qumulo.utils.acl_allocations.QumuloAPI"
        ) as mock_qumulo_api:
            mock_return_data = {
                "control": ["PRESENT"],
                "posix_special_permissions": [],
                "aces": AcesManager.default_aces.copy(),
            }

            group_name_base = f"storage-{self.form_data['storage_name']}"
            extra_aces = AcesManager.get_allocation_aces(
                f"{group_name_base}-rw", f"{group_name_base}-ro"
            )
            mock_return_data["aces"].extend(extra_aces)

            mock_qumulo_api.return_value.rc.fs.get_acl_v2.return_value = (
                mock_return_data
            )

            AclAllocations.remove_acl_access(allocation=test_allocation)

            mock_qumulo_api.return_value.rc.fs.set_acl_v2.assert_has_calls(calls)

    def test_remove_access_sets_allocation_status(self):
        test_allocation = create_allocation(self.project, self.user, self.form_data)
        acl_allocations = AclAllocations.get_access_allocations(test_allocation)

        with patch(
            "coldfront.plugins.qumulo.utils.acl_allocations.QumuloAPI"
        ) as mock_qumulo_api:
            mock_return_data = {
                "control": ["PRESENT"],
                "posix_special_permissions": [],
                "aces": AcesManager.default_aces.copy(),
            }

            group_name_base = f"storage-{self.form_data['storage_name']}"
            extra_aces = AcesManager.get_allocation_aces(
                f"{group_name_base}-rw", f"{group_name_base}-ro"
            )
            mock_return_data["aces"].extend(extra_aces)

            mock_qumulo_api.return_value.rc.fs.get_acl_v2.return_value = (
                mock_return_data
            )

            AclAllocations.remove_acl_access(allocation=test_allocation)

            acl_allocations = AclAllocations.get_access_allocations(test_allocation)

            for acl_allocation in acl_allocations:
                self.assertEqual(acl_allocation.status.name, "Revoked")

    def test_set_allocation_acls_sets_base_acl(self):
        mock_qumulo_api = MagicMock()
        mock_set_acl_v2 = MagicMock()
        mock_get_acl_v2 = MagicMock()
        mock_qumulo_api.rc.fs.set_acl_v2 = mock_set_acl_v2
        mock_qumulo_api.rc.fs.get_acl_v2 = mock_get_acl_v2

        form_data = self.form_data.copy()
        form_data["storage_filesystem_path"] = f"{os.environ.get('STORAGE2_PATH')}/foo"

        group_name_base = f"storage-{form_data['storage_name']}"
        expected_aces = AcesManager.default_copy()
        expected_aces.extend(
            AcesManager.get_allocation_aces(
                f"{group_name_base}-rw", f"{group_name_base}-ro"
            )
        )

        allocation = create_allocation(self.project, self.user, form_data)

        mock_get_acl_v2.return_value = AcesManager.get_base_acl()

        with patch(
            "coldfront.plugins.qumulo.utils.acl_allocations.AclAllocations.set_traverse_acl"
        ) as mock_set_traverse_acl:
            AclAllocations.set_allocation_acls(allocation, mock_qumulo_api)

            self.assertEqual(mock_set_acl_v2.call_count, 2)
            call_args = mock_set_acl_v2.call_args

            self.assertEqual(
                call_args.kwargs["path"],
                f"{form_data['storage_filesystem_path']}/Active",
            )

            diff = DeepDiff(
                call_args.kwargs["acl"]["aces"], expected_aces, ignore_order=True
            )
            self.assertFalse(diff)

    def test_set_allocation_acls_preserves_existing_acls(self):
        mock_qumulo_api = MagicMock()
        mock_set_acl_v2 = MagicMock()
        mock_get_acl_v2 = MagicMock()
        mock_qumulo_api.rc.fs.set_acl_v2 = mock_set_acl_v2
        mock_qumulo_api.rc.fs.get_acl_v2 = mock_get_acl_v2

        form_data = self.form_data.copy()
        form_data["storage_filesystem_path"] = f"{os.environ.get('STORAGE2_PATH')}/foo"

        group_name_base = f"storage-{form_data['storage_name']}"

        expected_new_aces = AcesManager.get_allocation_aces(
            f"{group_name_base}-rw", f"{group_name_base}-ro"
        )
        expected_acl = AcesManager.get_base_acl()
        expected_acl["aces"] = expected_new_aces
        expected_acl["aces"].extend(AcesManager.default_aces.copy())

        original_acl = AcesManager.get_base_acl()
        original_acl["aces"] = AcesManager.default_aces.copy()

        mock_get_acl_v2.return_value = original_acl
        allocation = create_allocation(self.project, self.user, form_data)

        with patch(
            "coldfront.plugins.qumulo.utils.acl_allocations.AclAllocations.set_traverse_acl"
        ) as mock_set_traverse_acl:
            AclAllocations.set_allocation_acls(allocation, mock_qumulo_api)

            self.assertEqual(mock_set_acl_v2.call_count, 2)
            call_args = mock_set_acl_v2.call_args

            self.assertEqual(
                call_args.kwargs["path"],
                f"{form_data['storage_filesystem_path']}/Active",
            )

            diff = DeepDiff(call_args.kwargs["acl"], expected_acl, ignore_order=True)
            self.assertFalse(diff)

    def test_set_allocation_acls_call_set_traverse_acl_on_base_path(self):
        mock_qumulo_api = MagicMock()
        mock_set_acl_v2 = MagicMock()
        mock_get_acl_v2 = MagicMock()
        mock_qumulo_api.rc.fs.set_acl_v2 = mock_set_acl_v2
        mock_qumulo_api.rc.fs.get_acl_v2 = mock_get_acl_v2

        form_data = self.form_data.copy()
        form_data["storage_filesystem_path"] = f"{os.environ.get('STORAGE2_PATH')}/foo"

        allocation = create_allocation(self.project, self.user, form_data)

        mock_get_acl_v2.return_value = AcesManager.get_base_acl()

        with patch(
            "coldfront.plugins.qumulo.utils.acl_allocations.AclAllocations.set_traverse_acl"
        ) as mock_set_traverse_acl:
            AclAllocations.set_allocation_acls(allocation, mock_qumulo_api)

            self.assertEqual(mock_set_acl_v2.call_count, 2)

            group_name_base = f"storage-{form_data['storage_name']}"
            mock_set_traverse_acl.assert_called_once_with(
                fs_path=form_data["storage_filesystem_path"],
                rw_groupname=f"{group_name_base}-rw",
                ro_groupname=f"{group_name_base}-ro",
                qumulo_api=mock_qumulo_api,
                is_base_allocation=True,
            )

    def test_set_allocation_acls_sets_sub_acl(self):
        mock_qumulo_api = MagicMock()
        mock_set_acl_v2 = MagicMock()
        mock_get_acl_v2 = MagicMock()
        mock_qumulo_api.rc.fs.set_acl_v2 = mock_set_acl_v2
        mock_qumulo_api.rc.fs.get_acl_v2 = mock_get_acl_v2

        form_data = self.form_data.copy()
        form_data["storage_filesystem_path"] = (
            f"{os.environ.get('STORAGE2_PATH')}/bar/Active/foo"
        )

        group_name_base = f"storage-{form_data['storage_name']}"

        expected_aces = AcesManager.default_copy()
        expected_aces.extend(
            AcesManager.get_allocation_aces(
                f"{group_name_base}-rw", f"{group_name_base}-ro"
            )
        )

        allocation = create_allocation(self.project, self.user, form_data)

        mock_get_acl_v2.return_value = AcesManager.get_base_acl()

        with patch(
            "coldfront.plugins.qumulo.utils.acl_allocations.AclAllocations.set_traverse_acl"
        ) as mock_set_traverse_acl:
            AclAllocations.set_allocation_acls(allocation, mock_qumulo_api)

            mock_set_acl_v2.assert_called_once()
            call_args = mock_set_acl_v2.call_args

            self.assertEqual(
                call_args.kwargs["path"],
                f"{form_data['storage_filesystem_path']}",
            )

            diff = DeepDiff(
                call_args.kwargs["acl"]["aces"], expected_aces, ignore_order=True
            )
            self.assertFalse(diff)

    def test_set_allocation_acls_preserves_existing_sub_acls(self):
        mock_qumulo_api = MagicMock()
        mock_set_acl_v2 = MagicMock()
        mock_get_acl_v2 = MagicMock()
        mock_qumulo_api.rc.fs.set_acl_v2 = mock_set_acl_v2
        mock_qumulo_api.rc.fs.get_acl_v2 = mock_get_acl_v2

        form_data = self.form_data.copy()
        form_data["storage_filesystem_path"] = (
            f"{os.environ.get('STORAGE2_PATH')}/foo/Active/bar"
        )

        group_name_base = f"storage-{form_data['storage_name']}"

        expected_new_aces = AcesManager.get_allocation_aces(
            f"{group_name_base}-rw", f"{group_name_base}-ro"
        )
        expected_acl = AcesManager.get_base_acl()
        expected_acl["aces"] = expected_new_aces

        existing_aces = AcesManager.default_aces.copy()
        existing_aces.extend(AcesManager.get_allocation_aces("test", "test1"))

        expected_acl["aces"].extend(existing_aces.copy())

        original_acl = AcesManager.get_base_acl()
        original_acl["aces"] = existing_aces.copy()

        mock_get_acl_v2.return_value = original_acl
        allocation = create_allocation(self.project, self.user, form_data)

        with patch(
            "coldfront.plugins.qumulo.utils.acl_allocations.AclAllocations.set_traverse_acl"
        ) as mock_set_traverse_acl:
            AclAllocations.set_allocation_acls(allocation, mock_qumulo_api)

            mock_set_acl_v2.assert_called_once()
            call_args = mock_set_acl_v2.call_args

            self.assertEqual(
                call_args.kwargs["path"],
                f"{form_data['storage_filesystem_path']}",
            )

            diff = DeepDiff(call_args.kwargs["acl"], expected_acl, ignore_order=True)
            self.assertFalse(diff)

    def test_set_traverse_acl_adds_traverse_priviledges_to_path(self):
        mock_qumulo_api = MagicMock()
        mock_set_acl_v2 = MagicMock()
        mock_qumulo_api.rc.fs.set_acl_v2 = mock_set_acl_v2

        fs_path = f"{os.environ.get('STORAGE2_PATH')}/foo"
        rw_groupname = "rw_group"
        ro_groupname = "ro_group"

        expected_acl = AcesManager.get_base_acl()
        expected_acl["aces"] = AcesManager.get_traverse_aces(
            rw_groupname, ro_groupname, True
        )

        mock_qumulo_api.rc.fs.get_acl_v2.return_value = AcesManager.get_base_acl()
        AclAllocations.set_traverse_acl(
            fs_path=fs_path,
            rw_groupname=rw_groupname,
            ro_groupname=ro_groupname,
            qumulo_api=mock_qumulo_api,
            is_base_allocation=True,
        )

        mock_set_acl_v2.assert_called_once()

        call_args = mock_set_acl_v2.call_args
        self.assertEqual(call_args.kwargs["path"], fs_path)

        diff = DeepDiff(call_args.kwargs["acl"], expected_acl, ignore_order=True)
        self.assertFalse(diff)

    def test_set_traverse_acl_adds_traverse_privileges_to_path_with_existing_acls(
        self,
    ):
        mock_qumulo_api = MagicMock()
        mock_set_acl_v2 = MagicMock()
        mock_qumulo_api.rc.fs.set_acl_v2 = mock_set_acl_v2

        fs_path = f"{os.environ.get('STORAGE2_PATH')}/foo"
        rw_groupname = "rw_group"
        ro_groupname = "ro_group"

        expected_acl = AcesManager.get_base_acl()
        expected_acl["aces"] = AcesManager.get_traverse_aces(
            rw_groupname, ro_groupname, True
        )
        expected_acl["aces"].extend(AcesManager.default_aces.copy())

        original_acl = AcesManager.get_base_acl()
        original_acl["aces"] = AcesManager.default_aces.copy()

        mock_qumulo_api.rc.fs.get_acl_v2.return_value = original_acl

        AclAllocations.set_traverse_acl(
            fs_path=fs_path,
            rw_groupname=rw_groupname,
            ro_groupname=ro_groupname,
            qumulo_api=mock_qumulo_api,
            is_base_allocation=True,
        )

        mock_set_acl_v2.assert_called_once()

        call_args = mock_set_acl_v2.call_args
        self.assertEqual(call_args.kwargs["path"], fs_path)

        diff = DeepDiff(call_args.kwargs["acl"], expected_acl, ignore_order=True)
        self.assertFalse(diff)

    def test_set_traverse_aces_sets_parent_directories_for_sub_allocation(self):
        mock_qumulo_api = MagicMock()
        mock_set_acl_v2 = MagicMock()
        mock_qumulo_api.rc.fs.set_acl_v2 = mock_set_acl_v2

        fs_path = f"{os.environ.get('STORAGE2_PATH')}/foo/Active/bar"
        rw_groupname = "rw_group"
        ro_groupname = "ro_group"

        expected_acl = AcesManager.get_base_acl()
        expected_acl["aces"] = AcesManager.get_traverse_aces(
            rw_groupname, ro_groupname, is_base_allocation=False
        )

        mock_qumulo_api.rc.fs.get_acl_v2.return_value = AcesManager.get_base_acl()
        AclAllocations.set_traverse_acl(
            fs_path=fs_path,
            rw_groupname=rw_groupname,
            ro_groupname=ro_groupname,
            qumulo_api=mock_qumulo_api,
            is_base_allocation=False,
        )

        mock_set_acl_v2.assert_called()

        call_args_list = mock_set_acl_v2.call_args_list
        self.assertEqual(len(call_args_list), 2)

        self.assertEqual(
            call_args_list[0].kwargs["path"],
            f"{os.environ.get('STORAGE2_PATH')}/foo/Active",
        )
        diff = DeepDiff(
            call_args_list[0].kwargs["acl"], expected_acl, ignore_order=True
        )

        self.assertEqual(
            call_args_list[1].kwargs["path"], f"{os.environ.get('STORAGE2_PATH')}/foo"
        )
        diff = DeepDiff(
            call_args_list[1].kwargs["acl"], expected_acl, ignore_order=True
        )
        self.assertFalse(diff)

    def test_is_base_allocation_confirms_base_allocation(self):
        path = f"/{os.environ.get('STORAGE2_PATH').strip('/')}/foo"
        self.assertTrue(AclAllocations.is_base_allocation(path), path)

        path = f"/{os.environ.get('STORAGE2_PATH').strip('/')}/foo/"
        self.assertTrue(AclAllocations.is_base_allocation(path), path)

    def test_is_base_allocation_rejects_sub_allocation(self):
        path = f"/{os.environ.get('STORAGE2_PATH').strip('/')}/foo/Active/bar"
        self.assertFalse(AclAllocations.is_base_allocation(path), path)

    def test_is_base_allocation_rejects_gibberish_allocations(self):
        path = f"/{os.environ.get('STORAGE2_PATH').strip('/')}/foo/Active"
        self.assertFalse(AclAllocations.is_base_allocation(path), path)

        path = "/foo"
        self.assertFalse(AclAllocations.is_base_allocation(path), path)

        path = f"/{os.environ.get('STORAGE2_PATH').strip('/')}/foo/bar/Active"
        self.assertFalse(AclAllocations.is_base_allocation(path), path)

        path = f"{os.environ.get('STORAGE2_PATH').strip('/')}/foo"
        self.assertFalse(AclAllocations.is_base_allocation(path), path)
