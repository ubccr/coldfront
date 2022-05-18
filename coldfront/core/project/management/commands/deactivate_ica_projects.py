import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.core.project.models import Project
from coldfront.core.project.utils import deactivate_project_and_allocation
from coldfront.core.utils.common import add_argparse_dry_run_argument
from coldfront.core.utils.common import display_time_zone_current_date
from coldfront.core.utils.mail import send_email_template

"""An admin command that performs deactivation steps for ICA Projects
whose end dates have passed."""


class Command(BaseCommand):

    help = (
        'Expire ICA projects whose end dates have passed. Optionally notify '
        'project owners')
    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        add_argparse_dry_run_argument(parser)
        parser.add_argument(
            '--send_emails',
            action='store_true',
            default=False,
            help='Send emails to PIs/managers about project deactivation.')

    def handle(self, *args, **options):
        """Deactivate ICA projects whose end_dates have passed, by:
            - Setting the Project's status to 'Inactive'.
            - Setting the Allocation's status to 'Expired'.
            - Setting the Allocation's start_date to the current date
              and its end_date to None.
            - Resetting the Service Units for the Allocation and its
             AllocationUsers to zero.
        """
        dry_run = options['dry_run']
        send_emails = options['send_emails']

        current_date = display_time_zone_current_date()

        for project in Project.objects.filter(name__startswith='ic_'):
            accounting_allocation_objects = get_accounting_allocation_objects(
                project)
            allocation = accounting_allocation_objects.allocation
            expiry_date = allocation.end_date

            if expiry_date and expiry_date < current_date:
                self.perform_deactivation(
                    project, accounting_allocation_objects, dry_run)
                if send_emails:
                    self.send_emails(project, expiry_date, dry_run)

    def perform_deactivation(self, project, accounting_allocation_objects,
                             dry_run):
        """Given a Project and an associated AccountingAllocationObjects
        objects, perform deactivation steps. Optionally display updates
        instead of performing them."""
        allocation = accounting_allocation_objects.allocation
        current_allowance = \
            accounting_allocation_objects.allocation_attribute.value
        updated_allowance = settings.ALLOCATION_MIN

        if dry_run:
            message = (
                f'Would deactivate Project {project.name} ({project.pk}), '
                f'update Allocation {allocation.pk}, and update Service Units '
                f'from {current_allowance} to {updated_allowance}.')
            self.stdout.write(self.style.WARNING(message))
        else:
            deactivate_project_and_allocation(project)
            message = (
                f'Deactivated Project {project.name} ({project.pk}), updated '
                f'Allocation {allocation.pk}, and updated Service Units from '
                f'{current_allowance} to {updated_allowance}.')
            self.stdout.write(self.style.SUCCESS(message))
            self.logger.info(message)

    def send_emails(self, project, expiry_date, dry_run):
        """Email project owners about the project's deactivation.
        Optionally display updates instead of performing them."""
        recipients = project.managers_and_pis_emails()
        num_recipients = len(recipients)
        recipients_noun = (
            f'{num_recipients} user' + int(num_recipients > 1) * 's')

        if dry_run:
            message = f'Would send a notification email to {recipients_noun}.'
            self.stdout.write(self.style.WARNING(message))
            return

        subject = 'Expired ICA Project Deactivation'
        template_name = 'email/expired_ica_project.txt'
        context = {
            'project_name': project.name,
            'expiry_date': expiry_date.strftime('%m-%d-%Y'),
            'support_email': settings.CENTER_HELP_EMAIL,
            'signature': settings.EMAIL_SIGNATURE,
        }
        sender = settings.EMAIL_SENDER

        try:
            send_email_template(
                subject, template_name, context, sender, recipients)
        except Exception as e:
            message = 'Failed to send notification email. Details:'
            self.stderr.write(self.style.ERROR(message))
            self.stderr.write(self.style.ERROR(str(e)))
            self.logger.error(message)
            self.logger.exception(e)
        else:
            message = f'Sent a notification email to {recipients_noun}.'
            self.stdout.write(self.style.SUCCESS(message))
