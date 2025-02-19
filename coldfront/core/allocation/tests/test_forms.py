import logging

from django.test import TestCase

from coldfront.core.resource.models import Resource
from coldfront.core.allocation.forms import AllocationForm, HSPH_CODE
from coldfront.core.test_helpers.factories import (
    setup_models,
    ResourceTypeFactory,
)


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

    def return_cleaned_form(self, FormClass):
        form = FormClass(
            data=self.post_data, request_user=self.pi_user, project_pk=self.project.pk
        )
        form.is_valid()
        form_cleaned = form.clean()
        return form_cleaned


class AllocationFormTest(AllocationFormBaseTest):
    """Tests for the AllocationCreateView"""

    def setUp(self):
        tier_restype = ResourceTypeFactory(name='Storage Tier')
        self.post_data = {
            'justification': 'test justification',
            'quantity': '1',
            'expense_code': '123-12312-3123-123123-123123-1231-23123',
            'resource': f'{self.storage_allocation.resources.first().pk}',
            'tier': Resource.objects.filter(resource_type=tier_restype).first()
        }

    def test_allocationform_expense_code_invalid1(self):
        """ensure correct error messages for incorrect expense_code value
        """
        self.post_data['expense_code'] = '123456789'
        form = AllocationForm(data=self.post_data, request_user=self.pi_user, project_pk=self.project.pk)
        self.assertEqual(
            form.errors['expense_code'], ['Input must contain exactly 33 digits.']
        )

    def test_allocationform_expense_code_invalid2(self):
        """ensure correct error messages for incorrect expense_code value
        """
        self.post_data['expense_code'] = '123-456AB-CDE789-22222-22222-22222-22222'
        form = AllocationForm(data=self.post_data, request_user=self.pi_user, project_pk=self.project.pk)
        self.assertEqual(
            form.errors['expense_code'], ["Input must consist only of digits (or x'es) and dashes."]
        )

    def test_allocationform_expense_code_invalid3(self):
        """ensure correct error messages for incorrect expense_code value
        """
        self.post_data['expense_code'] = '1Xx-' * 11
        form = AllocationForm(data=self.post_data, request_user=self.pi_user, project_pk=self.project.pk)
        self.assertEqual(
            form.errors['expense_code'], ["xes are only allowed in place of the product code (the third grouping of characters in the code)"]
        )

    def test_allocationform_expense_code_valid(self):
        """Test POST to the AllocationCreateView
        - ensure 33-digit codes go through
        - ensure correctly entered codes get properly formatted
        """
        # correct # of digits with no dashes
        cleaned_form = self.return_cleaned_form(AllocationForm)
        self.assertEqual(
            cleaned_form['expense_code'], '123-12312-8250-123123-123123-1231-23123'
        )

    def test_allocationform_expense_code_valid2(self):
        # check that expense_code was correctly formatted
        # correct # of digits with many dashes
        self.post_data['expense_code'] = '123-' * 11
        cleaned_form = self.return_cleaned_form(AllocationForm)

        self.assertEqual(
            cleaned_form['expense_code'], '123-12312-8250-123123-123123-1231-23123'
        )

    def test_allocationform_expense_code_valid3(self):
        """Test POST to the AllocationCreateView
        - ensure xes count as digits
        """
        # correct # of digits with no dashes
        self.post_data['expense_code'] = '123-12312-xxxx-123123-123123-1231-23123'
        cleaned_form = self.return_cleaned_form(AllocationForm)
        self.assertEqual(
            cleaned_form['expense_code'], '123-12312-8250-123123-123123-1231-23123'
        )

    def test_allocationform_expense_code_valid4(self):
        """Test POST to the AllocationCreateView
        - ensure xes count as digits
        """
        # correct # of digits with no dashes
        self.post_data['expense_code'] = '123.12312.xxxx.123123.123123.1231.23123'
        cleaned_form = self.return_cleaned_form(AllocationForm)
        self.assertEqual(
            cleaned_form['expense_code'], '123-12312-8250-123123-123123-1231-23123'
        )

    def test_allocationform_expense_code_multiplefield_invalid(self):
        """
        Test POST to AllocationCreateView in circumstance where code is entered
        and an existing_expense_codes value has also been selected
        """
        self.post_data['expense_code'] = '123-' * 11
        self.post_data['existing_expense_codes'] = HSPH_CODE
        form = AllocationForm(
            data=self.post_data, request_user=self.pi_user, project_pk=self.project.pk
        )
        self.assertIn("must either select an existing expense code or", form.errors['existing_expense_codes'][0])


class AllocationUpdateFormTest(AllocationFormBaseTest):
    """Tests for the AllocationNoteCreateView"""

    def setUp(self):
        self.post_data = {
            'resource': self.storage_allocation.resources.first(),
            'status': 'Active',
        }
