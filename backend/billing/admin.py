from django.contrib import admin
from django.utils.html import format_html
from .models import (
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


class BankAccountInline(admin.TabularInline):
    model = BankAccount
    extra = 1
    fields = ["bank_name", "account_name", "account_number", "branch_name", "routing_number", "is_default", "is_active"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "email", "website", "is_default", "logo_preview"]
    search_fields = ["name", "email", "phone"]
    inlines = [BankAccountInline]

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height: 35px; border-radius: 4px;" />', obj.logo.url)
        return "-"
    logo_preview.short_description = "Logo"


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ["bank_name", "account_name", "account_number", "branch_name", "routing_number", "company", "is_default", "is_active"]
    list_filter = ["company", "is_default", "is_active", "bank_name"]
    search_fields = ["bank_name", "account_name", "account_number", "branch_name"]


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ["currency_symbol", "currency_code", "default_company", "default_bank_account"]

    def has_add_permission(self, request):
        # Allow only 1 global setting instance
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    list_filter = ["is_active"]


class ClientServicePriceInline(admin.TabularInline):
    model = ClientServicePrice
    extra = 1
    autocomplete_fields = ["service"]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_person", "phone", "email", "is_active", "created_at"]
    search_fields = ["name", "contact_person", "phone", "email"]
    list_filter = ["is_active"]
    inlines = [ClientServicePriceInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "default_price", "billing_cycle", "is_active"]
    search_fields = ["name", "code"]
    list_filter = ["billing_cycle", "is_active"]


@admin.register(ClientServicePrice)
class ClientServicePriceAdmin(admin.ModelAdmin):
    list_display = ["client", "service", "custom_price", "is_active"]
    list_filter = ["is_active", "service"]
    search_fields = ["client__name", "service__name"]


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "invoice_number_prefix", "title_pattern", "is_default"]
    list_filter = ["is_default"]


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ["sl", "service", "item_name", "technical_specification", "quantity", "unit_price", "total"]
    readonly_fields = ["total"]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ["amount", "payment_date", "payment_method", "transaction_id", "note"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "title",
        "client_name",
        "billing_month",
        "payable_amount",
        "paid_amount",
        "due_amount",
        "status",
        "issue_date",
    ]
    list_filter = ["status", "issue_date", "company"]
    search_fields = ["invoice_number", "title", "client_name", "client__name"]
    inlines = [InvoiceItemInline, PaymentInline]
    date_hierarchy = "issue_date"
    readonly_fields = [
        "invoice_number",
        "sub_total",
        "payable_amount",
        "paid_amount",
        "due_amount",
        "qr_code_preview",
    ]

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "invoice_number",
                "title",
                "billing_month",
                "issue_date",
                "due_date",
                "status",
                "template",
            )
        }),
        ("Entities", {
            "fields": (
                "company",
                "client",
                "bank_account",
            )
        }),
        ("Calculations & Currency", {
            "fields": (
                "currency_symbol",
                "sub_total",
                "discount",
                "payable_amount",
                "paid_amount",
                "due_amount",
            )
        }),
        ("Invoice Content & Labels", {
            "fields": (
                "nb_text",
                "authorization_label",
                "received_by_label",
                "notes",
                "qr_code_preview",
            )
        }),
        ("Company Snapshot (Historical Freeze)", {
            "classes": ("collapse",),
            "fields": (
                "company_name",
                "company_tagline",
                "company_address",
                "company_website",
                "company_email",
                "company_phone",
                "company_logo_snapshot",
                "company_signature_snapshot",
            )
        }),
        ("Client Snapshot (Historical Freeze)", {
            "classes": ("collapse",),
            "fields": (
                "client_name",
                "client_contact_person",
                "client_address",
                "client_phone",
                "client_email",
            )
        }),
        ("Bank Details Snapshot (Historical Freeze)", {
            "classes": ("collapse",),
            "fields": (
                "bank_name",
                "account_name",
                "account_number",
                "branch_name",
                "routing_number",
            )
        }),
    )

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" style="height: 100px; width: 100px;" />', obj.qr_code.url)
        return "Will be generated on save"
    qr_code_preview.short_description = "QR Code"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["invoice", "amount", "payment_date", "payment_method", "transaction_id"]
    list_filter = ["payment_date", "payment_method"]
    search_fields = ["invoice__invoice_number", "transaction_id"]
