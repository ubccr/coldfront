from datetime import datetime, timedelta

from django.dispatch import receiver

from coldfront.core.allocation.signals import (allocation_activate_user,
                                               allocation_remove_user,
                                               allocation_change_user_role,
                                               allocation_expire, 
                                               allocation_remove,
                                               allocation_activate,
                                               visit_allocation_detail)
from coldfront.core.allocation.views import (AllocationActivateRequestView,
                                             AllocationAddUsersView,
                                             AllocationRemoveUsersView,
                                             AllocationUserDetailView,
                                             AllocationRemoveView,
                                             AllocationApproveRemovalRequestView,
                                             AllocationDetailView)
from coldfront.core.allocation.tasks import update_statuses
from coldfront.core.allocation.models import AllocationUser, Allocation
from coldfront.core.project.views import (ProjectAddUsersView,
                                          ProjectRemoveUsersView)
from coldfront.plugins.slate_project.utils import (add_user_to_slate_project_group,
                                                   remove_user_from_slate_project_group,
                                                   change_users_slate_project_groups,
                                                   add_slate_project_groups,
                                                   send_expiry_email,
                                                   sync_slate_project_users,
                                                   sync_slate_project_ldap_group,
                                                   sync_slate_project_user_statuses)

@receiver(allocation_activate, sender=AllocationDetailView)
@receiver(allocation_activate, sender=AllocationActivateRequestView)
def add_group(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    if not allocation_obj.get_parent_resource.name == 'Slate Project':
        return
    if not allocation_obj.status.name == 'Active':
        return
    
    return
    add_slate_project_groups(allocation_obj)

@receiver(allocation_activate_user, sender=ProjectAddUsersView)
@receiver(allocation_activate_user, sender=AllocationAddUsersView)
def activate_user(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    if not allocation_user_obj.allocation.get_parent_resource.name == 'Slate Project':
        return
    if not allocation_user_obj.allocation.status.name in ['Active', 'Renewal Requested']:
        return
    if not allocation_user_obj.status.name in ['Active', 'Eligible', 'Disabled', 'Retired']:
        return
    add_user_to_slate_project_group(allocation_user_obj)

@receiver(allocation_remove_user, sender=AllocationRemoveUsersView)
@receiver(allocation_remove_user, sender=ProjectRemoveUsersView)
def remove_user(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    if not allocation_user_obj.allocation.get_parent_resource.name == 'Slate Project':
        return
    if not allocation_user_obj.allocation.status.name in ['Active', 'Renewal Requested']:
        return

    remove_user_from_slate_project_group(allocation_user_obj)

@receiver(allocation_change_user_role, sender=AllocationUserDetailView)
def change_user_role(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    if not allocation_user_obj.allocation.get_parent_resource.name == 'Slate Project':
        return
    if not allocation_user_obj.allocation.status.name in ['Active', 'Renewal Requested']:
        return
    if not allocation_user_obj.status.name in ['Active', 'Eligible', 'Disabled', 'Retired']:
        return

    change_users_slate_project_groups(allocation_user_obj)

@receiver(allocation_expire, sender=update_statuses)
def expire(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    if not allocation_obj.get_parent_resource.name == 'Slate Project':
        return
    if not allocation_obj.status.name == 'Expired':
        return

    send_expiry_email(allocation_obj)

@receiver(allocation_remove, sender=AllocationRemoveView)
@receiver(allocation_remove, sender=AllocationApproveRemovalRequestView)
def remove(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    if not allocation_obj.get_parent_resource.name == 'Slate Project':
        return
    if not allocation_obj.status.name == 'Removed':
        return

@receiver(visit_allocation_detail, sender=AllocationDetailView)
def sync_slate_project(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    if not allocation_obj.get_parent_resource.name == 'Slate Project':
        return
    if not allocation_obj.status.name in ['Active', 'Renewal Requested']:
        return

    sync_slate_project_ldap_group(allocation_obj)
    sync_slate_project_users(allocation_obj)

    slate_project_user_objs = AllocationUser.objects.filter(
        allocation = allocation_obj,
        status__name__in=['Active', 'Eligible', 'Disabled', 'Retired'],
        modified__lt = datetime.now() - timedelta(seconds=5)
    ).select_related('user', 'status', 'allocation', 'allocation__project')
    sync_slate_project_user_statuses(slate_project_user_objs)
