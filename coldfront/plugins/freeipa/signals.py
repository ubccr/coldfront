from django.dispatch import receiver
from django_q.tasks import async_task

from coldfront.core.allocation.signals import (allocation_activate_user,
                                               allocation_remove_user)
from coldfront.core.allocation.views import (AllocationActivateRequestView,
                                             AllocationAddUsersView,
                                             AllocationRemoveUsersView,
                                             AllocationRenewView)
from coldfront.core.project.views import (ProjectAddUsersView,
                                          ProjectRemoveUsersView)
from coldfront.core.utils.common import import_from_settings


@receiver(allocation_activate_user, sender=ProjectAddUsersView)
@receiver(allocation_activate_user, sender=AllocationActivateRequestView)
@receiver(allocation_activate_user, sender=AllocationAddUsersView)
def activate_user(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    async_task('coldfront.plugins.freeipa.tasks.add_user_group',
               allocation_user_pk)


@receiver(allocation_remove_user, sender=ProjectRemoveUsersView)
@receiver(allocation_remove_user, sender=AllocationRemoveUsersView)
@receiver(allocation_remove_user, sender=AllocationRenewView)
def remove_user(sender, **kwargs):
    allocation_user_pk = kwargs.get('allocation_user_pk')
    async_task('coldfront.plugins.freeipa.tasks.remove_user_group',
               allocation_user_pk)
