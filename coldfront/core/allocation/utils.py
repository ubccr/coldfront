from datetime import datetime
from django.db.models import Q
from django.urls import reverse
from django.forms.models import model_to_dict
from django.contrib.auth.models import Permission

from coldfront.core.allocation.models import (AllocationUser,
                                              AllocationUserStatusChoice,
                                              AllocationStatusChoice,
                                              AllocationAdminAction)
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
            users_emails
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
            users_emails
        )


def create_admin_action(user, fields_to_check, allocation, base_model=None):
    if base_model is None:
        base_model = allocation
    base_model_dict = model_to_dict(base_model)

    for key, value in fields_to_check.items():
        base_model_value = base_model_dict.get(key)
        if type(value) is not type(base_model_value):
            if key == 'status':
                status_class = base_model._meta.get_field('status').remote_field.model
                base_model_value = status_class.objects.get(pk=base_model_value).name
                value = value.name
        if value != base_model_value:
            AllocationAdminAction.objects.create(
                user=user,
                allocation=allocation,
                action=f'Changed "{key}" from "{base_model_value}" to "{value}" for "{base_model}"'
            )


def create_admin_action_for_deletion(user, deleted_obj, allocation, base_model=None):
    if base_model:
        AllocationAdminAction.objects.create(
            user=user,
            allocation=allocation,
            action=f'Deleted "{deleted_obj}" from "{base_model}" in "{allocation}"'
        )
    else:
        AllocationAdminAction.objects.create(
            user=user,
            allocation=allocation,
            action=f'Deleted "{deleted_obj}" from "{allocation}"'
        )


def create_admin_action_for_creation(user, created_obj, allocation, base_model=None):
    if base_model:
        AllocationAdminAction.objects.create(
            user=user,
            allocation=allocation,
            action=f'Created "{created_obj}" in "{base_model}" in "{allocation}"'
        )
    else:
        AllocationAdminAction.objects.create(
            user=user,
            allocation=allocation,
            action=f'Created "{created_obj}" in "{allocation}"'
        )


def update_linked_allocation_attribute(allocation_attribute):
    """
    Checks if an allocation attribute's type is linked to the allocation attribute and assigns the
    allocation attribute the new value.

    :param allocation_attribute: The allocation attribute that is being created/modified
    """
    linked_allocation_attribute = allocation_attribute.allocation_attribute_type.linked_allocation_attribute
    allocation_obj = allocation_attribute.allocation
    if hasattr(allocation_obj, linked_allocation_attribute):
        setattr(allocation_obj, linked_allocation_attribute, allocation_attribute.value)
        allocation_obj.save()


def get_project_managers_in_allocation(allocation_obj):
    """
    Returns the project managers in the given allocation.

    :param allocation_obj: The allocation to grab the project managers from
    """
    project_managers_in_allocation=[]
    project_managers = allocation_obj.project.projectuser_set.filter(
        role__name='Manager'
    ).exclude(status__name__in=['Removed', 'Denied'])
    allocation_users = allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error'])
    users = [allocation_user.user for allocation_user in allocation_users]
    for project_manager in project_managers:
        if project_manager.user in users:
            project_managers_in_allocation.append(project_manager)

    return project_managers_in_allocation


def check_if_groups_in_review_groups(review_groups, groups, permission=None):
    """
    Returns True if at least one group in a group query is included in a review group query. An
    additional permission can be given to check if at least one matching group has it. Since this
    is for determining permissions this returns True if the review group query is empty, meaning
    open to all groups.

    :param review_groups: The review group query to compare the groups to
    :param groups: The group query being compared
    :param permission: A permission at least one matching group should have
    """
    if not review_groups.exists():
        return True

    if not groups.exists():
        return False

    matched_groups = groups.intersection(review_groups)
    if matched_groups.exists():
        if permission is None:
            return True

        matched_group_ids = matched_groups.values_list('id', flat=True)
        permission_exists = Permission.objects.filter(
            group__id__in=matched_group_ids, codename=permission
        ).exists()
        if permission_exists:
            return True

    return False