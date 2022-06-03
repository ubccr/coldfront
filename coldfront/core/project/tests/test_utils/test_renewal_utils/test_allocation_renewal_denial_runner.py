from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.tests.test_utils.test_renewal_utils.utils import TestRunnerMixinBase
from coldfront.core.project.utils_.renewal_utils import AllocationRenewalDenialRunner
from coldfront.core.project.utils_.renewal_utils import get_next_allowance_year_period
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.common import utc_now_offset_aware
from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.test import TestCase


class TestRunnerMixin(TestRunnerMixinBase):
    """A mixin for testing AllocationRenewalDenialRunner."""

    def test_request_allocation_period_not_ended_not_enforced(self):
        """Test that the provided AllocationRenewalRequest's
        AllocationPeriod does not need to have not ended."""
        allocation_period = AllocationPeriod.objects.filter(
            name__startswith='Allowance Year',
            end_date__lt=display_time_zone_current_date()).first()
        self.request_obj.allocation_period = allocation_period
        self.request_obj.save()
        AllocationRenewalDenialRunner(self.request_obj)

    def test_request_allocation_period_started_not_enforced(self):
        """Test that the provided AllocationRenewalRequest's
        AllocationPeriod does not need to have started."""
        allocation_period = get_next_allowance_year_period()
        self.request_obj.allocation_period = allocation_period
        self.request_obj.save()
        AllocationRenewalDenialRunner(self.request_obj)

    def test_request_initial_not_complete_status_enforced(self):
        """Test that the provided AllocationRenewalRequest must not be
        in the 'Complete' state, or an exception will be raised."""
        statuses = AllocationRenewalRequestStatusChoice.objects.all()
        self.assertEqual(statuses.count(), 4)
        for status in statuses:
            self.request_obj.status = status
            self.request_obj.save()
            if status.name != 'Complete':
                AllocationRenewalDenialRunner(self.request_obj)
            else:
                try:
                    AllocationRenewalDenialRunner(self.request_obj)
                except AssertionError as e:
                    message = 'The request must not have status \'Complete\'.'
                    self.assertEqual(str(e), message)
                    continue
                else:
                    self.fail('An AssertionError should have been raised.')

    @override_settings(
        REQUEST_APPROVAL_CC_LIST=['admin0@email.com', 'admin1@email.com'])
    def test_runner_sends_emails(self):
        """Test that the runner sends a notification email to the
        requester and the PI, CC'ing a designated list of admins."""
        request = self.request_obj
        requester = request.requester
        pi = request.pi

        # Set the reason.
        request.state['other'] = {
            'justification': 'This is a test of email functionality.',
            'timestamp': utc_now_offset_aware().isoformat(),
        }
        request.save()

        runner = AllocationRenewalDenialRunner(request)
        runner.run()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        request.refresh_from_db()

        expected_subject = (
            f'{settings.EMAIL_SUBJECT_PREFIX} {str(request)} Denied')
        self.assertEqual(expected_subject, email.subject)

        expected_body_snippets = [
            'has been denied for the following reason',
            'Category: Other',
            f'Justification: {request.state["other"]["justification"]}',
            f'Current Project: {request.pre_project.name}',
            f'Requested Project: {request.post_project.name}',
            'If you have any questions',
        ]
        for expected_body_snippet in expected_body_snippets:
            self.assertIn(expected_body_snippet, email.body)

        expected_from_email = settings.EMAIL_SENDER
        self.assertEqual(expected_from_email, email.from_email)

        expected_to = sorted([requester.email, pi.email])
        self.assertEqual(expected_to, sorted(email.to))

        expected_cc = ['admin0@email.com', 'admin1@email.com']
        self.assertEqual(expected_cc, sorted(email.cc))

    def test_runner_sets_status(self):
        """Test that the runner sets the status of the request to
        'Denied'."""
        request = self.request_obj

        self.assertEqual(request.status.name, 'Under Review')

        runner = AllocationRenewalDenialRunner(request)
        runner.run()

        request.refresh_from_db()
        self.assertEqual(request.status.name, 'Denied')


class TestNewProjectDenialMixin(object):
    """A mixin for testing that a new Project associated with the
    request is given to the 'Denied' status."""

    def test_new_project_denied(self):
        """Test that a new Project created during the request is
        denied."""
        request = self.request_obj
        project = request.post_project

        denied_status = ProjectStatusChoice.objects.get(name='Denied')
        self.assertNotEqual(denied_status, project.status)

        runner = AllocationRenewalDenialRunner(request)
        runner.run()

        project.refresh_from_db()
        self.assertEqual(denied_status, project.status)


class TestUnpooledToUnpooled(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalDenialRunner in the
    'unpooled_to_unpooled' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            pi=self.pi0,
            pre_project=self.unpooled_project0,
            post_project=self.unpooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'unpooled_to_unpooled'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.UNPOOLED_TO_UNPOOLED)


class TestUnpooledToPooled(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalDenialRunner in the
    'unpooled_to_pooled' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            pi=self.pi0,
            pre_project=self.unpooled_project0,
            post_project=self.pooled_project1)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'unpooled_to_pooled'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.UNPOOLED_TO_POOLED)


class TestPooledToPooledSame(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalDenialRunner in the
    'pooled_to_pooled_same' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.pooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_pooled_same'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_POOLED_SAME)


class TestPooledToPooledDifferent(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalDenialRunner in the
    'pooled_to_pooled_different' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.pooled_project1)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_pooled_different'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_POOLED_DIFFERENT)


class TestPooledToUnpooledOld(TestRunnerMixin, TestCase):
    """A class for testing the AllocationRenewalDenialRunner in the
    'pooled_to_unpooled_old' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=self.unpooled_project0)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_unpooled_old'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_OLD)


class TestPooledToUnpooledNew(TestNewProjectDenialMixin, TestRunnerMixin,
                              TestCase):
    """A class for testing the AllocationRenewalDenialRunner in the
    'pooled_to_unpooled_new' case."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        new_project_request = self.create_under_review_new_project_request()
        self.request_obj = self.create_request(
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review'),
            pi=self.pi0,
            pre_project=self.pooled_project0,
            post_project=new_project_request.project,
            new_project_request=new_project_request)

    def test_pooling_preference_case(self):
        """Test that the pooling preference case for the class' renewal
        request is 'pooled_to_unpooled_new'."""
        self.assert_pooling_preference_case(
            AllocationRenewalRequest.POOLED_TO_UNPOOLED_NEW)
