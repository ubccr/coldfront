# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from collections import defaultdict

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, Subquery
from django.utils.translation import gettext_lazy as _

from coldfront.users.constants import CONSTRAINT_TOKEN_USER
from coldfront.users.models import ObjectPermission
from coldfront.users.permissions import (
    permission_is_exempt,
    qs_filter_from_constraints,
    resolve_permission,
)

__all__ = ("ObjectPermissionMixin", "ObjectPermissionRequiredMixin")


class ObjectPermissionMixin:
    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous:
            return dict()
        if not hasattr(user_obj, "_object_perm_cache"):
            user_obj._object_perm_cache = self.get_object_permissions(user_obj)
        return user_obj._object_perm_cache

    def get_permission_filter(self, user_obj):
        # Include permissions assigned via roles (both direct user roles and group-inherited roles)
        return Q(users=user_obj) | Q(groups__user=user_obj) | Q(roles__users=user_obj) | Q(roles__groups__user=user_obj)

    def get_object_permissions(self, user_obj):
        """
        Return all permissions granted to the user by an ObjectPermission.
        """
        # Initialize a dictionary mapping permission names to sets of constraints
        perms = defaultdict(list)

        # Collect any configured default permissions
        for perm_name, constraints in settings.DEFAULT_PERMISSIONS.items():
            constraints = constraints or tuple()
            if type(constraints) not in (list, tuple):
                raise ImproperlyConfigured(
                    f"Constraints for default permission {perm_name} must be defined as a list or tuple."
                )
            perms[perm_name].extend(constraints)

        # Retrieve all assigned and enabled ObjectPermissions
        object_permissions = (
            ObjectPermission.objects.filter(
                id__in=Subquery(
                    ObjectPermission.objects.filter(self.get_permission_filter(user_obj), enabled=True)
                    .values("id")
                    .distinct()
                )
            )
            .order_by("id")
            .prefetch_related("object_types")
        )

        # Create a dictionary mapping permissions to their constraints
        for obj_perm in object_permissions:
            for object_type in obj_perm.object_types.all():
                for action in obj_perm.actions:
                    perm_name = f"{object_type.app_label}.{action}_{object_type.model}"
                    perms[perm_name].extend(obj_perm.list_constraints())

        return perms

    def has_perm(self, user_obj, perm, obj=None):
        app_label, __, model_name = resolve_permission(perm)

        # Superusers implicitly have all permissions
        if user_obj.is_active and user_obj.is_superuser:
            return True

        # Permission is exempt from enforcement (i.e. listed in EXEMPT_VIEW_PERMISSIONS)
        if permission_is_exempt(perm):
            return True

        # Handle inactive/anonymous users
        if not user_obj.is_active or user_obj.is_anonymous:
            return False

        object_permissions = self.get_all_permissions(user_obj)

        # If no applicable ObjectPermissions have been created for this user/permission, deny permission
        if perm not in object_permissions:
            return False

        # If no object has been specified, grant permission. (The presence of a permission in this set tells
        # us that the user has permission for *some* objects, but not necessarily a specific object.)
        if obj is None:
            return True

        # Sanity check: Ensure that the requested permission applies to the specified object
        model = obj._meta.concrete_model
        if model._meta.label_lower != ".".join((app_label, model_name)):
            raise ValueError(
                _("Invalid permission {permission} for model {model}").format(permission=perm, model=model)
            )

        # Compile a QuerySet filter that matches all instances of the specified model
        tokens = {
            CONSTRAINT_TOKEN_USER: user_obj,
        }
        qs_filter = qs_filter_from_constraints(object_permissions[perm], tokens)

        # Permission to perform the requested action on the object depends on whether the specified object matches
        # the specified constraints. Note that this check is made against the *database* record representing the object,
        # not the instance itself.
        return model.objects.filter(qs_filter, pk=obj.pk).exists()


class ObjectPermissionRequiredMixin(LoginRequiredMixin):
    """
    Similar to Django's built-in PermissionRequiredMixin, but extended to check for both model-level and object-level
    permission assignments. If the user has only object-level permissions assigned, the view's queryset is filtered
    to return only those objects on which the user is permitted to perform the specified action.

    additional_permissions: An optional iterable of statically declared permissions to evaluate in addition to those
                            derived from the object type
    """

    additional_permissions = list()

    def get_required_permission(self):
        """
        Return the specific permission necessary to perform the requested action on an object.
        """
        raise NotImplementedError(
            _("{class_name} must implement get_required_permission()").format(class_name=self.__class__.__name__)
        )

    def has_permission(self):
        user = self.request.user
        permission_required = self.get_required_permission()

        # Check that the user has been granted the required permission(s).
        if user.has_perms((permission_required, *self.additional_permissions)):
            # Update the view's QuerySet to filter only the permitted objects
            action = resolve_permission(permission_required)[1]
            self.queryset = self.queryset.restrict(user, action)

            return True

        return False

    def dispatch(self, request, *args, **kwargs):

        if not hasattr(self, "queryset"):
            raise ImproperlyConfigured(
                _(
                    "{class_name} has no queryset defined. ObjectPermissionRequiredMixin may only be used on views "
                    "which define a base queryset"
                ).format(class_name=self.__class__.__name__)
            )

        if not self.has_permission():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)
