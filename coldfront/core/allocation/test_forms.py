import logging

from django.test import TestCase

from coldfront.core.allocation.forms import (
    AllocationForm,
)
from coldfront.core.test_helpers.factories import setup_models


logging.disable(logging.CRITICAL)

UTIL_FIXTURES = [
    "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

class AllocationFormBaseTest(TestCase):
    """Base class for allocation view tests."""

    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests."""
        setup_models(cls)

    def return_cleaned_form(self):
        form = AllocationForm(
            data=self.post_data, request_user=self.pi_user, project_pk=self.project.pk
        )
        form.is_valid()
        form_cleaned = form.clean()
        return form_cleaned

class AllocationFormTest(AllocationFormBaseTest):
    """Tests for the AllocationCreateView"""

    def setUp(self):
        self.post_data = {
            'justification': 'test justification',
            'quantity': '1',
            'resource': f'{self.proj_allocation.resources.first().pk}',
        }

    def test_allocationcreateview_post_offerlettercode_invalid(self):
        """ensure correct error messages for incorrect offer_letter_code value
        """
        self.post_data['offer_letter_code'] = '123456789'
        form = AllocationForm(data=self.post_data, request_user=self.pi_user, project_pk=self.project.pk)
        self.assertEqual(
            form.errors['offer_letter_code'], ['Input must contain exactly 33 digits.']
        )

    def test_allocationcreateview_post_offerlettercode_valid(self):
        """Test POST to the AllocationCreateView
        - ensure 33-digit codes go through
        - ensure correctly entered codes get properly formatted
        """
        # correct # of digits with no dashes
        self.post_data['offer_letter_code'] = '123' * 11
        cleaned_form = self.return_cleaned_form()
        self.assertEqual(
            cleaned_form['offer_letter_code'], '123-12312-3123-123123-123123-1231-23123'
        )

    def test_allocationcreateview_post_offerlettercode_valid2(self):
        # check that offer code was correctly formatted
        # correct # of digits with many dashes
        self.post_data['offer_letter_code'] = '123-' * 11
        cleaned_form = self.return_cleaned_form()
        self.assertEqual(
            cleaned_form['offer_letter_code'], '123-12312-3123-123123-123123-1231-23123'
        )
