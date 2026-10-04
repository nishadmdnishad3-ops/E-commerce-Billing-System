from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
from .models import (
    UserProfile,
    Company,
    BankAccount,
    Settings,
    PaymentMethod,
    Client,
    Service,
    ClientServicePrice,
    InvoiceTemplate,
    Invoice,
    InvoiceItem,
    Payment,
)

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["role", "phone"]


class UserDetailSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_superuser", "role", "phone"]

    def get_role(self, obj):
        if obj.is_superuser:
            return UserProfile.ROLE_ADMIN
        if hasattr(obj, "profile"):
            return obj.profile.role
        return UserProfile.ROLE_STAFF

    def get_phone(self, obj):
        if hasattr(obj, "profile"):
            return obj.profile.phone
        return ""


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = "__all__"


class CompanySerializer(serializers.ModelSerializer):
    bank_accounts = BankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = "__all__"


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = "__all__"


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = "__all__"


class ClientServicePriceSerializer(serializers.ModelSerializer):
    service_name = serializers.ReadOnlyField(source="service.name")

    class Meta:
        model = ClientServicePrice
        fields = "__all__"


class ClientSerializer(serializers.ModelSerializer):
    client_services = ClientServicePriceSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = "__all__"


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"


class InvoiceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = "__all__"


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ["id", "sl", "service", "item_name", "technical_specification", "quantity", "unit_price", "total"]
        read_only_fields = ["total"]


class PaymentSerializer(serializers.ModelSerializer):
    payment_method_name = serializers.ReadOnlyField(source="payment_method.name")

    class Meta:
        model = Payment
        fields = ["id", "invoice", "amount", "payment_date", "payment_method", "payment_method_name", "transaction_id", "note", "created_at"]


class InvoiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "title",
            "billing_month",
            "issue_date",
            "due_date",
            "status",
            "client_name",
            "currency_symbol",
            "sub_total",
            "discount",
            "vat_rate",
            "vat_amount",
            "payable_amount",
            "advance_amount",
            "paid_amount",
            "due_amount",
            "created_at",
        ]


class InvoiceDetailSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    qr_code_url = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    signature_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = "__all__"

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.qr_code.url) if request else obj.qr_code.url
        return None

    def get_logo_url(self, obj):
        if obj.company_logo_snapshot:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.company_logo_snapshot.url) if request else obj.company_logo_snapshot.url
        return None

    def get_signature_url(self, obj):
        if obj.company_signature_snapshot:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.company_signature_snapshot.url) if request else obj.company_signature_snapshot.url
        return None


class InvoiceCreateUpdateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "title",
            "billing_month",
            "issue_date",
            "due_date",
            "status",
            "client",
            "company",
            "bank_account",
            "template",
            "currency_symbol",
            "discount",
            "vat_rate",
            "vat_amount",
            "advance_amount",
            "nb_text",
            "authorization_label",
            "received_by_label",
            "notes",
            "items",
        ]
        read_only_fields = ["invoice_number"]

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        invoice = Invoice.objects.create(**validated_data)

        # Create items
        for idx, item_data in enumerate(items_data, start=1):
            sl = item_data.pop("sl", idx)
            InvoiceItem.objects.create(invoice=invoice, sl=sl, **item_data)

        invoice.calculate_totals()
        Invoice.objects.filter(pk=invoice.pk).update(
            sub_total=invoice.sub_total,
            vat_amount=invoice.vat_amount,
            payable_amount=invoice.payable_amount,
            advance_amount=invoice.advance_amount,
            paid_amount=invoice.paid_amount,
            due_amount=invoice.due_amount,
            status=invoice.status,
        )
        return invoice

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            # Replace or update items
            instance.items.all().delete()
            for idx, item_data in enumerate(items_data, start=1):
                sl = item_data.pop("sl", idx)
                InvoiceItem.objects.create(invoice=instance, sl=sl, **item_data)

        instance.calculate_totals()
        Invoice.objects.filter(pk=instance.pk).update(
            sub_total=instance.sub_total,
            vat_amount=instance.vat_amount,
            payable_amount=instance.payable_amount,
            advance_amount=instance.advance_amount,
            paid_amount=instance.paid_amount,
            due_amount=instance.due_amount,
            status=instance.status,
        )
        return instance
