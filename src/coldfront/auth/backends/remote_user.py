# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import logging

from django.conf import settings
from django.contrib.auth.backends import RemoteUserBackend as _RemoteUserBackend
from django.contrib.auth.models import AnonymousUser

from coldfront.users.models import Group, ObjectPermission, User
from coldfront.users.permissions import (
    resolve_permission_type,
)


class RemoteUserBackend(_RemoteUserBackend):
    """
    Custom implementation of Django's RemoteUserBackend which provides configuration hooks for basic customization.
    """

    @property
    def create_unknown_user(self):
        return settings.REMOTE_AUTH_AUTO_CREATE_USER

    def configure_groups(self, user, remote_groups):
        logger = logging.getLogger("coldfront.auth.RemoteUserBackend")

        # Assign default groups to the user
        group_list = []
        for name in remote_groups:
            try:
                group_list.append(Group.objects.get(name=name))
            except Group.DoesNotExist:
                if settings.REMOTE_AUTH_AUTO_CREATE_GROUPS:
                    group_list.append(Group.objects.create(name=name))
                else:
                    logging.error(
                        f"Could not assign group {name} to remotely-authenticated user {user}: Group not found"
                    )
        if group_list:
            user.groups.set(group_list)
            logger.debug(f"Assigned groups to remotely-authenticated user {user}: {group_list}")
        else:
            user.groups.clear()
            logger.debug(f"Stripping user {user} from Groups")

        # Evaluate superuser status
        user.is_superuser = self._is_superuser(user)
        logger.debug(f"User {user} is Superuser: {user.is_superuser}")
        logger.debug(f"User {user} should be Superuser: {self._is_superuser(user)}")

        user.save()
        return user

    def authenticate(self, request, remote_user, remote_groups=None):
        """
        The username passed as ``remote_user`` is considered trusted. Return
        the ``User`` object with the given username. Create a new ``User``
        object if ``create_unknown_user`` is ``True``.
        Return None if ``create_unknown_user`` is ``False`` and a ``User``
        object with the given username is not found in the database.
        """
        logger = logging.getLogger("coldfront.auth.RemoteUserBackend")
        logger.debug(f"trying to authenticate {remote_user} with groups {remote_groups}")
        if not remote_user:
            return None
        user = None
        username = self.clean_username(remote_user)

        # Note that this could be accomplished in one try-except clause, but
        # instead we use get_or_create when creating unknown users since it has
        # built-in safeguards for multiple threads.
        if self.create_unknown_user:
            user, created = User._default_manager.get_or_create(**{User.USERNAME_FIELD: username})
            if created:
                user = self.configure_user(request, user)
        else:
            try:
                user = User._default_manager.get_by_natural_key(username)
            except User.DoesNotExist:
                pass
        if self.user_can_authenticate(user):
            if settings.REMOTE_AUTH_GROUP_SYNC_ENABLED:
                if user is not None and not isinstance(user, AnonymousUser):
                    return self.configure_groups(user, remote_groups)
            else:
                return user
        return None

    def _is_superuser(self, user):
        logger = logging.getLogger("coldfront.auth.RemoteUserBackend")
        superuser_groups = settings.REMOTE_AUTH_SUPERUSER_GROUPS
        logger.debug(f"Superuser Groups: {superuser_groups}")
        superusers = settings.REMOTE_AUTH_SUPERUSERS
        logger.debug(f"Superuser Users: {superusers}")
        user_groups = set()
        for g in user.groups.all():
            user_groups.add(g.name)
        logger.debug(f"User {user.username} is in Groups:{user_groups}")

        result = user.username in superusers or (set(user_groups) & set(superuser_groups))
        logger.debug(f"User {user.username} in Superuser Users :{result}")
        return bool(result)

    def _is_staff(self, user):
        # Retain for pre-v4.5 compatibility
        return user.is_superuser

    def configure_user(self, request, user):
        logger = logging.getLogger("coldfront.auth.RemoteUserBackend")
        if not settings.REMOTE_AUTH_GROUP_SYNC_ENABLED:
            # Assign default groups to the user
            group_list = []
            for name in settings.REMOTE_AUTH_DEFAULT_GROUPS:
                try:
                    group_list.append(Group.objects.get(name=name))
                except Group.DoesNotExist:
                    logging.error(
                        f"Could not assign group {name} to remotely-authenticated user {user}: Group not found"
                    )
            if group_list:
                user.groups.add(*group_list)
                logger.debug(f"Assigned groups to remotely-authenticated user {user}: {group_list}")

            # Assign default object permissions to the user
            permissions_list = []
            for permission_name, constraints in settings.REMOTE_AUTH_DEFAULT_PERMISSIONS.items():
                try:
                    object_type, action = resolve_permission_type(permission_name)
                    # TODO: Merge multiple actions into a single ObjectPermission per object type
                    obj_perm = ObjectPermission(actions=[action], constraints=constraints)
                    obj_perm.save()
                    obj_perm.users.add(user)
                    obj_perm.object_types.add(object_type)
                    permissions_list.append(permission_name)
                except ValueError:
                    logging.error(
                        f"Invalid permission name: '{permission_name}'. Permissions must be in the form "
                        "<app>.<action>_<model>. (Example: ras.add_project)"
                    )
            if permissions_list:
                logger.debug(f"Assigned permissions to remotely-authenticated user {user}: {permissions_list}")
        else:
            logger.debug(
                f"Skipped initial assignment of permissions and groups to remotely-authenticated user {user} as "
                f"Group sync is enabled"
            )

        return user

    def has_perm(self, user_obj, perm, obj=None):
        return False
