from django.db.models import Q

from coldfront.core.allocation.models import (AllocationAttributeType,
                                              AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.signals import allocation_activate_user
from coldfront.core.resource.models import Resource


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
        percent = 0

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
            (Q(is_public=True) | Q(allowed_groups__in=user_obj.groups.all()) | Q(allowed_users__in=[user_obj,]))
        ).distinct()

    return resources


def test_allocation_function(allocation_pk):
    pass
    # print('test_allocation_function', allocation_pk)


def get_allocation_user_cluster_access_status(allocation_obj, user_obj):
    return allocation_obj.allocationuserattribute_set.get(
        allocation_user__user=user_obj,
        allocation_attribute_type__name='Cluster Account Status',
        value__in=['Pending - Add', 'Active'])


def request_project_cluster_access(allocation_obj, user_obj):
    allocation_user_active_status_choice = \
        AllocationUserStatusChoice.objects.get(name='Active')
    cluster_access_allocation_attribute_type = \
        AllocationAttributeType.objects.get(name='Cluster Account Status')

    if allocation_obj.allocationuser_set.filter(user=user_obj).exists():
        allocation_user_obj = allocation_obj.allocationuser_set.get(
            user=user_obj)
        allocation_user_obj.status = allocation_user_active_status_choice
        allocation_user_obj.save()
    else:
        allocation_user_obj = AllocationUser.objects.create(
            allocation=allocation_obj, user=user_obj,
            status=allocation_user_active_status_choice)
    allocation_activate_user.send(
        sender=None, allocation_user_pk=allocation_user_obj.pk)

    queryset = allocation_user_obj.allocationuserattribute_set
    cluster_access_status, _ = queryset.get_or_create(
        allocation_attribute_type=(
            cluster_access_allocation_attribute_type),
        allocation=allocation_obj)
    if cluster_access_status.value == 'Active':
        raise ValueError('Cluster access status is already Active.')
    cluster_access_status.value = 'Pending - Add'
    cluster_access_status.save()
