from django.test import TestCase

from coldfront.plugins.qumulo.validators import validate_storage_root
from django.core.exceptions import ValidationError

import os


class TestValidateStorageRoot(TestCase):
    def test_passes_starts_with_storage_root(self):
        storage_root = os.environ.get("STORAGE2_PATH").strip("/")

        try:
            validate_storage_root(f"/{storage_root}/test-dir")
        except Exception:
            self.fail()

    def test_fails_does_not_start_with_storage_root(self):
        with self.assertRaises(ValidationError):
            validate_storage_root(f"/test-dir")
