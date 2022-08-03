import datetime
# import the logging library
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from coldfront.core.allocation.models import (Allocation, AllocationAttribute,
                                              AllocationStatusChoice)
from coldfront.core.utils.common import get_domain_url, import_from_settings
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


def update_statuses():

    expired_status_choice = AllocationStatusChoice.objects.get(
        name='Expired')
    allocations_to_expire = Allocation.objects.filter(
        status__name__in=['Active','Payment Pending','Payment Requested', 'Unpaid',], end_date__lt=datetime.datetime.now().date())
    for sub_obj in allocations_to_expire:
        sub_obj.status = expired_status_choice
        sub_obj.save()

    logger.info('Allocations set to expired: {}'.format(
        allocations_to_expire.count()))


def send_expiry_emails():
    # Allocations expiring

    for days_remaining in sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)):
        expring_in_days = datetime.datetime.today(
        ) + datetime.timedelta(days=days_remaining)

        for allocation_obj in Allocation.objects.filter(status__name='Active', end_date=expring_in_days):

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
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
                'signature': EMAIL_SIGNATURE

            }

            email_receiver_list = []
            for allocation_user in allocation_obj.project.projectuser_set.all():
                if (allocation_user.enable_notifications and
                    allocation_obj.allocationuser_set.filter(
                        user=allocation_user.user, status__name='Active')
                        and allocation_user.user.email not in email_receiver_list):

                    email_receiver_list.append(allocation_user.user.email)

            send_email_template('Allocation to {} expiring in {} days'.format(resource_name, days_remaining),
                                'email/allocation_expiring.txt',
                                template_context,
                                EMAIL_SENDER,
                                email_receiver_list
                                )

            logger.info('Allocation to {} expiring in {} days email sent to PI {}.'.format(
                resource_name, days_remaining, allocation_obj.project.pi.username))

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
            'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
            'signature': EMAIL_SIGNATURE

        }

        email_receiver_list = []
        for allocation_user in allocation_obj.project.projectuser_set.all():
            if (allocation_user.enable_notifications and
                allocation_obj.allocationuser_set.filter(
                    user=allocation_user.user, status__name='Active')
                    and allocation_user.user.email not in email_receiver_list):

                email_receiver_list.append(allocation_user.user.email)

        send_email_template('Allocation to {} expiring in {} days'.format(resource_name, days_remaining),
                            'email/allocation_expiring.txt',
                            template_context,
                            EMAIL_SENDER,
                            email_receiver_list
                            )

        logger.info('Allocation to {} expiring in {} days email sent to PI {}.'.format(
            resource_name, days_remaining, allocation_obj.project.pi.username))

    # Expired allocations

    expring_in_days = datetime.datetime.today() + datetime.timedelta(days=-1)

    for allocation_obj in Allocation.objects.filter(end_date=expring_in_days):

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
            'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
            'project_url': project_url,
            'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
            'signature': EMAIL_SIGNATURE
        }

        email_receiver_list = []
        for allocation_user in allocation_obj.project.projectuser_set.all():
            if (allocation_user.enable_notifications and
                allocation_obj.allocationuser_set.filter(
                    user=allocation_user.user, status__name='Active')
                    and allocation_user.user.email not in email_receiver_list):

                email_receiver_list.append(allocation_user.user.email)

        send_email_template('Allocation to {} has expired'.format(resource_name),
                            'email/allocation_expired.txt',
                            template_context,
                            EMAIL_SENDER,
                            email_receiver_list
                            )

        logger.info('Allocation to {} expired email sent to PI {}.'.format(
            resource_name, allocation_obj.project.pi.username))
