import datetime
# import the logging library
import logging
import pytz

from datetime import datetime

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from django_q.models import Schedule

from urllib.parse import urljoin

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


def project_detail_url(project):
    domain = import_from_settings('CENTER_BASE_URL')
    view = reverse('project-detail', kwargs={'pk': project.pk})
    return urljoin(domain, view)


class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def su_login_callback(user):
    """Only superusers are allowed to login as other users
    """
    if user.is_active and user.is_superuser:
        return True

    logger.warn(
        'User {} requested to login as another user but does not have permissions', user)
    return False


def add_argparse_dry_run_argument(parser):
    """Add an optional argument '--dry_run' to the given argparse parser
    to indicate that the corresponding action will display would-be
    updates instead of performing them."""
    parser.add_argument(
        '--dry_run',
        action='store_true',
        help='Display updates without performing them.')


def assert_obj_type(obj, expected_obj_type, null_allowed=False):
    """Raise an AssertionError if the given object does not have the
    given type. If null_allowed is True, do nothing if the object is
    None."""
    if null_allowed and obj is None:
        return
    message = f'{obj} does not have type {expected_obj_type}.'
    assert isinstance(obj, expected_obj_type), message


def delete_scheduled_tasks(func, *args):
    """Delete scheduled tasks (Schedule objects) for running the given
    function with the given arguments. Write a message to the log."""
    scheduled_tasks = Schedule.objects.filter(func=func, args=args)
    num_scheduled_tasks = scheduled_tasks.count()
    if num_scheduled_tasks:
        scheduled_tasks.delete()
        message = (
            f'Deleted {num_scheduled_tasks} scheduled tasks for running '
            f'{func}({", ".join(str(arg) for arg in args)}).')
        logger.info(message)


def display_time_zone_current_date():
    """Return the current date in settings.DISPLAY_TIME_ZONE."""
    return utc_now_offset_aware().astimezone(
        pytz.timezone(settings.DISPLAY_TIME_ZONE)).date()


def display_time_zone_date_to_utc_datetime(date):
    """Return the given date, interpreted as being in
    settings.DISPLAY_TIME_ZONE, as a datetime object in the UTC
    timezone.

    Source: https://stackoverflow.com/a/25390097
    """
    dt_tz_unaware = datetime.combine(date, datetime.min.time())
    display_tz = pytz.timezone(settings.DISPLAY_TIME_ZONE)
    dt_display_tz = display_tz.localize(dt_tz_unaware)
    return pytz.utc.normalize(dt_display_tz)


def format_date_month_name_day_year(date):
    """Return a string of the form "Month Day, Year" for the given
    date (i.e., June 1, 2022)."""
    return date.strftime('%B %-d, %Y')


def session_wizard_all_form_data(submitted_forms_list, step_num_to_data,
                                 total_num_forms):
    """Given a list of user-submitted forms, a mapping from step number
    (str) to user-submitted data, and the total number of possible
    forms, return a list of dictionaries containing data for each step,
    including empty dictionaries for skipped steps.

    This is a utility method for children of SessionWizardView.

    Parameters:
        - submitted_forms_list: A list of user-submitted forms
        - step_num_to_data: A mapping from step number (str) to the
                            user-submitted data from that step's form
        - total_num_forms: The total number of possible forms

    Returns: list(dict)

    Raises: None.
    """
    data = iter([form.cleaned_data for form in submitted_forms_list])
    all_form_data = [{} for _ in range(total_num_forms)]
    for step in sorted(step_num_to_data.keys()):
        all_form_data[int(step)] = next(data)
    return all_form_data


def utc_now_offset_aware():
    """Return the offset-aware current UTC time."""
    return datetime.utcnow().replace(tzinfo=pytz.utc)


def validate_num_service_units(num_service_units):
    """Raise exceptions if the given number of service units does
    not conform to the expected constraints."""
    if not isinstance(num_service_units, Decimal):
        raise TypeError(
            f'Number of service units {num_service_units} is not a Decimal.')
    minimum, maximum = settings.ALLOCATION_MIN, settings.ALLOCATION_MAX
    if not (minimum <= num_service_units <= maximum):
        raise ValueError(
            f'Number of service units {num_service_units} is not in the '
            f'acceptable range [{minimum}, {maximum}].')
    num_service_units_tuple = num_service_units.as_tuple()
    max_digits = settings.DECIMAL_MAX_DIGITS
    if len(num_service_units_tuple.digits) > max_digits:
        raise ValueError(
            f'Number of service units {num_service_units} has greater than '
            f'{max_digits} digits.')
    max_places = settings.DECIMAL_MAX_PLACES
    if abs(num_service_units_tuple.exponent) > max_places:
        raise ValueError(
            f'Number of service units {num_service_units} has greater than '
            f'{max_places} decimal places.')
