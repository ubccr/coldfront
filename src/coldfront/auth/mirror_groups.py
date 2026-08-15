# SPDX-FileCopyrightText: (C) Peter Sagerson
#
# SPDX-License-Identifier: BSD-2-Clause

from coldfront.users.models import Group


# Copied from django_auth_ldap.backend._LDAPUser and modified to support our
# custom Group model.
def _mirror_groups(self):
    """
    Mirrors the user's LDAP groups in the Django database and updates the
    user's membership.
    """
    target_group_names = frozenset(self._get_groups().get_group_names())
    current_group_names = frozenset(self._user.groups.values_list("name", flat=True).iterator())

    # These were normalized to sets above.
    MIRROR_GROUPS_EXCEPT = self.settings.MIRROR_GROUPS_EXCEPT
    MIRROR_GROUPS = self.settings.MIRROR_GROUPS

    # If the settings are white- or black-listing groups, we'll update
    # target_group_names such that we won't modify the membership of groups
    # beyond our purview.
    if isinstance(MIRROR_GROUPS_EXCEPT, (set, frozenset)):
        target_group_names = (target_group_names - MIRROR_GROUPS_EXCEPT) | (current_group_names & MIRROR_GROUPS_EXCEPT)
    elif isinstance(MIRROR_GROUPS, (set, frozenset)):
        target_group_names = (target_group_names & MIRROR_GROUPS) | (current_group_names - MIRROR_GROUPS)

    if target_group_names != current_group_names:
        existing_groups = list(Group.objects.filter(name__in=target_group_names).iterator())
        existing_group_names = frozenset(group.name for group in existing_groups)

        new_groups = [
            Group.objects.get_or_create(name=name)[0] for name in target_group_names if name not in existing_group_names
        ]

        self._user.groups.set(existing_groups + new_groups)
