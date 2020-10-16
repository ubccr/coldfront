from coldfront.api.statistics.tests.test_job_base import TestJobBase
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationAttributeUsage
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUserAttributeUsage
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.resource.models import Resource
from decimal import ConversionSyntax
from decimal import Decimal
from django.conf import settings
from django.test import override_settings


class TestCanSubmitJobView(TestJobBase):
    """A suite for testing the can_submit_job view."""

    def assert_result(self, job_cost, user_id, account_id, status_code,
                      success, message):
        """Check that the given parameters produce the given status
        code, success, and message."""
        response = self.client.get(TestCanSubmitJobView.get_url(
            job_cost, user_id, account_id))
        self.assertEqual(response.status_code, status_code)
        json = response.json()
        self.assertEqual(json['success'], success)
        self.assertEqual(json['message'], message)

    @staticmethod
    def get_url(job_cost, user_id, account_id):
        """Return the request URL for the given parameters."""
        return f'/api/can_submit_job/{job_cost}/{user_id}/{account_id}/'

    def test_other_requests_not_allowed(self):
        """Test that other requests (e.g. POST; PATCH; DELETE) are not
        allowed."""
        url = TestCanSubmitJobView.get_url('0', '0', '0')
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.patch(url).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_empty_arguments(self):
        """Test that requests fail if the arguments are not nonempty."""
        def message(field):
            return f'{field}  is not a nonempty string.'
        self.assert_result(' ', '0', '0', 400, False, message('job_cost'))
        self.assert_result('0', ' ', '0', 400, False, message('user_id'))
        self.assert_result('0', '0', ' ', 400, False, message('account_id'))

    def test_invalid_job_costs(self):
        """Test that requests with various invalid job_cost values
        fail."""
        message = (
            f'Encountered exception [{ConversionSyntax}] when converting '
            f'job_cost alphabetic to a decimal.')
        self.assert_result('alphabetic', '0', '0', 400, False, message)

        message = 'job_cost -0.01 is not nonnegative.'
        self.assert_result('-0.01', '0', '0', 400, False, message)

        message = (
            f'job_cost 1000000000.00 has greater than '
            f'{settings.DECIMAL_MAX_DIGITS} digits.')
        self.assert_result('1000000000.00', '0', '0', 400, False, message)

        message = (
            f'job_cost 1.000 has greater than '
            f'{settings.DECIMAL_MAX_PLACES} decimal places.')
        self.assert_result('1.000', '0', '0', 400, False, message)

    def test_invalid_user_id(self):
        """Test that requests with an invalid user_id value fail."""
        self.user.delete()
        message = f'No user exists with user_id 0.'
        self.assert_result('1.00', '0', '0', 400, False, message)

    def test_invalid_account_id(self):
        """Test that requests with an invalid account_id value fail."""
        self.project.delete()
        message = f'No account exists with account_id 0.'
        self.assert_result(
            '1.00', '0', '0', 400, False, message)

    def test_no_user_account_association(self):
        """Test that requests with an unrelated user and account
        fail."""
        self.project_user.delete()
        message = f'User user0 is not a member of account test_project.'
        self.assert_result('1.00', '0', 'test_project', 400, False, message)

    def test_no_active_compute_allocation(self):
        """Test that requests wherein the account has no active compute
        allocation fail."""
        message = 'Account test_project has no active compute allocation.'
        # The allocation is expired.
        self.allocation.status = AllocationStatusChoice.objects.get(
            name='Expired')
        self.allocation.save()
        self.assert_result('1.00', '0', 'test_project', 400, False, message)
        # The allocation is active, but does not have Savio Compute as a
        # resource.
        self.allocation.status = AllocationStatusChoice.objects.get(
            name='Active')
        self.allocation.resources.all().delete()
        self.allocation.save()
        self.assert_result('1.00', '0', 'test_project', 400, False, message)
        # The allocation does not exist.
        self.allocation.delete()
        self.assert_result('1.00', '0', 'test_project', 400, False, message)

    def test_user_not_member_of_compute_allocation(self):
        """Test that requests wherein the user is not an active member
        of the account's compute allocation fail."""
        message = (
            f'User user0 is not an active member of the compute allocation '
            f'for account test_project.')
        # The allocation user has been removed from the allocation.
        self.allocation_user.status = AllocationUserStatusChoice.objects.get(
            name='Removed')
        self.allocation_user.save()
        self.assert_result('1.00', '0', 'test_project', 400, False, message)
        # The allocation user does not exist.
        self.allocation_user.delete()
        self.assert_result('1.00', '0', 'test_project', 400, False, message)

    def test_bad_database_state_causes_server_error(self):
        """Test that requests fails if there are too few or too many of
        a given database object than expected."""
        message = 'Unexpected server error.'
        # The account has more than one allocation with Savio Compute as a
        # resource.
        resource = Resource.objects.get(name='Savio Compute')
        status = AllocationStatusChoice.objects.get(name='Active')
        allocation = Allocation.objects.create(
            project=self.project, status=status)
        allocation.resources.add(resource)
        allocation.save()
        self.assert_result('1.00', '0', 'test_project', 500, False, message)
        allocation.delete()
        # There are multiple allocation user status choices named 'Active'.
        AllocationUserStatusChoice.objects.create(name='Active')
        self.assert_result('1.00', '0', 'test_project', 500, False, message)
        # There are no allocation user status choices named 'Active'.
        AllocationUserStatusChoice.objects.filter(name='Active').delete()
        self.assert_result('1.00', '0', 'test_project', 500, False, message)

    def test_cost_exceeds_allocation(self):
        """Test that requests with costs that would cause usages to
        exceed allocations fail."""
        # Usage objects have been created by signals.
        self.assertEqual(AllocationAttributeUsage.objects.count(), 1)
        self.assertEqual(
            self.account_usage.value, Decimal(settings.ALLOCATION_MIN))
        self.assertEqual(AllocationUserAttributeUsage.objects.count(), 1)
        self.assertEqual(
            self.user_account_usage.value, Decimal(settings.ALLOCATION_MIN))
        # Manually increase the usages.
        self.account_usage.value = Decimal(self.allocation_attribute.value)
        self.account_usage.save()
        self.user_account_usage.value = Decimal(
            self.allocation_user_attribute.value)
        self.user_account_usage.save()
        # If the account's usage would exceed its allocation, the request
        # should fail.
        message = (
            'Adding job_cost 0.01 to account balance 1000.00 would exceed '
            'account allocation 1000.00.')
        self.assert_result('0.01', '0', 'test_project', 200, False, message)
        # The usages should not have changed.
        self.user_account_usage.refresh_from_db()
        self.account_usage.refresh_from_db()
        self.assertEqual(self.user_account_usage.value, Decimal('500.00'))
        self.assertEqual(self.account_usage.value, Decimal('1000.00'))
        # Manually increase the account's allocation.
        self.allocation_attribute.value = '2000.00'
        self.allocation_attribute.save()
        # If the user's usage would exceed his/her allocation, the request
        # should fail.
        message = (
            'Adding job_cost 0.01 to user balance 500.00 would exceed user '
            'allocation 500.00.')
        self.assert_result('0.01', '0', 'test_project', 200, False, message)
        # The usages should not have changed.
        self.user_account_usage.refresh_from_db()
        self.account_usage.refresh_from_db()
        self.assertEqual(self.user_account_usage.value, Decimal('500.00'))
        self.assertEqual(self.account_usage.value, Decimal('1000.00'))

    def test_success(self):
        """Test that requests without issue succeed."""
        message = 'A job with job_cost 500.00 can be submitted.'
        self.assert_result('500.00', '0', 'test_project', 200, True, message)

    def test_condo_jobs_always_allowed(self):
        """Test that requests under Condo accounts always succeed,
        regardless of cost."""
        job_cost = str(settings.ALLOCATION_MAX)

        self.assertEqual(self.allocation_attribute.value, '1000.00')
        self.assertFalse(self.project.name.startswith('co_'))
        message = (
            f'Adding job_cost {job_cost} to account balance 0.00 would exceed '
            f'account allocation 1000.00.')
        self.assert_result(job_cost, '0', 'test_project', 200, False, message)

        self.project.name = 'co_project'
        self.project.save()
        message = f'A job with job_cost {job_cost} can be submitted.'
        self.assert_result(job_cost, '0', 'co_project', 200, True, message)

    @override_settings(ALLOW_ALL_JOBS=True)
    def test_allow_all_jobs(self):
        """Test that, when the ALLOW_ALL_JOBS setting is True, normally
        failing requests succeed."""
        job_cost = settings.ALLOCATION_MAX

        self.assertEqual(self.allocation_attribute.value, '1000.00')
        message = f'A job with job_cost {job_cost} can be submitted.'
        self.assert_result(job_cost, '0', 'test_project', 200, True, message)
