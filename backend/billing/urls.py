from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    LogoutView,
    CurrentUserView,
    ChangePasswordView,
    UserManagementViewSet,
    AuditLogViewSet,
    CompanyViewSet,
    BankAccountViewSet,
    SettingsViewSet,
    PaymentMethodViewSet,
    ClientViewSet,
    ServiceViewSet,
    ClientServicePriceViewSet,
    InvoiceTemplateViewSet,
    InvoiceViewSet,
    InvoiceItemViewSet,
    PaymentViewSet,
)

router = DefaultRouter()
router.register(r"users", UserManagementViewSet, basename="user")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")
router.register(r"companies", CompanyViewSet, basename="company")
router.register(r"bank-accounts", BankAccountViewSet, basename="bank-account")
router.register(r"settings", SettingsViewSet, basename="settings")
router.register(r"payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"client-services", ClientServicePriceViewSet, basename="client-service")
router.register(r"templates", InvoiceTemplateViewSet, basename="template")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"invoice-items", InvoiceItemViewSet, basename="invoice-item")
router.register(r"payments", PaymentViewSet, basename="payment")

urlpatterns = [
    # Auth endpoints
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="token_logout"),
    path("auth/me/", CurrentUserView.as_view(), name="current_user"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),

    # REST APIs
    path("", include(router.urls)),
]
