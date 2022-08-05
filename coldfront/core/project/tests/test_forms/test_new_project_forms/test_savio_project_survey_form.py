from copy import deepcopy

from django.conf import settings
from django.test import override_settings
from flags.state import flag_enabled

from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectSurveyForm
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.computing_allowance import ComputingAllowance
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.tests.test_base import TestBase


class TestSavioProjectSurveyForm(TestBase):
    """A class for testing SavioProjectSurveyForm."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_fields_conditionally_included_for_deployment(self):
        """Test that, based on whether BRC_ONLY or LRC_ONLY is enabled,
        some fields are (not) included."""
        self.assertTrue(flag_enabled('BRC_ONLY'))
        self.assertFalse(flag_enabled('LRC_ONLY'))

        brc_only_fields = ['data_storage_space', 'cloud_computing']

        computing_allowance = Resource.objects.get(name=BRCAllowances.FCA)

        form = SavioProjectSurveyForm(computing_allowance=computing_allowance)
        for field in brc_only_fields:
            self.assertIn(field, form.fields)

        flags_copy = deepcopy(settings.FLAGS)
        flags_copy.pop('BRC_ONLY')
        flags_copy['LRC_ONLY'] = [{'condition': 'boolean', 'value': True}]
        with override_settings(FLAGS=flags_copy):
            form = SavioProjectSurveyForm(
                computing_allowance=computing_allowance)
            for field in brc_only_fields:
                self.assertNotIn(field, form.fields)

    def test_text_updated_for_deployment(self):
        """Test that, based on whether BRC_ONLY or LRC_ONLY is enabled,
        some fields have updated help text and labels."""
        self.assertTrue(flag_enabled('BRC_ONLY'))
        self.assertFalse(flag_enabled('LRC_ONLY'))

        altered_fields = [
            ('existing_resources', 'label'),
            ('large_memory_nodes', 'label'),
            ('io', 'help_text'),
            ('network_to_internet', 'label'),
        ]

        computing_allowance = Resource.objects.get(name=BRCAllowances.FCA)

        with override_settings(
                PRIMARY_CLUSTER_NAME='Savio', PROGRAM_NAME_SHORT='BRC'):
            form = SavioProjectSurveyForm(
                computing_allowance=computing_allowance)
            for field_name, field_attribute in altered_fields:
                attribute_value = getattr(
                    form.fields[field_name], field_attribute)
                self.assertTrue(
                    'Savio' in attribute_value or 'BRC' in attribute_value)

        flags_copy = deepcopy(settings.FLAGS)
        flags_copy.pop('BRC_ONLY')
        flags_copy['LRC_ONLY'] = [{'condition': 'boolean', 'value': True}]
        with override_settings(
                FLAGS=flags_copy, PRIMARY_CLUSTER_NAME='Lawrencium',
                PROGRAM_NAME_SHORT='LRC'):
            form = SavioProjectSurveyForm(
                computing_allowance=computing_allowance)
            for field_name, field_attribute in altered_fields:
                attribute_value = getattr(
                    form.fields[field_name], field_attribute)
                self.assertTrue(
                    'Lawrencium' in attribute_value or
                    'LRC' in attribute_value)

    def test_text_updated_for_instructional_allowance(self):
        """Test that, if the input computing allowance is instructional,
        some fields have updated help text and labels."""
        self.assertTrue(flag_enabled('BRC_ONLY'))
        self.assertFalse(flag_enabled('LRC_ONLY'))

        altered_fields = {
            ('scope_and_intent', 'label'),
            ('computational_aspects', 'label'),
            ('existing_resources', 'label'),
            ('processor_core_hours_year', 'label'),
        }

        instructional_encountered = False
        for allowance in ComputingAllowanceInterface().allowances():
            form = SavioProjectSurveyForm(computing_allowance=allowance)
            wrapper = ComputingAllowance(allowance)
            for field_name, field_attribute in altered_fields:
                attribute_value = getattr(
                    form.fields[field_name], field_attribute)
                if not wrapper.is_instructional():
                    self.assertTrue(
                        'research' in attribute_value or
                        'project' in attribute_value or
                        'user' in attribute_value)
                else:
                    self.assertTrue(
                        'course' in attribute_value or
                        'student' in attribute_value)
            instructional_encountered = True
        self.assertTrue(instructional_encountered)
