from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.api.statistics.utils import set_project_allocation_value
from coldfront.api.statistics.utils import set_project_usage_value
from coldfront.api.statistics.utils import set_project_user_allocation_value
from coldfront.api.statistics.utils import set_project_user_usage_value
from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.utils_.email_utils import project_email_receiver_list
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import project_detail_url
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.mail import send_email_template

from decimal import Decimal
from django.conf import settings

import logging

"""Utilities relating to requests to add Service Units to a Project's
allocation."""


logger = logging.getLogger(__name__)


class AllocationAdditionRunnerBase(object):
    """A base class that Runners for handling AllocationAdditionRequests
    should inherit from."""

    def __init__(self, request_obj, *args, **kwargs):
        """Store the given AllocationAdditionRequest. If it has an
        unexpected status, raise an error."""
        self.request_obj = request_obj
        expected_status = AllocationAdditionRequestStatusChoice.objects.get(
            name='Under Review')
        self.assert_request_status(expected_status)

    def assert_request_status(self, expected_status):
        """Raise an assertion error if the request does not have the
        given expected status."""
        if not isinstance(
                expected_status, AllocationAdditionRequestStatusChoice):
            raise TypeError(
                'Status is not an AllocationAdditionRequestStatusChoice.')
        message = f'The request must have status \'{expected_status}\'.'
        assert self.request_obj.status == expected_status, message

    def run(self):
        raise NotImplementedError('This method is not implemented.')


class AllocationAdditionDenialRunner(AllocationAdditionRunnerBase):
    """An object that performs necessary database changes when an
    AllocationAdditionRequest is denied."""

    def deny_request(self):
        """Set the status of the request to 'Denied'."""
        self.request_obj.status = \
            AllocationAdditionRequestStatusChoice.objects.get(name='Denied')
        self.request_obj.save()

    def run(self):
        """Deny the request and send notification emails."""
        self.deny_request()
        self.send_email()

    def send_email(self):
        """Send a notification email to the managers and PIs (who have
        notifications enabled) of the requested Project, stating that
        the request has been denied."""
        try:
            request = self.request_obj
            project = request.project
            reason = request.denial_reason()

            subject = f'Service Units Purchase Request ({project.name}) Denied'
            template_name = (
                'email/project_allocation_addition/request_denied.txt')
            context = {
                'num_sus': str(request.num_service_units),
                'project_name': project.name,
                'reason_category': reason.category,
                'reason_justification': reason.justification,
                'signature': settings.EMAIL_SIGNATURE,
                'support_email': settings.CENTER_HELP_EMAIL,
            }
            sender = settings.EMAIL_SENDER
            receiver_list = project_email_receiver_list(project)
            send_email_template(
                subject, template_name, context, sender, receiver_list)
        except Exception as e:
            logger.error('Failed to send notification email. Details:')
            logger.exception(e)


class AllocationAdditionProcessingRunner(AllocationAdditionRunnerBase):
    """An object that performs necessary database changes when an
    AllocationAdditionRequest is processed."""

    accounting_objects = None

    def __init__(self, request_obj):
        """If the request has an invalid number of service units or if
        an expected database object does not exist, raise an error."""
        super().__init__(request_obj)
        self.accounting_objects = get_accounting_allocation_objects(
            self.request_obj.project)

    def complete_request(self):
        """Set the status of the request to 'Complete' and set its
        completion_time."""
        self.request_obj.status = \
            AllocationAdditionRequestStatusChoice.objects.get(name='Complete')
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()

    def compute_updated_service_units(self, added_service_units):
        """Return the new total number of Service Units the given
        Project should have, after subtracting usage and adding the
        given number."""
        objects = self.accounting_objects
        allocation = Decimal(objects.allocation_attribute.value)
        usage = Decimal(objects.allocation_attribute_usage.value)
        unused_service_units = max(allocation - usage, Decimal('0.00'))
        return unused_service_units + added_service_units

    def run(self):
        """Perform database changes and send a notification email.
        Return the Project's updated Service Units amount."""
        added_service_units = self.request_obj.num_service_units
        total_service_units = self.compute_updated_service_units(
            added_service_units)
        date_time = utc_now_offset_aware()

        self.update_allocation(total_service_units, date_time)
        self.update_user_allocations(total_service_units, date_time)

        self.complete_request()
        self.send_email(added_service_units, total_service_units)

        return total_service_units

    def send_email(self, added_service_units, total_service_units):
        """Send a notification email to the managers and PIs (who have
        notifications enabled) of the requested Project, stating that
        the request has been processed, that the given number of service
        units have been added, and that the Project's total number of
        service units is the given number."""
        try:
            request = self.request_obj
            project = request.project
            subject = (
                f'Service Units Purchase Request ({project.name}) Processed')
            template_name = (
                'email/project_allocation_addition/request_processed.txt')
            context = {
                'added_sus': str(added_service_units),
                'project_name': project.name,
                'project_url': project_detail_url(project),
                'signature': settings.EMAIL_SIGNATURE,
                'support_email': settings.CENTER_HELP_EMAIL,
                'total_sus': str(total_service_units),
            }
            sender = settings.EMAIL_SENDER
            receiver_list = project_email_receiver_list(project)
            send_email_template(
                subject, template_name, context, sender, receiver_list)
        except Exception as e:
            logger.error('Failed to send notification email. Details:')
            logger.exception(e)

    def update_allocation(self, num_service_units, date_time):
        """Set the Project's allocation to the given number, reset its
        usage to zero, update its start time to the given datetime, and
        create a transaction."""
        project = self.request_obj.project

        set_project_allocation_value(project, num_service_units)
        set_project_usage_value(project, Decimal('0.00'))

        self.accounting_objects.allocation.start_date = date_time
        self.accounting_objects.allocation.save()

        ProjectTransaction.objects.create(
            project=project,
            date_time=date_time,
            allocation=num_service_units)

    def update_user_allocations(self, num_service_units, date_time):
        """Set ProjectUsers' allocations to the given number, reset
        their usages to zero, and create transactions."""
        project = self.request_obj.project
        for project_user in project.projectuser_set.all():
            user = project_user.user

            allocation_updated = set_project_user_allocation_value(
                user, project, num_service_units)
            set_project_user_usage_value(user, project, Decimal('0.00'))

            if allocation_updated:
                ProjectUserTransaction.objects.create(
                    project_user=project_user,
                    date_time=date_time,
                    allocation=num_service_units)


def can_project_purchase_service_units(project):
    """Return whether the given Project is eligible to purchase
    additional Service Units for its allowance."""
    if not isinstance(project, Project):
        raise TypeError(f'{project} is not a Project object.')
    return project.name.startswith('ac_')


def has_pending_allocation_addition_request(project):
    """Return whether the given Project has an 'Under Review'
    AllocationAdditionRequest."""
    under_review_status = AllocationAdditionRequestStatusChoice.objects.get(
        name='Under Review')
    return AllocationAdditionRequest.objects.filter(
        project=project, status=under_review_status).exists()
