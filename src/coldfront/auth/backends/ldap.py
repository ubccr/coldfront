# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils.module_loading import import_string

from coldfront.auth.mirror_groups import _mirror_groups
from coldfront.auth.mixins import ObjectPermissionMixin

# Create a new instance of django-auth-ldap's LDAPBackend with our own ObjectPermissions
try:
    from django_auth_ldap.backend import LDAPBackend as LDAPBackend_
    from django_auth_ldap.backend import _LDAPUser

    class ColdFrontLDAPBackend(ObjectPermissionMixin, LDAPBackend_):
        def get_permission_filter(self, user_obj):
            permission_filter = super().get_permission_filter(user_obj)
            if (
                self.settings.FIND_GROUP_PERMS
                and hasattr(user_obj, "ldap_user")
                and hasattr(user_obj.ldap_user, "group_names")
            ):
                permission_filter = permission_filter | Q(groups__name__in=user_obj.ldap_user.group_names)
            return permission_filter

    # Patch with our modified _mirror_groups() method to support our custom Group model
    _LDAPUser._mirror_groups = _mirror_groups

except ModuleNotFoundError:
    pass


class LDAPBackend:
    _required_settings = ("AUTH_LDAP_SERVER_URI",)

    def __new__(cls, *args, **kwargs):
        try:
            import ldap
            from django_auth_ldap.config import LDAPSearch
        except ModuleNotFoundError as e:
            if getattr(e, "name") == "ldap":
                raise ImproperlyConfigured("LDAP authentication has been configured, but ldap is not installed.")
            elif getattr(e, "name") == "django_auth_ldap":
                raise ImproperlyConfigured(
                    "LDAP authentication has been configured, but django-auth-ldap is not installed."
                )
            raise e

        for s in cls._required_settings:
            if not hasattr(settings, s):
                raise ImproperlyConfigured(f"Required parameter {s} is missing from settings")

        obj = ColdFrontLDAPBackend()

        scope = ldap.SCOPE_SUBTREE if settings.LDAP_SEARCH_SCOPE.lower() == "subtree" else ldap.SCOPE_ONELEVEL
        if not obj.settings.USER_SEARCH:
            obj.settings.USER_SEARCH = LDAPSearch(
                settings.LDAP_USER_SEARCH_BASE, scope, settings.LDAP_USER_SEARCH_QUERY
            )

        if not obj.settings.GROUP_SEARCH:
            obj.settings.GROUP_SEARCH = LDAPSearch(
                settings.LDAP_GROUP_SEARCH_BASE, scope, settings.LDAP_GROUP_SEARCH_QUERY
            )

        if settings.LDAP_GROUP_TYPE:
            try:
                group_type = import_string(f"django_auth_ldap.config.{settings.LDAP_GROUP_TYPE}")
                obj.settings.GROUP_TYPE = group_type()
            except ImportError:
                raise ImproperlyConfigured(
                    "LDAP authentication configuration error, LDAP_GROUP_TYPE is not a valid group type."
                )

        # Optionally disable strict certificate checking
        if getattr(settings, "LDAP_IGNORE_CERT_ERRORS", False):
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        # Optionally set CA cert directory
        if ca_cert_dir := getattr(settings, "LDAP_CA_CERT_DIR", None):
            ldap.set_option(ldap.OPT_X_TLS_CACERTDIR, ca_cert_dir)

        # Optionally set CA cert file
        if ca_cert_file := getattr(settings, "LDAP_CA_CERT_FILE", None):
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, ca_cert_file)

        return obj
