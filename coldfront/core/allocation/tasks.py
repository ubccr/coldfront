import datetime
# import the logging library
import logging

from coldfront.core.allocation.models import (Allocation, AllocationAttribute,
                                              AllocationStatusChoice)
from coldfront.core.allocation.utils import get_allocation_user_emails
from coldfront.core.allocation.signals import allocation_expire
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template

# Get an instance of a logger
logger = logging.getLogger(__name__)


CENTER_NAME = import_from_settings('CENTER_NAME')
CENTER_BASE_URL = import_from_settings('CENTER_BASE_URL')
CENTER_PROJECT_RENEWAL_HELP_URL = import_from_settings(
    'CENTER_PROJECT_RENEWAL_HELP_URL')
EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings(
    'EMAIL_OPT_OUT_INSTRUCTION_URL')
EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS = import_from_settings(
    'EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS', [7, ])
EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')


def update_statuses():

    expired_status_choice = AllocationStatusChoice.objects.get(
        name='Expired')
    allocations_to_expire = Allocation.objects.filter(
        status__name__in=['Active', 'Payment Pending', 'Payment Requested', 'Unpaid', ],
        end_date__lt=datetime.datetime.now().date(),
        project__requires_review=True
    )
    for sub_obj in allocations_to_expire:
        sub_obj.status = expired_status_choice
        sub_obj.save()

        allocation_expire.send(sender=update_statuses, allocation_pk=sub_obj.pk)

    logger.info(f'Allocations set to expired: {allocations_to_expire.count()}')


def send_expiry_emails():
    # Allocations expiring

    for days_remaining in sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)):
        expring_in_days = datetime.datetime.today(
        ) + datetime.timedelta(days=days_remaining)

        allocations_expiring_soon = Allocation.objects.filter(
            status__name='Active',
            end_date=expring_in_days,
            project__requires_review=True,
            project__status__name__in=['Active', 'Review Pending'],
            is_locked=False
        )
        for allocation_obj in allocations_expiring_soon:
            if not allocation_obj.project.requires_review:
                return

            expire_notification = allocation_obj.allocationattribute_set.filter(
                allocation_attribute_type__name='EXPIRE NOTIFICATION').first()
            if expire_notification and expire_notification.value == 'No':
                continue

            cloud_usage_notification = allocation_obj.allocationattribute_set.filter(
                allocation_attribute_type__name='CLOUD_USAGE_NOTIFICATION').first()
            if cloud_usage_notification and cloud_usage_notification.value == 'No':
                continue


            allocation_renew_url = '{}/{}/{}/{}'.format(
                CENTER_BASE_URL.strip('/'), 'allocation', allocation_obj.pk, 'renew')

            resource_name = allocation_obj.get_parent_resource.name

            template_context = {
                'center_name': CENTER_NAME,
                'allocation_type': resource_name,
                'expring_in_days': days_remaining,
                'allocation_renew_url': allocation_renew_url,
                'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                'signature': EMAIL_SIGNATURE,
                'project_title': allocation_obj.project.title
            }

            email_receiver_list = get_allocation_user_emails(allocation_obj)
            send_email_template(f'Your {resource_name} allocation is expiring in {days_remaining} days',
                                'email/allocation_expiring.txt',
                                template_context,
                                EMAIL_TICKET_SYSTEM_ADDRESS,
                                email_receiver_list
                                )

            logger.info(
                f'A {resource_name} allocation is expiring in {days_remaining} days, email '
                f'sent to allocation users (allocation pk={allocation_obj.pk}).'
            )

    # Allocations expiring today
    today = datetime.datetime.now().strftime('%Y-%m-%d')

    for allocation_attribute in AllocationAttribute.objects.filter(
            value=today,
            allocation_attribute_type__name='send_expiry_email_on_date'):

        allocation_obj = allocation_attribute.allocation
        days_remaining = allocation_obj.expires_in

        allocation_renew_url = '{}/{}/{}/{}'.format(
            CENTER_BASE_URL.strip('/'), 'allocation', allocation_obj.pk, 'renew')

        resource_name = allocation_obj.get_parent_resource.name

        template_context = {
            'center_name': CENTER_NAME,
            'allocation_type': resource_name,
            'expring_in_days': days_remaining,
            'allocation_renew_url': allocation_renew_url,
            'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
            'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
            'signature': EMAIL_SIGNATURE,
            'project_title': allocation_obj.project.title
        }

        email_receiver_list = get_allocation_user_emails(allocation_obj)
        send_email_template(f'Your {resource_name} allocation is expiring in {days_remaining} days',
                            'email/allocation_expiring.txt',
                            template_context,
                            EMAIL_TICKET_SYSTEM_ADDRESS,
                            email_receiver_list
                            )

        logger.info(
            f'A {resource_name} allocation is expiring in {days_remaining} days, email sent '
            f'to allocation users (allocation pk={allocation_obj.pk}).'
        )

    # Expired allocations

    expring_in_days = datetime.datetime.today() + datetime.timedelta(days=-1)

    for allocation_obj in Allocation.objects.filter(
        end_date=expring_in_days,
        status__name__in=['Active', ],
        project__requires_review=True):

        expire_notification = allocation_obj.allocationattribute_set.filter(
            allocation_attribute_type__name='EXPIRE NOTIFICATION').first()
        if expire_notification and expire_notification.value == 'No':
            continue

        resource_name = allocation_obj.get_parent_resource.name

        allocation_renew_url = '{}/{}/{}/{}'.format(
            CENTER_BASE_URL.strip('/'), 'allocation', allocation_obj.pk, 'renew')

        project_url = '{}/{}/{}/'.format(CENTER_BASE_URL.strip('/'),
                                         'project', allocation_obj.project.pk)

        template_context = {
            'center_name': CENTER_NAME,
            'allocation_type': resource_name,
            'allocation_renew_url': allocation_renew_url,
            'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
            'project_url': project_url,
            'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
            'signature': EMAIL_SIGNATURE,
            'project_title': allocation_obj.project.title
        }

        email_receiver_list = get_allocation_user_emails(allocation_obj)
        send_email_template(f'Your {resource_name} allocation has expired',
                            'email/allocation_expired.txt',
                            template_context,
                            EMAIL_TICKET_SYSTEM_ADDRESS,
                            email_receiver_list
                            )

        logger.info(
            f'A {resource_name} allocation has expired, email sent to allocation users '
            f'(allocation pk={allocation_obj.pk}).'
        )
