from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'

    def ready(self):
        # Ensure the built-in demo roles exist automatically after migrations.
        post_migrate.connect(self._ensure_demo_users, sender=self.__class__)

    def _ensure_demo_users(self, sender, **kwargs):
        User = get_user_model()
        from .models import UserProfile

        demo_users = [
            ("admin", "admin123", True, UserProfile.ROLE_ADMIN, "+8801581677077"),
            ("accountant", "accountant123", False, UserProfile.ROLE_ACCOUNTANT, "+8801700000001"),
            ("staff", "staff123", False, UserProfile.ROLE_STAFF, "+8801700000002"),
        ]

        for username, password, is_superuser, role, phone in demo_users:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@raktch.com",
                    "first_name": "System" if username == "admin" else "Demo",
                    "last_name": "Admin" if username == "admin" else "User",
                    "is_active": True,
                    "is_staff": is_superuser,
                    "is_superuser": is_superuser,
                },
            )
            user.set_password(password)
            user.is_active = True
            user.is_staff = user.is_staff or is_superuser
            user.is_superuser = user.is_superuser or is_superuser
            user.save(update_fields=["password", "is_active", "is_staff", "is_superuser"])
            UserProfile.objects.update_or_create(
                user=user,
                defaults={"role": role, "phone": phone},
            )
