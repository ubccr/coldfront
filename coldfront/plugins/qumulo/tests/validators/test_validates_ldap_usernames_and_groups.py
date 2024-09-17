from django.test import TestCase

from django.core.exceptions import ValidationError
from coldfront.plugins.qumulo.validators import validate_ldap_usernames_and_groups


class TestValidatesLdapUsernamesAndGroups(TestCase):

    def setUp(self):
        self.expect_error_message = "The ddname \"%(name)\" must not include '(', ')', '@', '/', or end with a period."
        self.translate_table = str.maketrans(
            {
                "+": r"\+",
                ";": r"\;",
                ",": r"\,",
                "\\": r"\\",
                '"': r"\"",
                "<": r"\<",
                ">": r"\>",
                "#": r"\#",
            }
        )
        return super().setUp()

    def test_validates_when_name_is_none(self):
        name = None
        is_valid = validate_ldap_usernames_and_groups(name)
        self.assertIsNone(is_valid)

    def test_validates_when_name_is_blank(self):
        blank_names = ["", " ", "  "]
        for name in blank_names:
            is_valid = validate_ldap_usernames_and_groups(name)
            self.assertIsNone(is_valid)

    def test_validates_when_name_ends_with_period(self):
        name = "name-ends-with."
        self.assertRaises(ValidationError, validate_ldap_usernames_and_groups, name)
        self.assertRaisesMessage(ValidationError, self.expect_error_message)

    def test_validates_when_name_has_disallowed_characters(self):
        for invalid_token in ["(", ")", "@", "/"]:
            name = f"name{invalid_token}here"
            self.assertRaises(ValidationError, validate_ldap_usernames_and_groups, name)
            self.assertRaisesMessage(ValidationError, self.expect_error_message)

    def test_validates_when_name_escapes_special_characters(self):
        name = 'name+;,\"test"<test>#'
        escaped_name = name.translate(self.translate_table)
        is_valid = validate_ldap_usernames_and_groups(escaped_name)
        self.assertTrue(is_valid)

    def test_validates_when_name_does_not_escape_special_characters(self):
        unescaped_name = 'name+;,"test"<test>#'
        self.assertRaises(
            ValidationError, validate_ldap_usernames_and_groups, unescaped_name
        )
        self.assertRaisesMessage(ValidationError, self.expect_error_message)

    def test_validates_when_is_valid(self):
        for name in [
            "name.last",
            "name_last",
            "n.k-last",
            "Lab XYZ Allocation 1",
            "Lab XYZ Allocation 2",
        ]:
            is_valid = validate_ldap_usernames_and_groups(name)
            self.assertTrue(is_valid)
