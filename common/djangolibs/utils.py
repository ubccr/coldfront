from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import datetime
from core.djangoapps.subscription.models import Subscription, SubscriptionStatusChoice
# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


def import_from_settings(attr, *args):
    """
    Load an attribute from the django settings.
    :raises:
        ImproperlyConfigured
    src: https://github.com/mozilla/mozilla-django-oidc
    """
    try:
        if args:
            return getattr(settings, attr, args[0])
        return getattr(settings, attr)
    except AttributeError:
        raise ImproperlyConfigured('Setting {0} not found'.format(attr))


def update_statuses():

    number_expired = Subscription.objects.filter(
        status__name='Active', active_until__lt=datetime.datetime.now().date()).update(
        status=SubscriptionStatusChoice.objects.get(name='Expired'))

    logger.info('Subscriptions set to expired: {}'.format(number_expired))
