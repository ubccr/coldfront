from django.test import TestCase

from coldfront.plugins.qumulo.validators import validate_relative_path
from django.core.exceptions import ValidationError


class TestValidateRelativePath(TestCase):

    def test_absolute_path_fails(self):
        with self.assertRaises(ValidationError):
            validate_relative_path("/test-dir")

    def test_relative_path_only_single_part_passes(self):
        validate_relative_path("test-dir")

    def test_relative_path_only_multiple_parts_fails(self):
        with self.assertRaises(ValidationError):
            validate_relative_path("test-dir/test-dir2")
