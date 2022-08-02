from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.tests.test_utils.test_new_project_utils.utils import TestRunnerMixinBase
from coldfront.core.project.utils_.new_project_utils import SavioProjectApprovalRunner
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase

from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core import mail
from django.test import override_settings


class TestSavioProjectApprovalRunner(TestRunnerMixinBase, TestBase):
    """A class for testing SavioProjectApprovalRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a request.
        computing_allowance = Resource.objects.get(name=BRCAllowances.FCA)
        interface = ComputingAllowanceInterface()
        self.request_obj = SavioProjectAllocationRequest.objects.create(
            requester=self.requester,
            allocation_type=interface.name_short_from_name(
                computing_allowance.name),
            computing_allowance=computing_allowance,
            allocation_period=self.allocation_period,
            pi=self.pi,
            project=self.project,
            pool=False,
            survey_answers={},
            status=ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Processing'),
            request_time=utc_now_offset_aware() - timedelta(days=1))

    @override_settings(
        REQUEST_APPROVAL_CC_LIST=['admin0@email.com', 'admin1@email.com'])
    def test_runner_sends_emails_conditionally(self):
        """Test that the runner sends a notification email to the
        requester and the PI, CC'ing a designated list of admins, if
        requested."""
        request = self.request_obj
        project = request.project
        requester = request.requester
        pi = request.pi

        # If not requested, an email should not be sent.
        num_service_units = Decimal('0.00')
        runner = SavioProjectApprovalRunner(
            self.request_obj, num_service_units)
        runner.run()

        self.assertEqual(len(mail.outbox), 0)

        request.refresh_from_db()
        request.status = ProjectAllocationRequestStatusChoice.objects.get(
            name='Approved - Processing')
        request.approved_time = None
        request.save()

        # If requested, an email should be sent.
        runner = SavioProjectApprovalRunner(
            self.request_obj, num_service_units, send_email=True)
        runner.run()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        expected_subject = (
            f'{settings.EMAIL_SUBJECT_PREFIX} New Project Request '
            f'({project.name}) Approved')
        self.assertEqual(expected_subject, email.subject)

        formatted_start_date = request.allocation_period.start_date.strftime(
            '%B %-d, %Y')
        expected_body_snippets = [
            'request to create project',
            (f'under Allocation Period "{request.allocation_period.name}" has '
             f'been approved'),
            (f'processed on {formatted_start_date}, {num_service_units} will '
             f'be added to the project'),
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

        # If pooling, the email should be different.
        request.refresh_from_db()
        request.pool = True
        request.status = ProjectAllocationRequestStatusChoice.objects.get(
            name='Approved - Processing')
        request.approved_time = None
        request.save()

        runner = SavioProjectApprovalRunner(
            self.request_obj, num_service_units, send_email=True)
        runner.run()

        self.assertEqual(len(mail.outbox), 2)
        email = mail.outbox[-1]

        expected_subject = (
            f'{settings.EMAIL_SUBJECT_PREFIX} Pooled Project Request '
            f'({project.name}) Approved')
        self.assertEqual(expected_subject, email.subject)
        expected_body_snippets[0] = (
            'request to pool your allocation with project')
        for expected_body_snippet in expected_body_snippets:
            self.assertIn(expected_body_snippet, email.body)
        self.assertEqual(expected_from_email, email.from_email)
        self.assertEqual(expected_to, sorted(email.to))
        self.assertEqual(expected_cc, sorted(email.cc))

    def test_runner_sets_status_and_approval_time(self):
        """Test that the runner sets the status of the request to
        'Approved - Scheduled' and its approval_time to the current
        time."""
        self.assertEqual(self.request_obj.status.name, 'Approved - Processing')
        self.assertFalse(self.request_obj.approval_time)
        pre_time = utc_now_offset_aware()

        num_service_units = Decimal('0.00')
        runner = SavioProjectApprovalRunner(
            self.request_obj, num_service_units)
        runner.run()

        post_time = utc_now_offset_aware()
        self.request_obj.refresh_from_db()
        approval_time = self.request_obj.approval_time
        self.assertEqual(self.request_obj.status.name, 'Approved - Scheduled')
        self.assertTrue(approval_time)
        self.assertTrue(pre_time <= approval_time <= post_time)
