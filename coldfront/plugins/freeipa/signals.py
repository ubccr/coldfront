# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.dispatch import receiver
from django_q.tasks import async_task

from coldfront.core.allocation.signals import allocation_activate_user, allocation_remove_user
from coldfront.core.allocation.views import AllocationAddUsersView, AllocationRemoveUsersView, AllocationRenewView
from coldfront.core.project.views import ProjectAddUsersView, ProjectRemoveUsersView


@receiver(allocation_activate_user, sender=ProjectAddUsersView)
@receiver(allocation_activate_user, sender=AllocationAddUsersView)
def activate_user(sender, **kwargs):
    allocation_user_pk = kwargs.get("allocation_user_pk")
    async_task("coldfront.plugins.freeipa.tasks.add_user_group", allocation_user_pk)


@receiver(allocation_remove_user, sender=ProjectRemoveUsersView)
@receiver(allocation_remove_user, sender=AllocationRemoveUsersView)
@receiver(allocation_remove_user, sender=AllocationRenewView)
def remove_user(sender, **kwargs):
    allocation_user_pk = kwargs.get("allocation_user_pk")
    async_task("coldfront.plugins.freeipa.tasks.remove_user_group", allocation_user_pk)
