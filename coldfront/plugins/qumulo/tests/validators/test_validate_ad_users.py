from django.test import TestCase
from unittest.mock import patch, MagicMock, call

from django.core.exceptions import ValidationError
from coldfront.plugins.qumulo.validators import (
    validate_ad_users,
    validate_single_ad_user,
)


class TestValidateAdUsers(TestCase):
    def setUp(self):
        self.patcher = patch("coldfront.plugins.qumulo.validators.ActiveDirectoryAPI")
        self.mock_active_directory = self.patcher.start()

        self.mock_get_user = MagicMock()
        self.mock_active_directory.return_value.get_user = self.mock_get_user

        return super().setUp()

    def tearDown(self):
        self.patcher.stop()

        return super().tearDown()

    def test_passes_emptylist(self):
        try:
            validate_ad_users([])
        except ValidationError:
            self.fail("Failed to validate empty list")

    def test_validates_a_single_user(self):
        self.mock_get_user.return_value = {
            "dn": "user_dn",
            "attributes": {"other_attr": "value"},
        }
        user = "userkey"

        try:
            validate_ad_users([user])
        except ValidationError:
            self.fail("Failed to validate a single user")

        try:
            validate_single_ad_user(user)
        except ValidationError:
            self.fail("Failed to validate a single user")

    def test_fails_for_a_user(self):
        self.mock_get_user.side_effect = ValueError("foo")
        user = "userkey"

        with self.assertRaises(ValidationError) as context_manager:
            validate_ad_users([user])

        self.assertEquals(context_manager.exception.error_list[0].message, user)
        self.assertEquals(context_manager.exception.error_list[0].code, "invalid")

        self.mock_get_user.side_effect = ValueError("foo")
        user = "userkey"

        with self.assertRaises(ValidationError) as context_manager:
            validate_single_ad_user(user)

        self.assertEquals(context_manager.exception.message, "This WUSTL Key could not be validated")
        self.assertEquals(context_manager.exception.code, "invalid")

    def test_validates_multiple_users(self):
        self.mock_get_user.return_value = {
            "dn": "user_dn",
            "attributes": {"other_attr": "value"},
        }
        users = ["userkey", "userkey2", "userkey3"]

        try:
            validate_ad_users(users)
        except ValidationError:
            self.fail("Failed to validate multiple users")
        calls = list(map(lambda user: call(user), users))
        self.mock_get_user.assert_has_calls(calls)

    def test_notify_multiple_failed_users(self):
        def mock_side_effect(user):
            if user == "userkey2":
                return {
                    "dn": "user_dn",
                    "attributes": {"other_attr": "value"},
                }
            raise ValueError("Invalid user:".format(user))

        self.mock_get_user.side_effect = mock_side_effect
        users = ["userkey", "userkey2", "userkey3"]

        with self.assertRaises(ValidationError) as context_manager:
            validate_ad_users(users)

        self.assertIn(users[0], context_manager.exception)
        self.assertIn(users[2], context_manager.exception)
