from django.test import TestCase
from django.core.exceptions import ValidationError
from coldfront.plugins.qumulo.validators import validate_leading_forward_slash


class TestValidateLeadingForwardSlash(TestCase):
    def test_no_error_with_valid_input(self):
        try:
            validate_leading_forward_slash("/foo")
        except:
            self.fail(
                "validate_leading_forward_slash raised ExceptionType unexpectedly!"
            )

    def test_raises_error_with_invalid_input(self):
        with self.assertRaises(ValidationError):
            validate_leading_forward_slash("foo")

    def test_no_error_on_empty_input(self):
        try:
            validate_leading_forward_slash("")
        except:
            self.fail(
                "validate_leading_forward_slash raised ExceptionType unexpectedly!"
            )
