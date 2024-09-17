from django.test import TestCase

from coldfront.plugins.qumulo.validators import validate_storage_name
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
    default_form_data,
)

from django.core.exceptions import ValidationError

import os


class TestValidateStorageName(TestCase):
    def setUp(self):
        self.build_data = build_models()

    def test_passes_unique_name(self):
        try:
            validate_storage_name("test-name")
        except Exception:
            self.fail()

    def test_fails_duplicate_name(self):
        test_name = "foo"

        form_data = default_form_data.copy()
        form_data["storage_name"] = test_name

        create_allocation(
            self.build_data["project"], self.build_data["user"], form_data
        )

        with self.assertRaises(ValidationError):
            validate_storage_name(test_name)

    def test_accepts_valid_characters(self):
        try:
            validate_storage_name("test-name_123.test")
        except Exception:
            self.fail()

    def test_rejects_invalid_characters(self):
        invalid_chars = [
            " ",
            "!",
            "@",
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "(",
            ")",
            "+",
            "=",
            "[",
            "]",
            "{",
            "}",
            ";",
            ":",
            "'",
            '"',
            "<",
            ">",
            ",",
            "?",
            "/",
            "\\",
            "|",
            "`",
            "~",
        ]

        for char in invalid_chars:
            with self.assertRaises(ValidationError):
                validate_storage_name(f"test-name{char}123.test")
