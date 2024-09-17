from django.test import TestCase
from unittest.mock import patch, call, MagicMock
from coldfront.plugins.qumulo.utils.active_directory_api import ActiveDirectoryAPI
from ldap3 import MODIFY_DELETE

import os
from dotenv import load_dotenv

load_dotenv(override=True)


class TestActiveDirectoryAPI(TestCase):
    @patch("coldfront.plugins.qumulo.utils.active_directory_api.Connection")
    def setUp(self, mock_connection):
        self.mock_connection = mock_connection.return_value
        self.ad_api = ActiveDirectoryAPI()
        self.mock_connection.response = []

    def test_get_user_returns_user(self):
        self.mock_connection.response = [
            {"dn": "user_dn", "attributes": {"other_attr": "value"}}
        ]
        wustlkey = "test_wustlkey"
        expected_filter = f"(&(objectclass=person)(sAMAccountName={wustlkey}))"

        self.ad_api.get_user(wustlkey)

        self.mock_connection.search.assert_called_once_with(
            "dc=accounts,dc=ad,dc=wustl,dc=edu",
            expected_filter,
            attributes=["sAMAccountName", "mail", "givenName", "sn"],
        )

    def test_get_user_by_email_returns_user(self):

        self.mock_connection.response = [
            {"dn": "user_dn", "attributes": {"other_attr": "value"}}
        ]
        email = "wustlkey@wustl.edu"
        expected_filter = f"(&(objectclass=person)(mail={email}))"

        self.ad_api.get_user_by_email(email)

        self.mock_connection.search.assert_called_once_with(
            "dc=accounts,dc=ad,dc=wustl,dc=edu",
            expected_filter,
            attributes=["sAMAccountName", "mail", "givenName", "sn"],
        )

    def test_get_user_returns_value_error_on_empty_result(self):
        with self.assertRaises(ValueError) as context:
            self.ad_api.get_user(wustlkey=None)

        exception = context.exception
        self.assertEqual(str(exception), ("wustlkey must be defined"))

    def test_get_user_returns_value_error_on_invalid_wustlkey(self):
        with patch(
            "coldfront.plugins.qumulo.utils.active_directory_api.Connection.search",
            return_value=[],
        ):
            with self.assertRaises(ValueError) as context:
                self.ad_api.get_user(wustlkey="test")

            exception = context.exception
            self.assertEqual(str(exception), ("Invalid wustlkey"))

    def test_create_ad_group_creates_group(self):
        group_name = "test_group_name"
        expected_groups_ou = os.environ.get("AD_GROUPS_OU")
        expected_new_group_dn = f"cn={group_name},{expected_groups_ou}"

        self.ad_api.create_ad_group(group_name)

        self.mock_connection.add.assert_called_once_with(
            expected_new_group_dn, "group", attributes={"sAMAccountName": group_name}
        )

    @patch(
        "coldfront.plugins.qumulo.utils.active_directory_api.ActiveDirectoryAPI.get_group_dn"
    )
    @patch(
        "coldfront.plugins.qumulo.utils.active_directory_api.ActiveDirectoryAPI.get_user"
    )
    @patch(
        "coldfront.plugins.qumulo.utils.active_directory_api.ad_add_members_to_groups"
    )
    def test_add_user_to_ad_group_adds_wustlkey_to_group(
        self, mock_ad_add_members_to_groups, mock_get_user, mock_get_group_dn
    ):
        wustlkey = "test_wustlkey"
        user = mock_get_user.return_value
        user_dn = user["dn"]

        group_name = "test_group_name"
        expected_groups_ou = "OU=QA,OU=RIS,OU=Groups,DC=accounts,DC=ad,DC=wustl,DC=edu"
        expected_group_dn = f"cn={group_name},{expected_groups_ou}"
        mock_get_group_dn.return_value = expected_group_dn

        self.ad_api.add_user_to_ad_group(wustlkey, group_name)

        mock_get_user.assert_called_once_with(wustlkey)
        mock_ad_add_members_to_groups.assert_called_once_with(
            self.mock_connection, user_dn, expected_group_dn
        )

    def test_get_group_dn_searches_for_group_dn(self):
        groups_OU = os.environ.get("AD_GROUPS_OU")

        group_name = "some_group_name"

        self.mock_connection.response = [
            {"dn": "group_dn", "attributes": {"other_attr": "value"}}
        ]

        expected_filter = f"(&(objectclass=group)(sAMAccountName={group_name}))"

        self.ad_api.get_group_dn(group_name)

        self.mock_connection.search.assert_called_once_with(groups_OU, expected_filter)

    def test_get_group_dn_returns_value_error_on_empty_result(self):
        group_name = "some_group_name"

        self.mock_connection.response = []

        with self.assertRaises(ValueError) as context:
            self.ad_api.get_group_dn(group_name)

        exception = context.exception
        self.assertEqual(str(exception), ("Invalid group_name"))

    def test_get_group_dn_returns_group_dn(self):
        group_name = "some_group_name"
        group_dn = "some_group_dn"

        self.mock_connection.response = [
            {"dn": group_dn, "attributes": {"other_attr": "value"}}
        ]

        return_group_dn = self.ad_api.get_group_dn(group_name)

        self.assertEqual(return_group_dn, group_dn)

    def test_delete_ad_group_gets_group_dn(self):
        groups_OU = os.environ.get("AD_GROUPS_OU")
        group_name = "some_group_name"

        self.mock_connection.response = [
            {"dn": "group_dn", "attributes": {"other_attr": "value"}}
        ]

        expected_filter = f"(&(objectclass=group)(sAMAccountName={group_name}))"

        self.ad_api.delete_ad_group(group_name)

        self.mock_connection.search.assert_called_once_with(groups_OU, expected_filter)

    def test_delete_ad_group_calls_delete(self):
        group_name = "some_group_name"
        group_dn = "some_group_dn"

        self.mock_connection.response = [
            {"dn": group_dn, "attributes": {"other_attr": "value"}}
        ]

        self.ad_api.delete_ad_group(group_name)

        self.mock_connection.delete.assert_called_once_with(group_dn)

    def test_remove_user_from_group_gets_user_dn(self):
        self.mock_connection.response = [
            {"dn": "user_dn", "attributes": {"other_attr": "value"}}
        ]

        user_name = "test_wustlkey"
        expected_filter = f"(&(objectclass=person)(sAMAccountName={user_name}))"

        self.ad_api.remove_user_from_group(user_name=user_name, group_name="bar")

        self.mock_connection.search.assert_has_calls(
            [
                call(
                    "dc=accounts,dc=ad,dc=wustl,dc=edu",
                    expected_filter,
                    attributes=["sAMAccountName", "mail", "givenName", "sn"],
                )
            ]
        )

    def test_remove_user_from_group_gets_group_dn(self):
        groups_OU = os.environ.get("AD_GROUPS_OU")
        group_name = "some_group_name"

        self.mock_connection.response = [
            {"dn": "group_dn", "attributes": {"other_attr": "value"}}
        ]

        expected_filter = f"(&(objectclass=group)(sAMAccountName={group_name}))"

        self.ad_api.remove_user_from_group("user_name", group_name)

        self.mock_connection.search.assert_has_calls([call(groups_OU, expected_filter)])

    @patch("coldfront.plugins.qumulo.utils.active_directory_api.Connection")
    def test_remove_user_from_group_calls_modify(self, mock_connection):
        group_name = "some_group_name"
        user_name = "some_user_name"
        user_dn = "user_dn_foo"
        group_dn = "group_dn_bar"

        with patch.object(
            ActiveDirectoryAPI,
            "get_user",
            MagicMock(),
        ) as mock_get_user:
            with patch.object(
                ActiveDirectoryAPI,
                "get_group_dn",
                MagicMock(),
            ) as mock_get_group_dn:
                mock_get_user.return_value = {
                    "dn": user_dn,
                    "attributes": {"other_attr": "value"},
                }

                mock_get_group_dn.return_value = group_dn

                self.mock_connection = mock_connection.return_value
                ad_api = ActiveDirectoryAPI()
                self.mock_connection.response = []

                ad_api.remove_user_from_group(user_name, group_name)

                self.mock_connection.modify.assert_called_once_with(
                    group_dn, {"member": [(MODIFY_DELETE, [user_dn])]}
                )
