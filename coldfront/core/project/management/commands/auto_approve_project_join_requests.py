from coldfront.core.allocation.utils import review_cluster_access_requests_url
from coldfront.core.project.utils import auto_approve_project_join_requests
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from urllib.parse import urljoin
import logging

"""An admin command that automatically approves user requests to join
projects that have completed their delay period."""


class Command(BaseCommand):

    help = (
        'Automatically approves user requests to join projects that have '
        'completed their delay period.')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        """Approve requests, outputting successes and failures. Send an
        email to admins if configured and if a non-zero number of
        requests were processed."""
        results = auto_approve_project_join_requests()
        num_processed = len(results)
        num_successes, num_failures = 0, 0
        for result in results:
            if result.success:
                num_successes = num_successes + 1
                self.stdout.write(self.style.SUCCESS(result.message))
            else:
                num_failures = num_failures + 1
                self.stderr.write(self.style.ERROR(result.message))
        if settings.EMAIL_ENABLED:
            if num_processed:
                self.send_email(num_processed, num_successes, num_failures)

    def send_email(self, num_processed, num_successes, num_failures):
        """Send an email to admins including the number of requests
        processed, and, of those, how many succeeded and failed."""
        subject = 'New Cluster Access Requests'
        template_name = 'email/new_cluster_access_requests.txt'
        context = {
            'num_failures': num_failures,
            'num_processed': num_processed,
            'num_successes': num_successes,
            'review_url': review_cluster_access_requests_url(),
        }
        sender = settings.EMAIL_SENDER
        receiver_list = settings.EMAIL_ADMIN_LIST
        try:
            send_email_template(
                subject, template_name, context, sender, receiver_list)
        except Exception as e:
            message = 'Failed to send notification email. Details:'
            self.stderr.write(self.style.ERROR(message))
            self.stderr.write(self.style.ERROR(str(e)))
            self.logger.error(message)
            self.logger.exception(e)
