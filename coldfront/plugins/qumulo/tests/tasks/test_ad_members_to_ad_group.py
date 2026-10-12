from django.test import TestCase, Client
from django.contrib.auth.models import User, Group

from unittest.mock import patch, MagicMock, ANY

from coldfront.plugins.qumulo.services.allocation_service import AllocationService
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    mock_qumulo_info,
    default_form_data,
)
from coldfront.plugins.qumulo.tasks import (
    add_allocation_group_to_parent_ad_group,
    addMembersToADGroup,
)
from coldfront.plugins.qumulo.utils.acl_allocations import AclAllocations

from coldfront.core.allocation.models import (
    AllocationUser,
)
from coldfront.core.project.models import Project

from django.test import RequestFactory

from ldap3.core.exceptions import LDAPInvalidDnError

import datetime
from copy import deepcopy
import json


@patch("coldfront.plugins.qumulo.services.allocation_service.async_task")
@patch("coldfront.plugins.qumulo.services.allocation_service.ActiveDirectoryAPI")
@patch("coldfront.plugins.qumulo.tasks.ActiveDirectoryAPI")
class TestAddMembersToADGroup(TestCase):
    def setUp(self) -> None:
        patch.dict(
            "os.environ",
            {
                "QUMULO_INFO": json.dumps(mock_qumulo_info),
            },
        ).start()

        self.client = Client()

        build_data = build_models()

        self.project: Project = build_data["project"]
        self.user: User = build_data["user"]

        self.form_data = default_form_data.copy()
        self.form_data["project_pk"] = self.project.id

        self.client.force_login(self.user)

        self.create_allocation = AllocationService.create_new_allocation

        self.request = RequestFactory().post("/")
        self.request.user = self.user

        return super().setUp()

    def tearDown(self):
        patch.stopall()

        return super().tearDown()

    def test_checks_single_user(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        active_directory_instance = MagicMock()
        mock_active_directory_api.return_value = active_directory_instance

        wustlkeys = ["foo"]
        self.form_data["rw_users"] = wustlkeys

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )

        addMembersToADGroup(wustlkeys, acl_allocation, datetime.datetime.now())

        active_directory_instance.get_members.assert_called_once_with(wustlkeys)

    def test_allocation_creation_schedules_groups_under_storage_parent(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        result = self.create_allocation(user=self.user, form_data=self.form_data)
        parent_group_name = "storage2"

        for access_allocation in result["access_allocations"]:
            allocation_group_name = access_allocation.get_attribute(
                "storage_acl_name"
            )
            self.assertIn(
                (
                    add_allocation_group_to_parent_ad_group,
                    allocation_group_name,
                    parent_group_name,
                ),
                [call.args[:3] for call in mock_allocation_view_async_task.call_args_list],
            )

        self.assertEqual(mock_allocation_view_AD.return_value.create_ad_group.call_count, 2)

    def test_allocation_creation_uses_filesystem_path_parent_group(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        form_data = self.form_data.copy()
        form_data["storage_filesystem_path"] = "/storage2-dev/fs1/allocation-name"
        result = self.create_allocation(user=self.user, form_data=form_data)

        scheduled_calls = [
            call.args[:3]
            for call in mock_allocation_view_async_task.call_args_list
            if call.args and call.args[0] == add_allocation_group_to_parent_ad_group
        ]
        self.assertEqual(
            scheduled_calls,
            [
                (
                    add_allocation_group_to_parent_ad_group,
                    result["access_allocations"][0].get_attribute("storage_acl_name"),
                    "storage2-dev",
                ),
                (
                    add_allocation_group_to_parent_ad_group,
                    result["access_allocations"][1].get_attribute("storage_acl_name"),
                    "storage2-dev",
                ),
            ],
        )

    def test_allocation_group_is_added_to_parent_group(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        active_directory_instance = MagicMock()
        active_directory_instance.get_group_dn.return_value = "allocation_group_dn"
        mock_active_directory_api.return_value = active_directory_instance

        add_allocation_group_to_parent_ad_group("storage2-baz-rw", "storage2")

        active_directory_instance.get_group_dn.assert_called_once_with(
            "storage2-baz-rw"
        )
        active_directory_instance.add_members_to_ad_group.assert_called_once_with(
            ["allocation_group_dn"], "storage2"
        )
        active_directory_instance.create_ad_group.assert_not_called()

    def test_appends_bad_user_list_on_invalid_user(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        active_directory_instance = MagicMock()
        active_directory_instance.get_members.return_value = []
        mock_active_directory_api.return_value = active_directory_instance

        wustlkeys = ["foo", "bar"]
        self.form_data["rw_users"] = wustlkeys

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )

        datetime_now = datetime.datetime.now()

        with patch(
            "coldfront.plugins.qumulo.tasks.__add_members_and_handle_errors"
        ) as mock_add_members_and_handle_errors:
            addMembersToADGroup(wustlkeys, acl_allocation, datetime_now, self.request.user.id)

            mock_add_members_and_handle_errors.assert_called_once_with(
                wustlkeys,
                acl_allocation,
                datetime_now,
                [],
                ["foo", "bar"],
                self.request.user.id,
            )

    def test_appends_good_user_list_on_valid_user(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        mock_user_response = [
            {
                "dn": "user_dn",
                "attributes": {
                    "objectClass": ["top", "person", "organizationalPerson", "user"],
                    "sAMAccountName": "foo",
                },
            }
        ]
        active_directory_instance = MagicMock()
        active_directory_instance.get_members.return_value = mock_user_response
        mock_active_directory_api.return_value = active_directory_instance

        wustlkeys = ["foo", "bar"]
        self.form_data["rw_users"] = wustlkeys

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )

        datetime_now = datetime.datetime.now()

        with patch(
            "coldfront.plugins.qumulo.tasks.__add_members_and_handle_errors"
        ) as mock_add_members_and_handle_errors:
            addMembersToADGroup(wustlkeys, acl_allocation, datetime_now, self.request.user.id)

            mock_add_members_and_handle_errors.assert_called_once_with(
                ["foo", "bar"],
                acl_allocation,
                datetime_now,
                [
                    {
                        "wustlkey": wustlkeys[0],
                        "dn": mock_user_response[0]["dn"],
                        "is_group": False,
                    }
                ],
                ["bar"],
                self.request.user.id,
            )

    def test_appends_good_group_with_is_group(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        mock_user_response = [
            {
                "dn": "user_dn",
                "attributes": {
                    "objectClass": ["top", "group"],
                    "sAMAccountName": "foo",
                },
            },
        ]
        active_directory_instance = MagicMock()
        active_directory_instance.get_members.return_value = mock_user_response
        mock_active_directory_api.return_value = active_directory_instance

        wustlkeys = ["foo"]
        self.form_data["rw_users"] = wustlkeys

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )

        datetime_now = datetime.datetime.now()

        with patch(
            "coldfront.plugins.qumulo.tasks.__add_members_and_handle_errors"
        ) as mock_add_members_and_handle_errors:
            addMembersToADGroup(wustlkeys, acl_allocation, datetime_now, self.request.user.id)

            mock_add_members_and_handle_errors.assert_called_once_with(
                wustlkeys,
                acl_allocation,
                datetime_now,
                [
                    {
                        "wustlkey": wustlkeys[0],
                        "dn": mock_user_response[0]["dn"],
                        "is_group": True,
                    }
                ],
                [],
                self.request.user.id,
            ),

    @patch("coldfront.plugins.qumulo.tasks.send_email_template")
    def test_sends_notifications_on_bad_users(
        self,
        mock_send_email_template: MagicMock,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        wustlkeys = ["foo", "bar"]
        self.form_data["rw_users"] = wustlkeys

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )

        mock_active_directory_api.return_value.get_members.return_value = []
        addMembersToADGroup(wustlkeys, acl_allocation, datetime.datetime.now(), self.request.user.id)

        mock_send_email_template.assert_called_once()

    def __get_members_mock(self, wustlkeys: str, good_keys: list[str]) -> list[dict]:
        mock_member_response = {
            "dn": "user_dn",
            "attributes": {
                "objectClass": ["top", "person", "organizationalPerson", "user"]
            },
        }

        return_list = []

        for key in good_keys:
            member = deepcopy(mock_member_response)
            member["attributes"]["sAMAccountName"] = key
            return_list.append(member)

        return return_list

    def test_does_not_add_bad_users_to_group(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        active_directory_instance = MagicMock()
        active_directory_instance.get_user.side_effect = ValueError("Invalid wustlkey")
        mock_active_directory_api.return_value = active_directory_instance

        wustlkeys = ["foo"]
        self.form_data["rw_users"] = wustlkeys

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )

        addMembersToADGroup(wustlkeys, acl_allocation, datetime.datetime.now(), self.request.user.id)

        active_directory_instance.add_members_to_ad_group.assert_not_called()

    def test_ads_good_users_to_allocation(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_service_AD: MagicMock,
        mock_allocation_service_async_task: MagicMock,
    ):

        wustlkeys = ["foo", "bar", "baz", "bah"]
        good_keys = wustlkeys[0:2]

        active_directory_instance = MagicMock()
        active_directory_instance.get_members.side_effect = (
            lambda wustlkeys: self.__get_members_mock(wustlkeys, good_keys)
        )
        mock_active_directory_api.return_value = active_directory_instance

        form_data = self.form_data
        form_data["rw_users"] = wustlkeys

        base_allocation = self.create_allocation(user=self.user, form_data=form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=base_allocation, resource_name="rw"
        )

        addMembersToADGroup(wustlkeys, acl_allocation, datetime.datetime.now(), self.request.user.id)
        allocation_users = list(
            map(
                lambda allocation_user: allocation_user.user.username,
                AllocationUser.objects.filter(allocation=acl_allocation),
            )
        )
        self.assertListEqual(allocation_users, good_keys)

    def test_ads_good_group_user_with_group_flag(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):

        wustlkeys = ["foo"]
        good_keys = wustlkeys[0:1]

        active_directory_instance = MagicMock()
        mock_member_response = [
            {
                "dn": "user_dn",
                "attributes": {
                    "objectClass": ["top", "group"],
                    "sAMAccountName": "foo",
                },
            }
        ]
        active_directory_instance.get_members.return_value = mock_member_response
        mock_active_directory_api.return_value = active_directory_instance

        form_data = self.form_data
        form_data["rw_users"] = wustlkeys

        base_allocation = self.create_allocation(user=self.user, form_data=form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=base_allocation, resource_name="rw"
        )

        addMembersToADGroup(wustlkeys, acl_allocation, datetime.datetime.now(), self.request.user.id)
        allocation_users = list(
            map(
                lambda allocation_user: allocation_user.user.username,
                AllocationUser.objects.filter(allocation=acl_allocation),
            )
        )
        self.assertListEqual(allocation_users, good_keys)

        is_group = list(
            map(
                lambda allocation_user: allocation_user.user.userprofile.is_group,
                AllocationUser.objects.filter(allocation=acl_allocation),
            )
        )

        self.assertListEqual(is_group, [True])

    def test_adds_users_to_group_when_done(
        self,
        mock_active_directory_api: MagicMock,
        mock_allocation_service_AD: MagicMock,
        mock_allocation_service_async_task: MagicMock,
    ):
        active_directory_instance = MagicMock()
        mock_active_directory_api.return_value = active_directory_instance

        wustlkeys = ["foo"]
        self.form_data["rw_users"] = wustlkeys

        active_directory_instance.get_members.return_value = [
            {
                "dn": "user_dn",
                "attributes": {
                    "objectClass": ["top", "person", "organizationalPerson", "user"],
                    "sAMAccountName": "foo",
                },
            }
        ]

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )
        group_name = acl_allocation.get_attribute("storage_acl_name")

        addMembersToADGroup(
            wustlkeys,
            acl_allocation,
            datetime.datetime.now(),
            self.request.user.id,
        )

        active_directory_instance.add_members_to_ad_group.assert_called_once_with(
            ["user_dn"], group_name
        )

    @patch("coldfront.plugins.qumulo.tasks.send_email_template")
    def test_sends_email_failed_user_add(
        self,
        mock_send_email_template: MagicMock,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        active_directory_instance = MagicMock()
        active_directory_instance.add_members_to_ad_group.side_effect = (
            LDAPInvalidDnError("foo")
        )
        mock_active_directory_api.return_value = active_directory_instance

        wustlkeys = ["foo", "bar"]
        self.form_data["rw_users"] = wustlkeys

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )

        ris_group = Group.objects.get_or_create(name="RIS_UserSupport")
        self.user.groups.add(ris_group[0].id)
        self.user.save()

        active_directory_instance.get_members.return_value = list(
            map(
                lambda wustlkey: {
                    "dn": "foo",
                    "attributes": {"objectClass": [], "sAMAccountName": wustlkey},
                },
                wustlkeys,
            )
        )
        addMembersToADGroup(
            wustlkeys,
            acl_allocation,
            datetime.datetime.now(),
            self.request.user.id,
        )

        mock_send_email_template.assert_called_once_with(
            subject="Error adding users to Storage Allocation",
            template_name="email/error_adding_users.txt",
            template_context=ANY,
            sender=ANY,
            receiver_list=[self.user.email],
        )

    @patch("coldfront.plugins.qumulo.tasks.send_email_template")
    def test_sends_email_to_user_support(
        self,
        mock_send_email_template: MagicMock,
        mock_active_directory_api: MagicMock,
        mock_allocation_view_AD: MagicMock,
        mock_allocation_view_async_task: MagicMock,
    ):
        wustlkeys = ["foo", "bar"]
        self.form_data["rw_users"] = wustlkeys

        allocation = self.create_allocation(user=self.user, form_data=self.form_data)[
            "allocation"
        ]
        acl_allocation = AclAllocations.get_access_allocation(
            storage_allocation=allocation, resource_name="rw"
        )

        ris_group = Group.objects.get_or_create(name="RIS_UserSupport")
        self.user.groups.add(ris_group[0].id)
        self.user.save()

        mock_active_directory_api.return_value.get_members.return_value = []
        addMembersToADGroup(wustlkeys, acl_allocation, datetime.datetime.now(), self.request.user.id)

        mock_send_email_template.assert_called_once_with(
            subject="Users not found in Storage Allocation",
            template_name="email/invalid_users.txt",
            template_context=ANY,
            sender=ANY,
            receiver_list=[self.user.email],
        )
