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
        return bool(request.user and request.user.is_authenticated and get_user_role(request.user) == UserProfile.ROLE_ADMIN)


class IsAccountantOrAdmin(permissions.BasePermission):
    """Allows access to Accountants and Admins."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = get_user_role(request.user)
        return role in [UserProfile.ROLE_ADMIN, UserProfile.ROLE_ACCOUNTANT]


class IsStaffOrAbove(permissions.BasePermission):
    """Allows access to authenticated Staff, Accountant, and Admin users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class SettingsAndCompanyPermission(permissions.BasePermission):
    """
    - SAFE_METHODS (GET): Any authenticated user (Staff, Accountant, Admin)
    - Modify (POST, PUT, PATCH, DELETE): Admin only
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return get_user_role(request.user) == UserProfile.ROLE_ADMIN


class PaymentPermission(permissions.BasePermission):
    """
    - SAFE_METHODS (GET): Any authenticated user
    - Create (POST): Accountant or Admin
    - Update (PUT, PATCH): Accountant or Admin
    - Delete (DELETE): Accountant or Admin (STAFF cannot delete payment)
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        role = get_user_role(request.user)
        return role in [UserProfile.ROLE_ADMIN, UserProfile.ROLE_ACCOUNTANT]


class InvoicePermission(permissions.BasePermission):
    """
    - SAFE_METHODS (GET): Any authenticated user
    - Delete (DELETE): Admin only
    - Create (POST): Staff (Draft only), Accountant, Admin
    - Update (PUT, PATCH): Accountant, Admin (Staff cannot edit non-draft or cancel invoices)
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = get_user_role(request.user)

        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == "DELETE":
            return role == UserProfile.ROLE_ADMIN

        if request.method == "POST":
            # Staff can create DRAFT only (validated in serializer/perform_create)
            return role in [UserProfile.ROLE_ADMIN, UserProfile.ROLE_ACCOUNTANT, UserProfile.ROLE_STAFF]

        return role in [UserProfile.ROLE_ADMIN, UserProfile.ROLE_ACCOUNTANT]

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        role = get_user_role(request.user)
        if request.method == "DELETE":
            return role == UserProfile.ROLE_ADMIN

        if role == UserProfile.ROLE_STAFF:
            # Staff can only edit DRAFT invoices and cannot change status to CANCELLED or ISSUED
            if obj.status != "DRAFT":
                return False
            req_status = request.data.get("status")
            if req_status and req_status != "DRAFT":
                return False
            return True

        return role in [UserProfile.ROLE_ADMIN, UserProfile.ROLE_ACCOUNTANT]
