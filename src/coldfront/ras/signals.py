# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging
from datetime import timedelta

from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.context import current_request
from coldfront.ras.models import Project, ProjectInvite, ProjectUser
from coldfront.utils.email import send_email_template

logger = logging.getLogger(__name__)

# Signals the allocation status has changed
allocation_status_change = Signal()

# Signals the allocation change request status has changed
allocation_change_request_status_change = Signal()


@receiver(pre_save, sender=Project)
def on_project_pre_save(sender, instance, **kwargs):
    """Signals for Project group FK change tracking."""
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


@receiver(post_save, sender=ProjectInvite)
def on_project_invite_created(sender, instance, created, **kwargs):
    """Sends the invite email (with the raw, non-persisted token) when a new invite is created, whether via the add form, bulk import, or quick add."""
    if not created:
        return

    request = current_request.get()
    if request is None:
        return

    # The raw token is only present on a freshly-created instance.
    token = instance.get_raw_token()
    if not token:
        logger.error("No raw token available for invite %s; email not sent", instance.pk)
        return

    subject = _("You have been invited to join a project")
    invite_path = reverse("ras:accept_invite", kwargs={"code": token})
    accept_url = request.build_absolute_uri(invite_path)
    context = {
        "project": instance.project,
        "expire_date": instance.created + timedelta(seconds=settings.INVITE_CODE_EXPIRE_SECONDS),
        "invite": instance,
        "button_link": accept_url,
        "attributes": {
            "Project": instance.project.name,
        },
    }

    try:
        send_email_template(context, "project_invite", subject, [instance.email])
    except Exception:
        logger.exception("Failed to send invite email for %s", instance.email)
