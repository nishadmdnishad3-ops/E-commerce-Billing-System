from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from billing.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds initial Admin, Accountant, and Staff users with verified UserProfiles"

    def handle(self, *args, **options):
        # 1. Admin
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@raktch.com", "first_name": "System", "last_name": "Admin", "is_staff": True, "is_superuser": True}
        )
        admin_user.set_password("admin123")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_active = True
        admin_user.save()
        UserProfile.objects.update_or_create(
            user=admin_user,
            defaults={"role": UserProfile.ROLE_ADMIN, "phone": "+8801581677077"}
        )
        self.stdout.write(self.style.SUCCESS("Admin user: username='admin', password='admin123', role='ADMIN'"))

        # 2. Accountant
        acc_user, created = User.objects.get_or_create(
            username="accountant",
            defaults={"email": "accountant@raktch.com", "first_name": "Senior", "last_name": "Accountant"}
        )
        acc_user.set_password("accountant123")
        acc_user.is_active = True
        acc_user.save()
        UserProfile.objects.update_or_create(
            user=acc_user,
            defaults={"role": UserProfile.ROLE_ACCOUNTANT, "phone": "+8801700000001"}
        )
        self.stdout.write(self.style.SUCCESS("Accountant user: username='accountant', password='accountant123', role='ACCOUNTANT'"))

        # 3. Staff
        staff_user, created = User.objects.get_or_create(
            username="staff",
            defaults={"email": "staff@raktch.com", "first_name": "Billing", "last_name": "Staff"}
        )
        staff_user.set_password("staff123")
        staff_user.is_active = True
        staff_user.save()
        UserProfile.objects.update_or_create(
            user=staff_user,
            defaults={"role": UserProfile.ROLE_STAFF, "phone": "+8801700000002"}
        )
        self.stdout.write(self.style.SUCCESS("Staff user: username='staff', password='staff123', role='STAFF'"))
