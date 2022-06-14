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
    # Allocations expiring

    #Go through all users

        #Go through their associated projects

            #Go thorugh each of their projects' allocations

                #If allocation is expiring (with set amount of days), expiring today, or expired
                #then mark project as having allocation(s) expired 
                #add project to list of their projects with expired allocations for that user

        #Email user about projects listed with expiring allocations

    # allocation attempt
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

                if ((allocation.status.name in ['Active', 'Payment Pending', 'Payment Requested', 'Unpaid']) and (allocation.end_date == expring_in_days)):
                    
                    project_renew_url = '{}/{}/{}/{}'.format(
                    CENTER_BASE_URL.strip('/'), 'project', allocation.project.pk, 'renew')

                    allocation_renew_url = '{}/{}/{}/{}'.format(
                    CENTER_BASE_URL.strip('/'), 'allocation', allocation.pk, 'renew')

                    template_context = {
                        'center_name': CENTER_NAME,
                        'project_title': allocation.project.title,
                        'expring_in_days': days_remaining,
                        'project_dict': projectdict,
                        'allocation_dict': allocationdict,
                        'expiration_dict': expirationdict,
                        'expiration_days': sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)),
                        'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
                        'signature': EMAIL_SIGNATURE
                    }

                    #Check for if expire and cloud usage notifications are set to 'Yes'
                    expire_notification = allocation.allocationattribute_set.filter(
                        allocation_attribute_type__name='EXPIRE NOTIFICATION').first()
                    if expire_notification and expire_notification.value == 'No':
                        continue

                    cloud_usage_notification = allocation.allocationattribute_set.filter(
                        allocation_attribute_type__name='CLOUD_USAGE_NOTIFICATION').first()
                    if cloud_usage_notification and cloud_usage_notification.value == 'No':
                        continue

                    #Filter allocationuser set for our user and append them to email list if they have notifications enabled and are active
                    for projectuser in allocationuser.allocation.project.projectuser_set.filter(user=users, status__name='Active'): 
                        if ((projectuser.enable_notifications) and 
                            (allocationuser.user == users and allocationuser.status.name == 'Active')):

                            if (users.email not in email_receiver_list):
                                email_receiver_list.append(users.email)

                            if allocation_renew_url not in expirationdict:
                                expirationdict[allocation_renew_url] = days_remaining
                            
                            if project_renew_url not in allocationdict:
                                allocationdict[project_renew_url] = list()
                                allocationdict[project_renew_url].append(allocation_renew_url)
                            else:
                                if allocation_renew_url not in allocationdict[project_renew_url]:
                                    allocationdict[project_renew_url].append(allocation_renew_url)

                            if users.email not in projectdict:
                                projectdict[users.email] = list()
                                projectdict[users.email].append(project_renew_url)
                            else:
                                if project_renew_url not in projectdict[users.email]:
                                    projectdict[users.email].append(project_renew_url)

        if len(email_receiver_list) != 0:
            #print('passed conditional')
            #print(email_receiver_list)
            print(projectdict)
            print(allocationdict)
            print(expirationdict)
            print(template_context['expiration_days'])
            print('\n')
            send_email_template('{} your allocation(s) are expiring soon'.format(users),
                        'email/allocation_expiring_test.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list
                        ) 

            logger.info('Allocation(s) expiring in soon, email sent to PI {}.'.format(
                            allocation.project.pi.username))
        #Users
    """   for users in User.objects.all():
        projectdict = {}
        email_receiver_list = []
        for days_remaining in sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)):
            expring_in_days = datetime.datetime.today(
                ) + datetime.timedelta(days=days_remaining)
            #User's projects
            for project in users.projectuser_set.all():
                project_renew_url = '{}/{}/{}/{}'.format(
                    CENTER_BASE_URL.strip('/'), 'project', project.project.pk, 'renew')

                template_context = {
                        'center_name': CENTER_NAME,
                        'project_title': project.project.title,
                        'expring_in_days': days_remaining,
                        'project_dict': projectdict,
                        'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
                        'signature': EMAIL_SIGNATURE
                    }
                #User's project allocations
                for allocation in project.project.allocation_set.filter(status__name__in=['Active', 'Payment Pending', 'Payment Requested', 'Unpaid',], end_date=expring_in_days):

                    #Check for if expire and cloud usage notifications are set to 'Yes'
                    expire_notification = allocation.allocationattribute_set.filter(
                        allocation_attribute_type__name='EXPIRE NOTIFICATION').first()
                    if expire_notification and expire_notification.value == 'No':
                        continue

                    cloud_usage_notification = allocation.allocationattribute_set.filter(
                        allocation_attribute_type__name='CLOUD_USAGE_NOTIFICATION').first()
                    if cloud_usage_notification and cloud_usage_notification.value == 'No':
                        continue

                    #Filter allocationuser set for our user and append them to email list if they have notifications enabled and are active 
                    if (project.enable_notifications and
                    allocation.allocationuser_set.filter(
                        user=users, status__name='Active')):
                    
                        if (users.email not in email_receiver_list):
                            email_receiver_list.append(users.email)

                        if users.email not in projectdict:
                            projectdict[users.email] = list()
                            projectdict[users.email].append(project_renew_url)
                        else:
                            projectdict[users.email].append(project_renew_url)

                    logger.info('Allocation to {} expiring in {} days email sent to PI {}.'.format(
                        allocation.get_parent_resource.name, days_remaining, project.project.pi.username))

        if email_receiver_list:
            send_email_template('{} your allocation(s) are expiring soon'.format(users),
                        'email/allocation_expiring_test.txt',
                        template_context,
                        EMAIL_SENDER,
                        email_receiver_list 
                        )        """
        
            
    """ for days_remaining in sorted(set(EMAIL_ALLOCATION_EXPIRING_NOTIFICATION_DAYS)):
        expring_in_days = datetime.datetime.today(
        ) + datetime.timedelta(days=days_remaining)
        
        for allocation_obj in Allocation.objects.filter(status__name__in=['Active', 'Payment Pending', 'Payment Requested', 'Unpaid',], end_date=expring_in_days):
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
                resource_name, days_remaining, allocation_obj.project.pi.username))"""

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
