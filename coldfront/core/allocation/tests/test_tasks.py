
from django.test import TestCase

from django.utils import timezone

from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.test_helpers.factories import (
    setup_models,
    AllocationFactory,
    AllocationChangeRequestFactory,
)
from coldfront.core.allocation.tasks import send_request_reminder_emails

UTIL_FIXTURES = [
    "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

class RequestReminderEmails(TestCase):

    fixtures = UTIL_FIXTURES

    def setUp(self):
        """set up test data"""
        setup_models(self)

        # create Allocations with status "new" and "created" dates of 5, 7, and 9 days ago
        self.allocation1 = AllocationFactory(
            status=AllocationStatusChoice.objects.get(name="New"),
            created=timezone.now() - timezone.timedelta(days=5),
        )
        self.allocation2 = AllocationFactory(
            status=AllocationStatusChoice.objects.get(name="New"),
            created=timezone.now() - timezone.timedelta(days=7)
        )
        self.allocation3 = AllocationFactory(
            status=AllocationStatusChoice.objects.get(name="New"),
            created=timezone.now() - timezone.timedelta(days=9)
        )

        # create AllocationChangeRequests with status "pending" and "created" dates of 5, 7, and 9 days ago
        self.acr1 = AllocationChangeRequestFactory(
            created=timezone.now() - timezone.timedelta(days=5),
        )
        self.acr2 = AllocationChangeRequestFactory(
            created=timezone.now() - timezone.timedelta(days=7)
        )
        self.acr3 = AllocationChangeRequestFactory(
            created=timezone.now() - timezone.timedelta(days=9)
        )

    def test_send_request_reminder_emails(self):
        """test send_request_reminder_emails task"""
        pending_changerequests, pending_allocations = send_request_reminder_emails()
