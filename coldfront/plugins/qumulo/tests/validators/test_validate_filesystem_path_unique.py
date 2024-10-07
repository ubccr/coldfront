import os

from django.test import TestCase
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from coldfront.core.allocation.models import AllocationStatusChoice

from coldfront.plugins.qumulo.tests.helper_classes.filesystem_path import (
    ValidFormPathMock,
)
from coldfront.plugins.qumulo.validators import validate_filesystem_path_unique
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    build_user_plus_project,
    create_allocation,
)

TEST_STORAGE2_PATH = "/storage2-dev/fs1"
existing_path_mocked_response = {
    "path": f"{TEST_STORAGE2_PATH}/bobs_your_uncle/",
    "name": "bobs_your_uncle",
    "num_links": 2,
    "type": "FS_FILE_TYPE_DIRECTORY",
    "major_minor_numbers": {"major": 0, "minor": 0},
    "symlink_target_type": "FS_FILE_TYPE_UNKNOWN",
    "file_number": "2010014",
    "id": "2010014",
    "mode": "0777",
    "owner": "500",
    "owner_details": {"id_type": "LOCAL_USER", "id_value": "admin"},
    "group": "513",
    "group_details": {"id_type": "LOCAL_GROUP", "id_value": "Users"},
    "blocks": "1",
    "datablocks": "0",
    "metablocks": "1",
    "size": "0",
    "access_time": "2024-05-17T13:23:40.283585722Z",
    "modification_time": "2024-05-17T13:23:40.283585722Z",
    "change_time": "2024-05-17T16:42:13.383433668Z",
    "creation_time": "2024-05-17T13:23:40.283585722Z",
    "child_count": 0,
    "extended_attributes": {
        "read_only": False,
        "hidden": False,
        "system": False,
        "archive": False,
        "temporary": False,
        "compressed": False,
        "not_content_indexed": False,
        "sparse_file": False,
        "offline": False,
    },
    "directory_entry_hash_policy": "FS_DIRECTORY_HASH_VERSION_FOLDED",
    "data_revision": None,
    "user_metadata_revision": "0",
}


class TestValidateFilesystemPathUnique(TestCase):
    def setUp(self):
        build_models()
        self.patcher = patch("coldfront.plugins.qumulo.validators.QumuloAPI")
        self.mock_qumulo_api = self.patcher.start()
        self.mock_get_file_attr = None
        os.environ["STORAGE2_PATH"] = TEST_STORAGE2_PATH

        return super().setUp()

    def tearDown(self):
        self.patcher.stop()
        return super().tearDown()

    def test_existing_path_raises_validation_error_on_qumulo_conflict(self):
        self.mock_qumulo_api.return_value.rc.fs.get_file_attr = MagicMock(
            return_value=existing_path_mocked_response
        )
        with self.assertRaises(ValidationError):
            validate_filesystem_path_unique("/new/existing/file/path")

    def test_unique_path_passes_validation(self):
        self.mock_qumulo_api.return_value.rc.fs.get_file_attr = ValidFormPathMock()
        try:
            validate_filesystem_path_unique("/new/nonexistent/file/path")
        except ValidationError:
            self.fail()

    def test_raises_error_on_coldfront_conflict(self):
        self.mock_qumulo_api.return_value.rc.fs.get_file_attr = ValidFormPathMock()

        user_project_data = build_user_plus_project("foo", "bar")

        relative_path = "foo/"

        form_data = {
            "storage_filesystem_path": f"{TEST_STORAGE2_PATH}/{relative_path}",
            "storage_export_path": "foo",
            "storage_name": "for_tester_foo",
            "storage_quota": 10,
            "protocols": ["nfs"],
            "rw_users": [user_project_data["user"].username],
            "ro_users": [],
            "storage_ticket": "ITSD-54321",
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "general",
        }
        create_allocation(
            user_project_data["project"], user_project_data["user"], form_data
        )

        with self.assertRaises(ValidationError):
            validate_filesystem_path_unique(relative_path)

    def test_only_raises_coldfront_error_for_select_statuses(self):
        self.mock_qumulo_api.return_value.rc.fs.get_file_attr = ValidFormPathMock()

        user_project_data = build_user_plus_project("foo", "bar")

        relative_path = "foo/"

        form_data = {
            "storage_filesystem_path": f"{TEST_STORAGE2_PATH}/{relative_path}",
            "storage_export_path": "foo",
            "storage_name": "for_tester_foo",
            "storage_quota": 10,
            "protocols": ["nfs"],
            "rw_users": [user_project_data["user"].username],
            "ro_users": [],
            "storage_ticket": "ITSD-54321",
            "cost_center": "Uncle Pennybags",
            "department_number": "Time Travel Services",
            "service_rate": "general",
        }

        existing_allocation = create_allocation(
            user_project_data["project"], user_project_data["user"], form_data
        )

        reserved_status_names = ["Active", "Pending", "New"]
        reserved_statuses = AllocationStatusChoice.objects.filter(
            name__in=reserved_status_names
        )
        for status in reserved_statuses:
            existing_allocation.status = status
            existing_allocation.save()

            with self.assertRaises(ValidationError):
                validate_filesystem_path_unique(relative_path)

        other_statuses = AllocationStatusChoice.objects.exclude(
            name__in=reserved_status_names
        )
        for status in other_statuses:
            existing_allocation.status = status
            existing_allocation.save()

            try:
                validate_filesystem_path_unique(relative_path)
            except ValidationError:
                self.fail()
