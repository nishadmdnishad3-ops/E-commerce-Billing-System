from rest_framework.views import exception_handler
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, ProtectedError):
        return Response(
            {
                "error": "Cannot delete this record because other records (such as invoices or client pricing) depend on it. Please delete the dependent records first."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError) and response is None:
        return Response(
            {"error": "Database integrity constraint violated."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return response
