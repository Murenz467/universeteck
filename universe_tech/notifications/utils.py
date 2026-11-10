import logging
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from .models import Notification

log = logging.getLogger(__name__)


def _wants_email(user):
    p = getattr(user, "profile", None)
    return bool(user.email) and (p.email_notifications if p else True)


def _send(to, subject, message, url="", button="Open", force=True):
    subject = " ".join(str(subject).split())[:200]      # one line only: blocks email header injection
    link = f"{settings.SITE_URL}{url}" if url else ""
    ctx = {"subject": subject, "message": message, "link": link, "button": button, "site": settings.SITE_NAME}
    try:
        mail = EmailMultiAlternatives(subject, message + (f"\n\n{link}" if link else ""),
                                      settings.DEFAULT_FROM_EMAIL, to)
        mail.attach_alternative(render_to_string("emails/notification.html", ctx), "text/html")
        mail.send(fail_silently=True)
    except Exception:  # never let an email problem break a request
        log.exception("Could not send email %r", subject)


def notify(user, message, url="", subject=None, kind="system", button="Open"):
    """In-app alert for the user, plus an email copy unless they switched emails off."""
    Notification.objects.create(user=user, message=message[:240], url=url, kind=kind)
    if _wants_email(user):
        _send([user.email], subject or "Universe Tech update", message, url, button)


def notify_once(user, message, url="", within_days=3, **kw):
    """Like notify(), but skipped if the same message was already sent recently (used by reminders)."""
    since = timezone.now() - timedelta(days=within_days)
    if Notification.objects.filter(user=user, message=message[:240], created__gte=since).exists():
        return False
    notify(user, message, url, **kw)
    return True


def notify_staff(subject, body, url=None, kind="system"):
    """Alert every active staff member in-app and email the company inbox."""
    url = url or reverse("staff_dashboard")
    staff = list(get_user_model().objects.filter(is_staff=True, is_active=True))
    for u in staff:
        Notification.objects.create(user=u, message=subject[:240], url=url, kind=kind)
    recipients = {settings.NOTIFY_EMAIL} | {u.email for u in staff if u.email}
    _send(sorted(r for r in recipients if r), subject, body, url, "Open in dashboard")
