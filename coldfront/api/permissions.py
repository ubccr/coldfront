from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import SAFE_METHODS


class IsAdminUserOrReadOnly(IsAuthenticated):
    """
    Allows access only to admin users, or is a read-only request.

    Disallows unauthenticated users.
    """

    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        if not is_authenticated:
            return False
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_staff or
            request.user.is_superuser
        )


class IsSuperuserOrStaff(IsAuthenticated):
    """
    Allows write access to superusers, read access to staff, and no
    access to other users.

    Disallows unauthenticated users.
    """
    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        if not is_authenticated:
            return False
        user = request.user
        if not user:
            return False
        if user.is_superuser:
            return True
        elif user.is_staff:
            return request.method in SAFE_METHODS
        return False
