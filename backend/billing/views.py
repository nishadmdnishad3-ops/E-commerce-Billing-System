from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from decimal import Decimal
from django.shortcuts import get_object_or_404

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
from .serializers import (
    UserDetailSerializer,
    CompanySerializer,
    BankAccountSerializer,
    SettingsSerializer,
    PaymentMethodSerializer,
    ClientSerializer,
    ServiceSerializer,
    ClientServicePriceSerializer,
    InvoiceTemplateSerializer,
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceCreateUpdateSerializer,
    InvoiceItemSerializer,
    PaymentSerializer,
)
from .permissions import IsAdminRole, IsAccountantOrAdmin, IsStaffOrAbove, InvoicePermission
from .filters import InvoiceFilter, ClientFilter, PaymentFilter


class CurrentUserView(APIView):
    """Returns details and role for the currently logged in user"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsStaffOrAbove()]
        return [IsAdminRole()]


class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsStaffOrAbove()]
        return [IsAccountantOrAdmin()]


class SettingsViewSet(viewsets.ModelViewSet):
    queryset = Settings.objects.all()
    serializer_class = SettingsSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsStaffOrAbove()]
        return [IsAdminRole()]


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsStaffOrAbove]


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().prefetch_related("client_services__service")
    serializer_class = ClientSerializer
    filterset_class = ClientFilter
    search_fields = ["name", "contact_person", "phone", "email"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsStaffOrAbove()]
        return [IsAccountantOrAdmin()]


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    search_fields = ["name", "code"]
    ordering_fields = ["name", "default_price"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsStaffOrAbove()]
        return [IsAccountantOrAdmin()]


class ClientServicePriceViewSet(viewsets.ModelViewSet):
    queryset = ClientServicePrice.objects.select_related("client", "service")
    serializer_class = ClientServicePriceSerializer
    filterset_fields = ["client", "service", "is_active"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsStaffOrAbove()]
        return [IsAccountantOrAdmin()]


class InvoiceTemplateViewSet(viewsets.ModelViewSet):
    queryset = InvoiceTemplate.objects.all()
    serializer_class = InvoiceTemplateSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsStaffOrAbove()]
        return [IsAccountantOrAdmin()]


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("client", "company", "bank_account", "template").prefetch_related("items", "payments")
    filterset_class = InvoiceFilter
    search_fields = ["invoice_number", "title", "client_name", "company_name"]
    ordering_fields = ["issue_date", "due_date", "payable_amount", "due_amount", "created_at"]
    ordering = ["-issue_date", "-id"]
    permission_classes = [InvoicePermission]

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return InvoiceCreateUpdateSerializer
        return InvoiceDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance
        detail_serializer = InvoiceDetailSerializer(instance, context=self.get_serializer_context())
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        detail_serializer = InvoiceDetailSerializer(instance, context=self.get_serializer_context())
        return Response(detail_serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAccountantOrAdmin])
    def record_payment(self, request, pk=None):
        invoice = self.get_object()
        amount = request.data.get("amount")
        payment_method_id = request.data.get("payment_method")
        note = request.data.get("note", "")
        transaction_id = request.data.get("transaction_id", "")
        payment_date = request.data.get("payment_date", timezone.now().date())

        if not amount:
            return Response({"error": "Payment amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount_dec = Decimal(str(amount))
            if amount_dec <= 0:
                raise ValueError
        except Exception:
            return Response({"error": "Invalid payment amount"}, status=status.HTTP_400_BAD_REQUEST)

        payment_method = None
        if payment_method_id:
            payment_method = PaymentMethod.objects.filter(id=payment_method_id).first()

        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount_dec,
            payment_date=payment_date,
            payment_method=payment_method,
            transaction_id=transaction_id,
            note=note,
        )

        invoice.refresh_from_db()
        return Response({
            "message": "Payment recorded successfully",
            "payment": PaymentSerializer(payment).data,
            "invoice": InvoiceDetailSerializer(invoice, context={"request": request}).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAccountantOrAdmin])
    def recalculate(self, request, pk=None):
        invoice = self.get_object()
        invoice.calculate_totals()
        invoice.save()
        return Response(InvoiceDetailSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["get"], permission_classes=[IsStaffOrAbove])
    def download_pdf(self, request, pk=None):
        from django.http import HttpResponse
        from .pdf_service import generate_invoice_pdf
        invoice = self.get_object()
        pdf_bytes = generate_invoice_pdf(invoice)
        filename = f"Invoice_{invoice.invoice_number or invoice.id}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["get"], permission_classes=[IsStaffOrAbove])
    def preview_pdf(self, request, pk=None):
        from django.http import HttpResponse
        from .pdf_service import generate_invoice_pdf
        invoice = self.get_object()
        pdf_bytes = generate_invoice_pdf(invoice)
        filename = f"Invoice_{invoice.invoice_number or invoice.id}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response

    @action(detail=False, methods=["post"], permission_classes=[IsAccountantOrAdmin])
    def generate_monthly_bills(self, request):
        """Batch-generate bills for all clients with subscribed services for a given month"""
        billing_month = request.data.get("billing_month")  # e.g. "May-2026"
        if not billing_month:
            return Response({"error": "billing_month is required (e.g. 'May-2026')"}, status=status.HTTP_400_BAD_REQUEST)

        company = Company.objects.filter(is_default=True).first() or Company.objects.first()
        bank_account = BankAccount.objects.filter(is_default=True, is_active=True).first() or BankAccount.objects.first()
        template = InvoiceTemplate.objects.filter(is_default=True).first() or InvoiceTemplate.objects.first()

        if not company:
            return Response({"error": "Please configure a Company before generating bills."}, status=status.HTTP_400_BAD_REQUEST)

        created_invoices = []
        clients = Client.objects.filter(is_active=True).prefetch_related("client_services__service")

        for client in clients:
            subscriptions = client.client_services.filter(is_active=True)
            if not subscriptions.exists():
                continue

            # Check if invoice already exists for this client and month
            if Invoice.objects.filter(client=client, billing_month=billing_month).exists():
                continue

            first_sub = subscriptions.first()
            service_name = first_sub.custom_name or first_sub.service.name
            title = f"{service_name} Monthly Bill ({billing_month})"

            invoice = Invoice.objects.create(
                title=title,
                billing_month=billing_month,
                client=client,
                company=company,
                bank_account=bank_account,
                template=template,
                status="ISSUED",
                issue_date=timezone.now().date(),
            )

            for idx, sub in enumerate(subscriptions, start=1):
                item_name = f"{idx}. {sub.custom_name or sub.service.name} ({billing_month})"
                spec = sub.custom_tech_specification or sub.service.default_tech_specification
                price = sub.custom_price or sub.service.default_price

                InvoiceItem.objects.create(
                    invoice=invoice,
                    sl=idx,
                    service=sub.service,
                    item_name=item_name,
                    technical_specification=spec,
                    quantity=Decimal("1.00"),
                    unit_price=price,
                    total=price,
                )

            invoice.calculate_totals()
            invoice.save()
            created_invoices.append(invoice.invoice_number)

        return Response({
            "message": f"Successfully generated {len(created_invoices)} bills for {billing_month}",
            "generated_invoices": created_invoices,
        }, status=status.HTTP_201_CREATED)


class InvoiceItemViewSet(viewsets.ModelViewSet):
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [IsAccountantOrAdmin]


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("invoice", "invoice__client", "payment_method")
    serializer_class = PaymentSerializer
    filterset_class = PaymentFilter
    ordering = ["-payment_date", "-id"]
    permission_classes = [IsAccountantOrAdmin]

    @action(detail=True, methods=["get"], permission_classes=[IsStaffOrAbove])
    def download_receipt(self, request, pk=None):
        from django.http import HttpResponse
        from .pdf_service import generate_money_receipt_pdf
        payment = self.get_object()
        pdf_bytes = generate_money_receipt_pdf(payment)
        filename = f"Money_Receipt_{payment.receipt_number}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["get"], permission_classes=[IsStaffOrAbove])
    def preview_receipt(self, request, pk=None):
        from django.http import HttpResponse
        from .pdf_service import generate_money_receipt_pdf
        payment = self.get_object()
        pdf_bytes = generate_money_receipt_pdf(payment)
        filename = f"Money_Receipt_{payment.receipt_number}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response

