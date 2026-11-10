import logging
from .utils import client_ip

log = logging.getLogger("ut.security")


def record(request, action, user=None, detail="", username=""):
    """Write a security event to the database and the application log. Never raises."""
    from .models import AuditEvent
    try:
        user = user or (getattr(request, "user", None) if request is not None else None)
        if user is not None and not getattr(user, "is_authenticated", False):
            user = None
        ip = client_ip(request) if request is not None else None
        AuditEvent.objects.create(user=user, username=(username or getattr(user, "username", ""))[:150],
                                  action=action, ip=ip, detail=detail[:300])
        log.info("%s user=%s ip=%s %s", action, username or getattr(user, "username", "-"), ip, detail)
    except Exception:
        log.exception("could not write audit event %s", action)
