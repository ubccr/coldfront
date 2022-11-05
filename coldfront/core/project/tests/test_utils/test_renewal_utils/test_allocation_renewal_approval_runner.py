from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.tests.test_utils.test_renewal_utils.utils import TestRunnerMixinBase
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalApprovalRunner
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.email.email_strategy import DropEmailStrategy
from decimal import Decimal
from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.test import TestCase


TEST_PRIMARY_CLUSTER_NAME = 'Savio'


class TestRunnerMixin(TestRunnerMixinBase):
    """A mixin for testing AllocationRenewalApprovalRunner."""

    def test_request_allocation_period_not_ended_enforced(self):
        """Test that the provided AllocationRenewalRequest's
        AllocationPeriod must not have ended, or an exception will be
        raised."""
        allocation_period = AllocationPeriod.objects.filter(
            name__startswith='Allowance Year',
            end_date__lt=display_time_zone_current_date()).first()
        self.request_obj.allocation_period = allocation_period
        self.request_obj.save()
        num_service_units = Decimal('0.00')
        try:
            AllocationRenewalApprovalRunner(
                self.request_obj, num_service_units)
        except AssertionError as e:
            message = (
                f'AllocationPeriod already ended on '
                f'{allocation_period.end_date}.')
            self.assertEqual(str(e), message)

    def test_request_allocation_period_started_not_enforced(self):
        """Test that the provided AllocationRenewalRequest's
        AllocationPeriod does not need to have started."""
        allocation_period = get_next_allowance_year_period()
        self.request_obj.allocation_period = allocation_period
        self.request_obj.save()
        num_service_units = Decimal('0.00')
        AllocationRenewalApprovalRunner(self.request_obj, num_service_units)

    def test_request_initial_under_review_status_enforced(self):
        """Test that the provided AllocationRenewalRequest must be in
        the 'Under Review' state, or an exception will be raised."""
        statuses = AllocationRenewalRequestStatusChoice.objects.all()
        self.assertEqual(statuses.count(), 4)
        num_service_units = Decimal('0.00')
        for status in statuses:
            self.request_obj.status = status
            if status.name == 'Under Review':
                AllocationRenewalApprovalRunner(
                    self.request_obj, num_service_units)
            else:
                try:
                    AllocationRenewalApprovalRunner(
                        self.request_obj, num_service_units)
                except AssertionError as e:
                    message = 'The request must have status \'Under Review\'.'
                    self.assertEqual(str(e), message)
                    continue
                else:
                    self.fail('An AssertionError should have been raised.')

    @override_settings(
        REQUEST_APPROVAL_CC_LIST=['admin0@email.com', 'admin1@email.com'])
    def test_runner_sends_emails_conditionally(self):
        """Test that the runner sends a notification email to the
        requester and the PI, CC'ing a designated list of admins, unless
        otherwise specified."""
        request = self.request_obj
        project = request.post_project
        requester = request.requester
        pi = request.pi

        # If not requested, an email should not be sent.
        num_service_units = Decimal('0.00')
        runner = AllocationRenewalApprovalRunner(
            request, num_service_units, email_strategy=DropEmailStrategy())
        runner.run()

        self.assertEqual(len(mail.outbox), 0)

        request.refresh_from_db()
        request.status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')
        request.approved_time = None
        request.save()

        # If requested (by default), an email should be sent.
        runner = AllocationRenewalApprovalRunner(request, num_service_units)
        runner.run()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        expected_subject = (
            f'{settings.EMAIL_SUBJECT_PREFIX} {str(request)} Approved')
        self.assertEqual(expected_subject, email.subject)

        formatted_start_date = request.allocation_period.start_date.strftime(
            '%B %-d, %Y')
        expected_body_snippets = [
            (f'processed on {formatted_start_date}, {num_service_units} will '
             f'be added to the project {project.name}'),
            'will gain the permission to manage the project',
            f'/project/{project.pk}/',
        ]
        for expected_body_snippet in expected_body_snippets:
            self.assertIn(expected_body_snippet, email.body)

        expected_from_email = settings.EMAIL_SENDER
        self.assertEqual(expected_from_email, email.from_email)

        expected_to = sorted([requester.email, pi.email])
        self.assertEqual(expected_to, sorted(email.to))

        expected_cc = ['admin0@email.com', 'admin1@email.com']
        self.assertEqual(expected_cc, sorted(email.cc))

    def test_runner_sets_status_and_approval_time(self):
        """Test that the runner sets the status of the request to
        'Approved' and its approval_time to the current time."""
        self.assertEqual(self.request_obj.status.name, 'Under Review')
        self.assertFalse(self.request_obj.approval_time)
        pre_time = utc_now_offset_aware()

        num_service_units = Decimal('0.00')
        runner = AllocationRenewalApprovalRunner(
            self.request_obj, num_service_units)
        runner.run()

        post_time = utc_now_offset_aware()
        self.request_obj.refresh_from_db()
        approval_time = self.request_obj.approval_time
        self.assertEqual(self.request_obj.status.name, 'Approved')
        self.assertTrue(approval_time)
        self.assertTrue(pre_time <= approval_time <= post_time)


@override_settings(PRIMARY_CLUSTER_NAME=TEST_PRIMARY_CLUSTER_NAME)
class TestUnpooledToUnpooled(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalApprovalRunner in the
    'unpooled_to_unpooled' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            computing_allowance=self.computing_allowance,
            pi=self.pi0,
            pre_project=self.unpooled_project0,
            post_project=self.unpooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'unpooled_to_unpooled'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED)


@override_settings(PRIMARY_CLUSTER_NAME=TEST_PRIMARY_CLUSTER_NAME)
class TestUnpooledToPooled(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalApprovalRunner in the
    'unpooled_to_pooled' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            computing_allowance=self.computing_allowance,
            pi=self.pi0,
            pre_project=self.unpooled_project0,
            post_project=self.pooled_project1)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'unpooled_to_pooled'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.UNPOOLED_TO_POOLED)


@override_settings(PRIMARY_CLUSTER_NAME=TEST_PRIMARY_CLUSTER_NAME)
class TestPooledToPooledSame(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalApprovalRunner in the
    'pooled_to_pooled_same' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            computing_allowance=self.computing_allowance,
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.pooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_pooled_same'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_POOLED_SAME)


@override_settings(PRIMARY_CLUSTER_NAME=TEST_PRIMARY_CLUSTER_NAME)
class TestPooledToPooledDifferent(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalApprovalRunner in the
    'pooled_to_pooled_different' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            computing_allowance=self.computing_allowance,
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.pooled_project1)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_pooled_different'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT)


@override_settings(PRIMARY_CLUSTER_NAME=TEST_PRIMARY_CLUSTER_NAME)
class TestPooledToUnpooledOld(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalApprovalRunner in the
    'pooled_to_unpooled_old' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            computing_allowance=self.computing_allowance,
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.unpooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_unpooled_old'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD)


@override_settings(PRIMARY_CLUSTER_NAME=TEST_PRIMARY_CLUSTER_NAME)
class TestPooledToUnpooledNew(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalApprovalRunner in the
    'pooled_to_unpooled_new' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        new_project_request = \
            self.simulate_new_project_allocation_request_processing()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            computing_allowance=self.computing_allowance,
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=new_project_request.project,
            new_project_request=new_project_request)

    def simulate_new_project_allocation_request_processing(self):
        """Create a new Project and simulate its processing. Return the
        created SavioProjectAllocationRequest."""
        return self.create_under_review_new_project_request()

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_unpooled_new'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW)
