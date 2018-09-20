from django.dispatch import receiver
from django_q.tasks import async_task

from common.djangolibs.utils import import_from_settings
from core.djangoapps.project.views import (ProjectAddUsersView,
                                           ProjectRemoveUsersView)
from core.djangoapps.subscription.signals import (subscription_activate_user,
                                                  subscription_remove_user)
from core.djangoapps.subscription.views import (SubscriptionAddUsersView,
                                                SubscriptionCreateView,
                                                SubscriptionDeleteUsersView)


def do_nothing_func():
    pass


def apply_freeipa_signal_setting(func):

    FREEIPA_DISABLE_SIGNAL_PROCESSING = import_from_settings('FREEIPA_DISABLE_SIGNAL_PROCESSING')

    def wrapper(*args, **kwargs):
        if FREEIPA_DISABLE_SIGNAL_PROCESSING:
            return do_nothing_func()
        else:
            return func(*args, **kwargs)

    return wrapper


@apply_freeipa_signal_setting
@receiver(subscription_activate_user, sender=ProjectAddUsersView)
@receiver(subscription_activate_user, sender=SubscriptionCreateView)
@receiver(subscription_activate_user, sender=SubscriptionAddUsersView)
def activate_user(sender, **kwargs):
    subscription_user_pk = kwargs.get('subscription_user_pk')
    async_task('extra.djangoapps.freeipa.tasks.add_user_group', subscription_user_pk)


@apply_freeipa_signal_setting
@receiver(subscription_remove_user, sender=ProjectRemoveUsersView)
@receiver(subscription_remove_user, sender=SubscriptionDeleteUsersView)
def remove_user(sender, **kwargs):
    subscription_user_pk = kwargs.get('subscription_user_pk')
    async_task('extra.djangoapps.freeipa.tasks.remove_user_group', subscription_user_pk)
