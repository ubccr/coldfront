import datetime
# import the logging library
import logging

from django.utils import timezone
from django.contrib.auth import get_user_model

from coldfront.core.allocation.models import (
    Allocation,
    AllocationStatusChoice,
    AllocationChangeRequest,
    AllocationAttributeChangeRequest,
)
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

EMAIL_ADMINS_ON_ALLOCATION_EXPIRE = import_from_settings('EMAIL_ADMINS_ON_ALLOCATION_EXPIRE')
EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST')
ADMIN_REMINDER_EMAIL = import_from_settings('ADMIN_REMINDER_EMAIL')
PENDING_ALLOCATION_STATUSES = import_from_settings(
    'PENDING_ALLOCATION_STATUSES', ['New'])
ACTIVE_ALLOCATION_STATUSES = import_from_settings(
    'ACTIVE_ALLOCATION_STATUSES', ['Active', 'Payment Pending', 'Payment Requested', 'Unpaid'])

def update_statuses():

    expired_status_choice = AllocationStatusChoice.objects.get(name='Expired')
    allocations_to_expire = Allocation.objects.filter(
        status__name__in=ACTIVE_ALLOCATION_STATUSES,
        end_date__lt=timezone.now().date()
    )
    for sub_obj in allocations_to_expire:
        sub_obj.status = expired_status_choice
        sub_obj.save()

    logger.info('Allocations set to expired: %s', allocations_to_expire.count())


def send_request_reminder_emails():
    """
    Send reminders to admins about active allocation requests and
    allocation update requests that have existed for more than a week
    """
    req_alert_date = timezone.now().date() - datetime.timedelta(days=7)
    # Allocation Change Requests are separate items.
    # if any that are more than a week old and "pending", send an email digest to admins
    pending_changerequests = {
        change_request: AllocationAttributeChangeRequest.objects.filter(
            allocation_change_request=change_request,
        )
        for change_request in AllocationChangeRequest.objects.filter(
                status__name='Pending', created__lte=req_alert_date
            )
    }
    if pending_changerequests:
        allocation_change_template_context = {
            'center_name': CENTER_NAME,
            'pending_changerequests': pending_changerequests,
            'signature': EMAIL_SIGNATURE,
            'url_base': f'{CENTER_BASE_URL.strip("/")}/allocation/change-request/'
        }

        send_email_template(
            subject='Pending Allocation Changes',
            template_name='email/pending_allocation_changes.txt',
            template_context=allocation_change_template_context,
            sender=EMAIL_SENDER,
            receiver_list=[ADMIN_REMINDER_EMAIL,],
        )
    # Allocation Requests are allocations marked as "new"
    pending_allocations = Allocation.objects.filter(
        status__name__in=PENDING_ALLOCATION_STATUSES, created__lte=req_alert_date
    )
    if pending_allocations:

        new_allocation_template_context = {
            'center_name': CENTER_NAME,
            'pending_allocations': pending_allocations,
            'signature': EMAIL_SIGNATURE,
            'url_base': f'{CENTER_BASE_URL.strip("/")}/allocation/'
        }

        send_email_template(
            subject='Pending Allocations',
            template_name='email/pending_allocations.txt',
            template_context=new_allocation_template_context,
            sender=EMAIL_SENDER,
            receiver_list=[ADMIN_REMINDER_EMAIL,],
        )

    # return statement for testing
    return (pending_changerequests, pending_allocations)


