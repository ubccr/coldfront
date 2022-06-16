from collections import UserDict
import datetime
# import the logging library
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from coldfront.core.allocation.models import (Allocation, AllocationAttribute,
                                              AllocationStatusChoice)
from coldfront.core.user.models import (User, UserProfile)
from coldfront.core.project.models import (Project, ProjectUser)
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
    #Allocations expiring today and soon
    EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS.insert(0, 0)
    for users in User.objects.all():
        projectdict = {}
        allocationdict = {}
        expirationdict = {}
        email_receiver_list = []
        for days_remaining in sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)):
            expring_in_days = (datetime.datetime.today(
                ) + datetime.timedelta(days=days_remaining)).date()
                       
            #User's project allocations
            for allocationuser in users.allocationuser_set.all():
                allocation = allocationuser.allocation

                if (((allocation.status.name in ['Active', 'Payment Pending', 'Payment Requested', 'Unpaid']) and (allocation.end_date == expring_in_days))
                    or ((days_remaining == 0) and (allocation.end_date == expring_in_days))):
                    
                    project_url = '{}/{}/{}/'.format(
                    CENTER_BASE_URL.strip('/'), 'project', allocation.project.pk)

                    if (allocation.status.name in ['Payment Pending', 'Payment Requested', 'Unpaid']):
                        allocation_renew_url = '{}/{}/{}/'.format(
                        CENTER_BASE_URL.strip('/'), 'allocation', allocation.pk)
                    else:
                        allocation_renew_url = '{}/{}/{}/{}'.format(
                        CENTER_BASE_URL.strip('/'), 'allocation', allocation.pk, 'renew')

                    resource_name = allocation.get_parent_resource.name

                    template_context = {
                        'center_name': CENTER_NAME,
                        'expring_in_days': days_remaining,
                        'project_dict': projectdict,
                        'allocation_dict': allocationdict,
                        'expiration_dict': expirationdict,
                        'expiration_days': sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)),
                        'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
                        'signature': EMAIL_SIGNATURE
                    }

                    if (days_remaining == 0):
                        allocation_attribute = allocation.allocationattribute_set.filter(
                            value=expring_in_days,
                            allocation_attribute_type__name='send_expiry_email_on_date')

                        if not allocation_attribute:
                            continue
                    else:
                        expire_notification = allocation.allocationattribute_set.filter(
                            allocation_attribute_type__name='EXPIRE NOTIFICATION').first()
                        if expire_notification and expire_notification.value == 'No':
                            continue

                        cloud_usage_notification = allocation.allocationattribute_set.filter(
                            allocation_attribute_type__name='CLOUD_USAGE_NOTIFICATION').first()
                        if cloud_usage_notification and cloud_usage_notification.value == 'No':
                            continue

                    for projectuser in allocation.project.projectuser_set.filter(user=users, status__name='Active'): 
                        if ((projectuser.enable_notifications) and 
                            (allocationuser.user == users and allocationuser.status.name == 'Active')):

                            if (users.email not in email_receiver_list):
                                email_receiver_list.append(users.email)

                            if allocation_renew_url not in expirationdict:
                                expirationdict[allocation_renew_url] = days_remaining
                            
                            if project_url not in allocationdict:
                                allocationdict[project_url] = []
                                allocationdict[project_url].append({allocation_renew_url : resource_name})
                            else:
                                if allocation_renew_url not in allocationdict[project_url]:
                                    allocationdict[project_url].append({allocation_renew_url : resource_name})

                            if allocation.project.title not in projectdict:
                                projectdict[allocation.project.title] = project_url
                            
        if len(email_receiver_list) != 0:
            send_email_template('{} your allocation(s) are expiring soon'.format(users),
                        'email/allocation_expiring_test.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                        ) 

            logger.debug('Allocation(s) expiring in soon, email sent to user {}.'.format(
                            users))

    #Allocations expired
    for users in User.objects.all():
        projectdict = {}
        allocationdict = {}
        email_receiver_list = []
        
        expring_in_days = (datetime.datetime.today() + datetime.timedelta(days=-1)).date()
                
        for allocationuser in users.allocationuser_set.all():
            allocation = allocationuser.allocation

            if (allocation.end_date == expring_in_days):
                
                project_url = '{}/{}/{}/'.format(
                CENTER_BASE_URL.strip('/'), 'project', allocation.project.pk)

                allocation_renew_url = '{}/{}/{}/{}'.format(
                CENTER_BASE_URL.strip('/'), 'allocation', allocation.pk, 'renew')

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
                if expire_notification and expire_notification.value == 'No':
                    continue

                for projectuser in allocation.project.projectuser_set.filter(user=users, status__name='Active'): 
                    if ((projectuser.enable_notifications) and 
                        (allocationuser.user == users and allocationuser.status.name == 'Active')):

                        if (users.email not in email_receiver_list):
                            email_receiver_list.append(users.email)

                        if project_url not in allocationdict:
                                allocationdict[project_url] = []
                                allocationdict[project_url].append({allocation_renew_url : resource_name})
                        else:
                            if allocation_renew_url not in allocationdict[project_url]:
                                allocationdict[project_url].append({allocation_renew_url : resource_name})

                        if allocation.project.title not in projectdict:
                            projectdict[allocation.project.title] = project_url
                            
        if len(email_receiver_list) != 0:

            send_email_template('{} your allocation(s) have expired'.format(users),
                        'email/allocation_expired.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                        ) 

            logger.debug('Allocation(s) expiring in soon, email sent to user {}.'.format(
                            users))