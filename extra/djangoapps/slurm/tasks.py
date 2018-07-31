
import subprocess

from django.contrib.auth.models import User

from core.djangoapps.subscription.models import SubscriptionUser
from core.djangoapps.subscription.utils import \
    set_subscription_user_status_to_error

# Resource Name
# subscription_user_obj.subscription.resources.first().name

# Resource Type Name
# subscription_user_obj.subscription.resources.first().resource_type.name

# User groups
# subscription_user_obj.user.group_set.all()


def activate_user_account_task1(subscription_user_pk):
    subscription_user_obj = SubscriptionUser.objects.get(pk=subscription_user_pk)

    print('Running activate_user_account_task1 for user: {} for resource {}'.format(
          subscription_user_obj.user.username, subscription_user_obj.subscription.resources.first().name), '.' * 25)

    try:
        completed = subprocess.run(['ls', '-l'], stdout=subprocess.PIPE)
        print('returncode:', completed.returncode)
        print('Have {} bytes in stdout:\n{}'.format(
            len(completed.stdout),
            completed.stdout.decode('utf-8'))
        )
    except subprocess.CalledProcessError as err:
        print('ERROR:', err)

    if False:  # some fail condition
        set_subscription_user_status_to_error(subscription_user_pk)


def activate_user_account_task2(subscription_user_pk):
    subscription_user_obj = SubscriptionUser.objects.get(pk=subscription_user_pk)

    print('Running activate_user_account_task2 for user: {} for resource {}'.format(
          subscription_user_obj.user.username, subscription_user_obj.subscription.resources.first().name), '.' * 25)

    if False:  # some fail condition
        set_subscription_user_status_to_error(subscription_user_pk)


def activate_user_account_task3(subscription_user_pk):
    subscription_user_obj = SubscriptionUser.objects.get(pk=subscription_user_pk)

    print('Running activate_user_account_task3 for user: {} for resource {}'.format(
          subscription_user_obj.user.username, subscription_user_obj.subscription.resources.first().name), '.' * 25)

    if False:  # some fail condition
        set_subscription_user_status_to_error(subscription_user_pk)


def remove_user_account_task1(subscription_user_pk):
    subscription_user_obj = SubscriptionUser.objects.get(pk=subscription_user_pk)
    print('Running remove_user_account_task1 for user: {} for resource {}'.format(
          subscription_user_obj.user.username, subscription_user_obj.subscription.resources.first().name), '.' * 25)

    if False:  # some fail condition
        set_subscription_user_status_to_error(subscription_user_pk)


def remove_user_account_task2(subscription_user_pk):
    subscription_user_obj = SubscriptionUser.objects.get(pk=subscription_user_pk)
    print('Running remove_user_account_task2 for user: {} for resource {}'.format(
          subscription_user_obj.user.username, subscription_user_obj.subscription.resources.first().name), '.' * 25)

    if False:  # some fail condition
        set_subscription_user_status_to_error(subscription_user_pk)
