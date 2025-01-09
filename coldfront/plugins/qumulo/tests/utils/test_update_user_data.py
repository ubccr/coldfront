from django.test import TestCase
from unittest.mock import patch, call, MagicMock

from ldap3 import MODIFY_DELETE

import os
from dotenv import load_dotenv

from django.contrib.auth.models import User

from coldfront.plugins.qumulo.utils.update_user_data import (
    update_user_with_additional_data,
)

load_dotenv()


class TestUpdateUserData(TestCase):

    def test_update_user_with_additional_data_saves_user(self):
        wustlkey = "test_wustlkey"
        with patch(
            "coldfront.plugins.qumulo.utils.update_user_data.ActiveDirectoryAPI"
        ) as mock_init:
            mock_instance = MagicMock()
            mock_init.return_value = mock_instance

            username = "test_wustlkey"
            email = "test@wustl.edu"
            given_name = "Test"
            surname = "Key"
            mock_instance.get_user.return_value = {
                "dn": "foo",
                "attributes": {
                    "sAMAccountName": username,
                    "mail": email,
                    "givenName": given_name,
                    "sn": surname,
                },
            }

            update_user_with_additional_data(wustlkey, test_override=True)

            saved_user = User.objects.get(username=username)

            assert saved_user.username == username
            assert saved_user.email == email
            assert saved_user.last_name == surname
            assert saved_user.first_name == given_name

    def test_update_user_ignores_group(self):
        wustlkey = "test_wustlkey"

        with patch(
            "coldfront.plugins.qumulo.utils.update_user_data.ActiveDirectoryAPI"
        ) as mock_init:
            mock_instance = MagicMock()
            mock_init.return_value = mock_instance
            mock_instance.get_user.side_effect = ValueError
            mock_instance.get_member.return_value = {
                "dn": "foo",
                "objectClass": "group",
            }

            username = "test_wustlkey"

            update_user_with_additional_data(wustlkey, test_override=True)

            saved_user = User.objects.get(username=username)

            assert saved_user.username == username
