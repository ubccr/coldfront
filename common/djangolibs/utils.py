import datetime
# import the logging library
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from core.djangoapps.subscription.models import (Subscription,
                                                 SubscriptionStatusChoice)

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


def get_domain_url(request):
    return request.build_absolute_uri().replace(request.get_full_path(), '')


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value
