# import the logging library
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

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


def get_domain_url(request):
    return request.build_absolute_uri().replace(request.get_full_path(), '')


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value

def uniques_and_intersection(list1, list2):
    intersection = list(set(list1) & set(list2))
    list1_unique = list(set(list1) - set(list2))
    list2_unique = list(set(list2) - set(list1))
    return (list1_unique, intersection, list2_unique)

def su_login_callback(user):
    """Only superusers are allowed to login as other users
    """
    if user.is_active and user.is_superuser:
        return True

    logger.warning(
        'User %s requested to login as another user but does not have permissions', user)
    return False
