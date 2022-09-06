from datetime import datetime
from django.db.models import Q
from django.urls import reverse

from coldfront.core.allocation.models import (AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import get_domain_url, import_from_settings
from coldfront.core.utils.mail import send_email_template

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings(
        'EMAIL_TICKET_SYSTEM_ADDRESS')
    EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings(
        'EMAIL_OPT_OUT_INSTRUCTION_URL')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')


def set_allocation_user_status_to_error(allocation_user_pk):
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    error_status = AllocationUserStatusChoice.objects.get(name='Error')
    allocation_user_obj.status = error_status
    allocation_user_obj.save()


def generate_guauge_data_from_usage(name, value, usage):

    label = "%s: %.2f of %.2f" % (name, usage, value)

    try:
        percent = (usage/value)*100
    except ZeroDivisionError:
        percent = 100
    except ValueError:
        percent = 100

    if percent < 80:
        color = "#6da04b"
    elif percent >= 80 and percent < 90:
        color = "#ffc72c"
    else:
        color = "#e56a54"

    usage_data = {
        "columns": [
            [label, percent],
        ],
        "type": 'gauge',
        "colors": {
            label: color
        }
    }

    return usage_data


def get_user_resources(user_obj):

    if user_obj.is_superuser:
        resources = Resource.objects.filter(is_allocatable=True)
    else:
        resources = Resource.objects.filter(
            Q(is_allocatable=True) &
            Q(is_available=True) &
            (Q(is_public=True) | Q(allowed_groups__in=user_obj.groups.all()) | Q(allowed_users__in=[user_obj, ]))
        ).distinct()

    return resources


def test_allocation_function(allocation_pk):
    print('test_allocation_function', allocation_pk)


def compute_prorated_amount(total_cost):
    current_date = datetime.now()
    expire_date = datetime(current_date.year, 7, 1)
    if expire_date < current_date:
        expire_date = expire_date.replace(year=expire_date.year + 1)

    difference = abs(expire_date - current_date)
    # Take into account leap years.
    one_year = expire_date - expire_date.replace(year=expire_date.year - 1)
    cost_per_day = total_cost / one_year.days
    return round(cost_per_day * difference.days + cost_per_day)


def send_allocation_user_request_email(request, usernames, parent_resource_name, email_receiver_list):
    if EMAIL_ENABLED:
        domain_url = get_domain_url(request)
        url = '{}{}'.format(domain_url, reverse('allocation-user-request-list'))
        template_context = {
            'center_name': EMAIL_CENTER_NAME,
            'resource': parent_resource_name,
            'url': url,
            'signature': EMAIL_SIGNATURE,
            'users': usernames
        }

        send_email_template(
            'New Allocation User Request(s)',
            'email/new_allocation_user_requests.txt',
            template_context,
            EMAIL_SENDER,
            email_receiver_list
        )


def send_added_user_email(request, allocation_obj, users, users_emails):
    if EMAIL_ENABLED:
        domain_url = get_domain_url(request)
        url = '{}{}'.format(domain_url, reverse('allocation-detail', kwargs={'pk': allocation_obj.pk}))
        template_context = {
            'center_name': EMAIL_CENTER_NAME,
            'resource': allocation_obj.get_parent_resource.name,
            'users': users,
            'project_title': allocation_obj.project.title,
            'url': url,
            'signature': EMAIL_SIGNATURE
        }

        send_email_template(
            'Added to Allocation',
            'email/allocation_added_users.txt',
            template_context,
            EMAIL_TICKET_SYSTEM_ADDRESS,
            [users_emails]
        )


def send_removed_user_email(allocation_obj, users, users_emails):
    if EMAIL_ENABLED:
        template_context = {
            'center_name': EMAIL_CENTER_NAME,
            'resource': allocation_obj.get_parent_resource.name,
            'users': users,
            'project_title': allocation_obj.project.title,
            'signature': EMAIL_SIGNATURE
        }

        send_email_template(
            'Removed From Allocation',
            'email/allocation_removed_users.txt',
            template_context,
            EMAIL_TICKET_SYSTEM_ADDRESS,
            [users_emails]
        )
