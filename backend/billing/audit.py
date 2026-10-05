from .models import AuditLog


def get_client_ip(request):
    if not request:
        return ""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def record_audit_log(
    action: str,
    request=None,
    user=None,
    model_name: str = "",
    object_id: str = "",
    object_repr: str = "",
    changes: dict = None,
    ip_address: str = None,
    username: str = None,
):
    try:
        actor = user or (request.user if request and hasattr(request, "user") and request.user.is_authenticated else None)
        uname = username or (actor.username if actor else "Anonymous")
        ip = ip_address or get_client_ip(request)

        return AuditLog.objects.create(
            user=actor if actor and getattr(actor, "is_authenticated", False) else None,
            username=uname,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else "",
            object_repr=str(object_repr)[:255] if object_repr else "",
            changes=changes or {},
            ip_address=ip or "",
        )
    except Exception as e:
        # Never break main transaction for audit log failures
        import logging
        logging.getLogger(__name__).warning("Failed to record audit log: %s", e)
        return None
