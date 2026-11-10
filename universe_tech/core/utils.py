from django.conf import settings
from django.utils import timezone


def client_ip(request):
    """Real client IP. X-Forwarded-For is only trusted for the number of proxies we really have
    (TRUSTED_PROXY_COUNT), counted from the right, because the left side can be forged by the visitor."""
    remote = request.META.get("REMOTE_ADDR") or None
    n = getattr(settings, "TRUSTED_PROXY_COUNT", 0)
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if n and fwd:
        parts = [p.strip() for p in fwd.split(",") if p.strip()]
        if len(parts) >= n:
            return parts[-n]
    return remote


def today():
    return timezone.localdate()
