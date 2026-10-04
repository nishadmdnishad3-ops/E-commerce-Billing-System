from rest_framework import permissions
from .models import UserProfile


def get_user_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return UserProfile.ROLE_ADMIN
    if hasattr(user, "profile"):
        return user.profile.role
    return UserProfile.ROLE_STAFF


class IsAdminRole(permissions.BasePermission):
    """Allows access only to Admin users."""

    def has_permission(self, request, view):
        return get_user_role(request.user) == UserProfile.ROLE_ADMIN


class IsAccountantOrAdmin(permissions.BasePermission):
    """Allows access to Accountants and Admins."""

    def has_permission(self, request, view):
        role = get_user_role(request.user)
        return role in [UserProfile.ROLE_ADMIN, UserProfile.ROLE_ACCOUNTANT]


class IsStaffOrAbove(permissions.BasePermission):
    """Allows access to authenticated Staff, Accountant, and Admin users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class InvoicePermission(permissions.BasePermission):
    """
    - Read (GET): Staff, Accountant, Admin
    - Create/Edit (POST/PUT/PATCH): Accountant, Admin
    - Delete: Admin only
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = get_user_role(request.user)

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == "DELETE":
            return role == UserProfile.ROLE_ADMIN

        return role in [UserProfile.ROLE_ADMIN, UserProfile.ROLE_ACCOUNTANT]