def send_expiry_emails():
    #Allocations expiring soon
    admin_projectdict = {}
    admin_allocationdict = {}
    for user in get_user_model().objects.all():
        projectdict = {}
        allocationdict = {}
        email_receiver_list = []

        expring_in_days = timezone.now().date() + datetime.timedelta(days=1)

        for allocationuser in user.allocationuser_set.all():
            allocation = allocationuser.allocation

            if allocation.end_date == expring_in_days:

                project_url = f'{CENTER_BASE_URL.strip("/")}/{"project"}/{allocation.project.pk}/'

                allocation_renew_url = f'{CENTER_BASE_URL.strip("/")}/{"allocation"}/{allocation.pk}/{"renew"}/'

                allocation_url = f'{CENTER_BASE_URL.strip("/")}/{"allocation"}/{allocation.pk}/'

                resource_name = allocation.get_parent_resource.name

                template_context = {
                    'center_name': CENTER_NAME,
                    'project_dict': projectdict,
                    'allocation_dict': allocationdict,
                    'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                    'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
                    'signature': EMAIL_SIGNATURE
                }

                expire_notification = allocation.allocationattribute_set.filter(
                    allocation_attribute_type__name='EXPIRE NOTIFICATION').first()

                for projectuser in allocation.project.projectuser_set.filter(user=user, status__name='Active'):
                    if not (expire_notification and expire_notification.value == 'Yes'):
                        continue

                    if not (projectuser.enable_notifications and
                        allocationuser.user == user and allocationuser.status.name == 'Active'):
                        continue

                    if user.email not in email_receiver_list:
                        email_receiver_list.append(user.email)

                    if project_url not in allocationdict:
                        allocationdict[project_url] = []
                    if {allocation_renew_url : resource_name} not in allocationdict[project_url]:
                        allocationdict[project_url].append({allocation_renew_url : resource_name})

                    if allocation.project.title not in projectdict:
                        projectdict[allocation.project.title] = (project_url, allocation.project.pi.username)

                    if EMAIL_ADMINS_ON_ALLOCATION_EXPIRE:

                        if project_url not in admin_allocationdict:
                            admin_allocationdict[project_url] = []
                        if {allocation_url : resource_name} not in admin_allocationdict[project_url]:
                            admin_allocationdict[project_url].append({allocation_url : resource_name})

                        if allocation.project.title not in admin_projectdict:
                            admin_projectdict[allocation.project.title] = (project_url, allocation.project.pi.username)


        if email_receiver_list:

            send_email_template('Your access to resource(s) have expired',
                        'email/allocation_expired.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                        )

            logger.debug(f'Allocation(s) expired email sent to user {user}.')

        projectdict = {}
        expirationdict = {}
        email_receiver_list = []
        for days_remaining in sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)):

            expring_in_days = timezone.now().date() + datetime.timedelta(days=days_remaining)

            for allocationuser in user.allocationuser_set.all():
                allocation = allocationuser.allocation

                if allocation.status.name in ACTIVE_ALLOCATION_STATUSES and allocation.end_date == expring_in_days:

                    project_url = f'{CENTER_BASE_URL.strip("/")}/{"project"}/{allocation.project.pk}/'

                    allocation_renew_url = f'{CENTER_BASE_URL.strip("/")}/{"allocation"}/{allocation.pk}/'
                    if allocation.status.name == 'Active':
                        allocation_renew_url = allocation_renew_url + '{"renew"}/'

                    resource_name = allocation.get_parent_resource.name

                    template_context = {
                        'center_name': CENTER_NAME,
                        'expring_in_days': days_remaining,
                        'project_dict': projectdict,
                        'expiration_dict': expirationdict,
                        'expiration_days': sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)),
                        'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
                        'signature': EMAIL_SIGNATURE
                    }

                    expire_notification = allocation.allocationattribute_set.filter(
                        allocation_attribute_type__name='EXPIRE NOTIFICATION').first()
                    if expire_notification and expire_notification.value == 'No':
                        continue

                    cloud_usage_notification = allocation.allocationattribute_set.filter(
                        allocation_attribute_type__name='CLOUD_USAGE_NOTIFICATION').first()
                    if cloud_usage_notification and cloud_usage_notification.value == 'No':
                        continue

                    for projectuser in allocation.project.projectuser_set.filter(user=user, status__name='Active'):
                        if not (projectuser.enable_notifications and
                            allocationuser.user == user and allocationuser.status.name == 'Active'):
                            continue

                        if user.email not in email_receiver_list:
                            email_receiver_list.append(user.email)

                        if days_remaining not in expirationdict:
                            expirationdict[days_remaining] = []
                        expirationdict[days_remaining].append((project_url, allocation_renew_url, resource_name))

                        if allocation.project.title not in projectdict:
                            projectdict[allocation.project.title] = (project_url, allocation.project.pi.username)

        if email_receiver_list:

            send_email_template(f"Your access to {CENTER_NAME}'s resources is expiring soon",
                        'email/allocation_expiring.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                        )

            logger.debug(f'Allocation(s) expiring in soon, email sent to user {user}.')


    # produce "allocations have expired" list and send emails
    if EMAIL_ADMINS_ON_ALLOCATION_EXPIRE:

        if admin_projectdict:

            admin_template_context = {
                'project_dict': admin_projectdict,
                'allocation_dict': admin_allocationdict,
                'signature': EMAIL_SIGNATURE
            }

            send_email_template('Allocation(s) have expired',
                                'email/admin_allocation_expired.txt',
                                admin_template_context,
                                EMAIL_SENDER,
                                [EMAIL_ADMIN_LIST,]
                                )
