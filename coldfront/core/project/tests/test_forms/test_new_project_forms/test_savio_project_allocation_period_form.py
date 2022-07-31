from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.project.forms_.new_project_forms.request_forms import SavioProjectAllocationPeriodForm
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.tests.test_base import TestBase

from copy import deepcopy
from datetime import timedelta
from django.conf import settings
from django.test import override_settings

from flags.state import disable_flag
from flags.state import enable_flag


class TestSavioProjectAllocationPeriodForm(TestBase):
    """A class for testing SavioProjectAllocationPeriodForm."""

    form_class = SavioProjectAllocationPeriodForm

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Delete existing AllocationPeriods.
        AllocationPeriod.objects.all().delete()

        # Create AllocationPeriods.
        today = display_time_zone_current_date()
        year = today.year
        num_days_in_allocation_year = \
            self.form_class.NUM_DAYS_IN_ALLOCATION_YEAR
        num_days_before_ica = self.form_class.NUM_DAYS_BEFORE_ICA

        self.past_fca_pca_period = AllocationPeriod.objects.create(
            name=f'Allowance Year {year - 1}',
            start_date=today - timedelta(days=num_days_in_allocation_year),
            end_date=today - timedelta(days=1))
        self.current_fca_pca_period = AllocationPeriod.objects.create(
            name=f'Allowance Year {year}',
            start_date=today,
            end_date=today + timedelta(days=num_days_in_allocation_year - 1))
        self.next_fca_pca_period = AllocationPeriod.objects.create(
            name=f'Allowance Year {year + 1}',
            start_date=today + timedelta(days=num_days_in_allocation_year),
            end_date=today + timedelta(
                days=2 * num_days_in_allocation_year - 1))
        self.future_fca_pca_period = AllocationPeriod.objects.create(
            name=f'Allowance Year {year + 2}',
            start_date=today + timedelta(days=2 * num_days_in_allocation_year),
            end_date=today + timedelta(
                days=3 * num_days_in_allocation_year - 1))

        self.past_ica_period = AllocationPeriod.objects.create(
            name=f'Spring Semester {year}',
            start_date=today - timedelta(days=100),
            end_date=today - timedelta(days=1))
        self.current_ica_period = AllocationPeriod.objects.create(
            name=f'Summer Sessions {year}',
            start_date=today - timedelta(days=50),
            end_date=today + timedelta(days=50))
        self.soon_ica_period = AllocationPeriod.objects.create(
            name=f'Fall Semester {year}',
            start_date=today + timedelta(days=num_days_before_ica // 2),
            end_date=today + timedelta(days=3 * num_days_before_ica // 4))
        self.future_ica_period = AllocationPeriod.objects.create(
            name=f'Fall Semester {year + 1}',
            start_date=today + timedelta(days=2 * num_days_before_ica),
            end_date=today + timedelta(days=3 * num_days_before_ica))

    def test_fca_pca_allowance_choices(self):
        """Test that the AllocationPeriods that are selectable for the
        FCA and PCA computing allowances on BRC are the expected
        ones."""
        computing_allowances = (
            Resource.objects.get(name=BRCAllowances.FCA),
            Resource.objects.get(name=BRCAllowances.PCA))

        flag_name = 'ALLOCATION_RENEWAL_FOR_NEXT_PERIOD_REQUESTABLE'

        # If renewal for the next period may not be requested, the next period
        # should not be selectable.
        disable_flag(flag_name)
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy.pop(flag_name)
        with override_settings(FLAGS=flags_copy):
            for computing_allowance in computing_allowances:
                form = self.form_class(computing_allowance=computing_allowance)
                period_choices = form.fields['allocation_period'].queryset
                self.assertEqual(period_choices.count(), 1)
                self.assertIn(self.current_fca_pca_period, period_choices)

        # Otherwise, it should be selectable.
        enable_flag(flag_name)
        for computing_allowance in computing_allowances:
            form = self.form_class(computing_allowance=computing_allowance)
            period_choices = form.fields['allocation_period'].queryset
            self.assertEqual(period_choices.count(), 2)
            self.assertIn(self.current_fca_pca_period, period_choices)
            self.assertIn(self.next_fca_pca_period, period_choices)

    def test_ica_allowance_choices(self):
        """Test that the AllocationPeriods that are selectable for the
        ICA allocation type are the expected ones."""
        computing_allowance = Resource.objects.get(name=BRCAllowances.ICA)
        form = self.form_class(computing_allowance=computing_allowance)
        period_choices = form.fields['allocation_period'].queryset
        self.assertEqual(period_choices.count(), 2)
        self.assertIn(self.current_ica_period, period_choices)
        self.assertIn(self.soon_ica_period, period_choices)

    def test_other_allowance_choices(self):
        """Test that the AllocationPeriods that are selectable for the
        other allocation types are the expected ones."""
        computing_allowances = (
            Resource.objects.get(name=BRCAllowances.CO),
            Resource.objects.get(name=BRCAllowances.RECHARGE))
        for computing_allowance in computing_allowances:
            form = self.form_class(computing_allowance=computing_allowance)
            period_choices = form.fields['allocation_period'].queryset
            self.assertEqual(period_choices.count(), 0)
