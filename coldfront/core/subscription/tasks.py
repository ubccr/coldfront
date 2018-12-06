import datetime
# import the logging library
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from coldfront.core.subscription.models import (Subscription,
                                                 SubscriptionStatusChoice)

from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email_template
# Get an instance of a logger
logger = logging.getLogger(__name__)


CENTER_NAME = import_from_settings('CENTER_NAME')
CENTER_BASE_URL = import_from_settings('CENTER_BASE_URL')
CENTER_PROJECT_RENEWAL_HELP_URL = import_from_settings('CENTER_PROJECT_RENEWAL_HELP_URL')
EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings('EMAIL_OPT_OUT_INSTRUCTION_URL')
EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
EMAIL_SUBSCRIPTION_EXPIRING_NOTIFICATION_DAYS = import_from_settings(
    'EMAIL_SUBSCRIPTION_EXPIRING_NOTIFICATION_DAYS', [7, ])


def update_statuses():

    expired_status_choice = SubscriptionStatusChoice.objects.get(name='Expired')
    subscriptions_to_expire = Subscription.objects.filter(
        status__name='Active', end_date__lt=datetime.datetime.now().date())
    for sub_obj in subscriptions_to_expire:
        sub_obj.status = expired_status_choice
        sub_obj.save()

    logger.info('Subscriptions set to expired: {}'.format(subscriptions_to_expire.count()))


def send_expiry_emails():
    ### Subscriptions expiring

    for days_remaining in sorted(set(EMAIL_SUBSCRIPTION_EXPIRING_NOTIFICATION_DAYS)):
        expring_in_days = datetime.datetime.today() + datetime.timedelta(days=days_remaining)

        for subscription_obj in Subscription.objects.filter(status__name='Active', end_date=expring_in_days):

            subscripion_renew_url = '{}/{}/{}/{}/'.format(CENTER_BASE_URL.strip('/'), 'subscription', subscription_obj.pk, 'renew')


            resource_name = subscription_obj.get_parent_resource.name

            template_context = {
                'center_name': CENTER_NAME,
                'subscription_type': resource_name,
                'expring_in_days': days_remaining,
                'subscripion_renew_url': subscripion_renew_url,
                'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
                'signature': EMAIL_SIGNATURE

            }

            email_receiver_list = []
            for subscription_user in subscription_obj.project.projectuser_set.all():
                if (subscription_user.enable_notifications and
                    subscription_obj.subscriptionuser_set.filter(
                        user=subscription_user.user, status__name='Active')
                    and subscription_user.user.email not in email_receiver_list):

                    email_receiver_list.append(subscription_user.user.email)

            print(subscription_obj.id, email_receiver_list)
            send_email_template('Subscription to {} expiring in {} days'.format(resource_name, days_remaining),
                'email/subscription_expiring.txt',
                template_context,
                EMAIL_SENDER,
                email_receiver_list
            )



            logger.info('Subscription to {} expiring in {} days email sent to PI {}.'.format(resource_name, days_remaining, subscription_obj.project.pi.username))


    ### Expired subscriptions

    expring_in_days = datetime.datetime.today() + datetime.timedelta(days=-1)

    for subscription_obj in Subscription.objects.filter(end_date=expring_in_days):

        resource_name = subscription_obj.get_parent_resource.name

        subscripion_renew_url = '{}/{}/{}/{}/'.format(CENTER_BASE_URL.strip('/'), 'subscription', subscription_obj.pk, 'renew')

        project_url = '{}/{}/{}/'.format(CENTER_BASE_URL.strip('/'), 'project', subscription_obj.project.pk)

        template_context = {
            'center_name': CENTER_NAME,
            'subscription_type': resource_name,
            'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
            'project_url': project_url,
            'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL,
            'signature': EMAIL_SIGNATURE
        }

        email_receiver_list = []
        for subscription_user in subscription_obj.project.projectuser_set.all():
            if (subscription_user.enable_notifications and
                subscription_obj.subscriptionuser_set.filter(
                    user=subscription_user.user, status__name='Active')
                and subscription_user.user.email not in email_receiver_list):

                email_receiver_list.append(subscription_user.user.email)

        print(subscription_obj.id, email_receiver_list)
        send_email_template('Subscription to {} has expired'.format(resource_name),
            'email/subscription_expired.txt',
            template_context,
            EMAIL_SENDER,
            email_receiver_list
        )


        logger.info('Subscription to {} expired email sent to PI {}.'.format(resource_name, days_remaining, subscription_obj.project.pi.username))
