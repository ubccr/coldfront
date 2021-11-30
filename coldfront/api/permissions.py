from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminUserOrReadOnly(BasePermission):
    """
    Allows access only to admin users, or is a read-only request.
    """

    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_staff or
            request.user.is_superuser
        )


class IsSuperuserOrStaff(BasePermission):
    """
    Allows write access to superusers, read access to staff, and no
    access to other users.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user:
            return False
        if user.is_superuser:
            return True
        elif user.is_staff:
            return request.method in SAFE_METHODS
        return False
