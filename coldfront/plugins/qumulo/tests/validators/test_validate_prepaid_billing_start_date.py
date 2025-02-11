from django.test import TestCase

from coldfront.plugins.qumulo.validators import validate_prepaid_start_date
from coldfront.plugins.qumulo.tests.utils.mock_data import (
    build_models,
    create_allocation,
    default_form_data,
)

from django.core.exceptions import ValidationError

from datetime import datetime

import os


class TestValidatePrepaidBillingStartDate(TestCase):
    def setUp(self):
        self.build_data = build_models()

    def test_passes_first_of_the_month(self):
        start_date = datetime.strptime("2025-01-01", "%Y-%m-%d")
        try:
            validate_prepaid_start_date(start_date)
        except Exception:
            self.fail()

    def test_fails_not_first_of_the_month(self):
        start_date = datetime.strptime("2025-01-15", "%Y-%m-%d")

        with self.assertRaises(ValidationError):
            validate_prepaid_start_date(start_date)
