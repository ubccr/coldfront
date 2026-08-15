# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.dispatch import Signal

logger = logging.getLogger(__name__)

# Signals the allocation status has changed
allocation_status_change = Signal()

# Signals the allocation change request status has changed
allocation_change_request_status_change = Signal()


def _connect_project_group_signals():  # noqa: N802
    """Connect signals for Project group FK change tracking.

    Imported lazily to avoid circular imports at module level.
    Called from :meth:`RASConfig.ready`.
    """

    from django.db.models.signals import post_save, pre_save
    from django.dispatch import receiver

    from coldfront.ras.models import Project, ProjectUser

    @receiver(pre_save, sender=Project)
    def on_project_pre_save(sender, instance, **kwargs):
        if instance.pk is None:
            return
        try:
            old = Project.objects.get(pk=instance.pk)
            instance._old_group = old.group
        except Project.DoesNotExist:
            pass

    @receiver(post_save, sender=Project)
    def on_project_group_changed(sender, instance, **kwargs):
        old_group = getattr(instance, "_old_group", None)
        new_group = instance.group
        if old_group == new_group:
            return
        for pu in ProjectUser.objects.filter(project=instance):
            if old_group:
                # Only remove from old group if no OTHER project with
                # the same old group still has this user as a member.
                other_projects = Project.objects.filter(
                    group=old_group,
                    users__user=pu.user,
                ).exclude(pk=instance.pk)
                if not other_projects.exists():
                    old_group.remove_member(pu.user)
            if new_group:
                new_group.add_member(pu.user)
