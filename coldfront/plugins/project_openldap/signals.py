# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Coldfront project_openldap plugin signals.py"""

import logging

from django.dispatch import receiver
from django_q.tasks import async_task

from coldfront.core.project.signals import (
    project_activate_user,
    project_archive,
    project_new,
    project_remove_user,
    project_update,
)
from coldfront.core.project.views import (
    ProjectAddUsersView,
    ProjectArchiveProjectView,
    ProjectCreateView,
    ProjectRemoveUsersView,
    ProjectUpdateView,
)

logger = logging.getLogger(__name__)


# Add a project
@receiver(project_new, sender=ProjectCreateView)
def send_project_new_signal(sender, **kwargs):
    project_obj = kwargs.get("project_obj")
    async_task("coldfront.plugins.project_openldap.tasks.add_project", project_obj)


# Archive a project
@receiver(project_archive, sender=ProjectArchiveProjectView)
def send_project_archive_signal(sender, **kwargs):
    project_obj = kwargs.get("project_obj")
    async_task("coldfront.plugins.project_openldap.tasks.remove_project", project_obj)


# Update a project (title)
@receiver(project_update, sender=ProjectUpdateView)
def send_project_update_signal(sender, **kwargs):
    project_obj = kwargs.get("project_obj")
    async_task("coldfront.plugins.project_openldap.tasks.update_project", project_obj)


# Add project user
@receiver(project_activate_user, sender=ProjectAddUsersView)
def send_project_activate_user_signal(sender, **kwargs):
    project_user_pk = kwargs.get("project_user_pk")
    async_task("coldfront.plugins.project_openldap.tasks.add_user_project", project_user_pk)


# Remove project user
@receiver(project_remove_user, sender=ProjectRemoveUsersView)
def send_project_remove_user_signal(sender, **kwargs):
    project_user_pk = kwargs.get("project_user_pk")
    async_task("coldfront.plugins.project_openldap.tasks.remove_user_project", project_user_pk)
