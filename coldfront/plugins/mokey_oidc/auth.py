# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)

PI_GROUP = import_from_settings("MOKEY_OIDC_PI_GROUP", "pi")
ALLOWED_GROUPS = import_from_settings("MOKEY_OIDC_ALLOWED_GROUPS", [])
DENY_GROUPS = import_from_settings("MOKEY_OIDC_DENY_GROUPS", [])


class OIDCMokeyAuthenticationBackend(OIDCAuthenticationBackend):
    def _sync_groups(self, user, groups):
        is_pi = False
        user.groups.clear()
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
            if group_name == PI_GROUP:
                is_pi = True

        user.userprofile.is_pi = is_pi

    def _parse_groups_from_claims(self, claims):
        groups = claims.get("groups", []) or []
        if isinstance(groups, str):
            groups = groups.split(";")

        return groups

    def create_user(self, claims):
        email = claims.get("email")
        username = claims.get("uid")
        if not username:
            logger.error("Failed to create user. username not found in mokey oidc id_token claims: %s", claims)
            return None

        if not email:
            logger.warning(
                "Creating user with no email. Could not find email for user %s in mokey oidc id_token claims: %s",
                username,
                claims,
            )

        user = self.UserModel.objects.create_user(username, email)

        user.first_name = claims.get("first", "")
        user.last_name = claims.get("last", "")

        groups = self._parse_groups_from_claims(claims)
        self._sync_groups(user, groups)

        user.save()

        return user

    def update_user(self, user, claims):
        user.first_name = claims.get("first", "")
        user.last_name = claims.get("last", "")
        email = claims.get("email")
        username = claims.get("uid")
        if email and len(email) > 0:
            user.email = email
        else:
            logger.warning(
                "Failed to update email. Could not find email for user %s in mokey oidc id_token claims: %s",
                username,
                claims,
            )

        groups = self._parse_groups_from_claims(claims)
        self._sync_groups(user, groups)

        user.save()

        return user

    def filter_users_by_claims(self, claims):
        uid = claims.get("uid")
        if not uid:
            return self.UserModel.objects.none()

        try:
            return self.UserModel.objects.filter(username=uid)
        except self.UserModel.DoesNotExist:
            return self.UserModel.objects.none()

    def verify_claims(self, claims):
        verified = super(OIDCMokeyAuthenticationBackend, self).verify_claims(claims)

        if len(ALLOWED_GROUPS) == 0 and len(DENY_GROUPS) == 0:
            return verified and True

        groups = self._parse_groups_from_claims(claims)

        if len(ALLOWED_GROUPS) > 0:
            for g in ALLOWED_GROUPS:
                if g not in groups:
                    return False

        if len(DENY_GROUPS) > 0:
            for g in DENY_GROUPS:
                if g in groups:
                    return False

        return verified and True
