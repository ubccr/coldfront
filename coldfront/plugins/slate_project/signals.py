from django.dispatch import receiver

from coldfront.core.allocation.signals import (allocation_activate_user,
                                               allocation_remove_user,
                                               allocation_change_user_role,
                                               allocation_expire, 
                                               allocation_remove)
from coldfront.core.allocation.views import (AllocationActivateRequestView,
                                             AllocationAddUsersView,
                                             AllocationRemoveUsersView,
                                             AllocationUserDetailView,
                                             AllocationRemoveView,
                                             AllocationApproveRemovalRequestView)
from coldfront.core.allocation.models import AllocationUser, Allocation
from coldfront.core.project.views import (ProjectAddUsersView,
                                          ProjectRemoveUsersView)
from coldfront.plugins.slate_project.utils import (add_user_to_ldap,
                                                   remove_user_from_ldap,
                                                   change_user_role_in_ldap)

@receiver(allocation_activate_user, sender=ProjectAddUsersView)
@receiver(allocation_activate_user, sender=AllocationActivateRequestView)
@receiver(allocation_activate_user, sender=AllocationAddUsersView)
def activate_user(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    if not allocation_user_obj.allocation.status.name == 'Active':
        return
    if allocation_user_obj.status.name != 'Active':
        return
    add_user_to_ldap(allocation_user_obj)

@receiver(allocation_remove_user, sender=AllocationRemoveUsersView)
@receiver(allocation_remove_user, sender=ProjectRemoveUsersView)
def remove_user(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    if not allocation_user_obj.allocation.status.name == 'Active':
        return

    remove_user_from_ldap(allocation_user_obj)

@receiver(allocation_change_user_role, sender=AllocationUserDetailView)
def change_user_role(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    if not allocation_user_obj.allocation.status.name == 'Active':
        return

    if allocation_user_obj.status.name != 'Active':
        return

    change_user_role_in_ldap(allocation_user_obj)

@receiver(allocation_expire, sender='update_statuses')
def expire(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    if not allocation_obj.status.name == 'Expired':
        return
    
    allocation_user_objs = allocation_obj.allocationuser_set.filter(status__name='Active')
    for allocation_user_obj in allocation_user_objs:
        remove_user_from_ldap(allocation_user_obj)

@receiver(allocation_remove, sender=AllocationRemoveView)
@receiver(allocation_remove, sender=AllocationApproveRemovalRequestView)
def remove(sender, **kwargs):
    allocation_pk = kwargs.get('allocation_pk')
    allocation_obj = Allocation.objects.get(pk=allocation_pk)
    if not allocation_obj.status.name == 'Removed':
        return

    allocation_user_objs = allocation_obj.allocationuser_set.filter(status__name='Active')
    for allocation_user_obj in allocation_user_objs:
        remove_user_from_ldap(allocation_user_obj)