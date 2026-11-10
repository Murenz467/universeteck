"""Helpers for turning a lead (QuoteRequest) into a customer account."""
from django.conf import settings
from django.contrib.auth import get_user_model
from urllib.parse import urlparse
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.text import slugify
from .models import get_profile


def get_or_invite_client(quote_request, request=None):
    """Return the user for a lead, creating an account and emailing a set-password link if needed.

    Returns (user, created)."""
    User = get_user_model()
    if quote_request.user_id:
        return quote_request.user, False
    user = User.objects.filter(email__iexact=quote_request.email).first()
    created = False
    if not user:
        base = slugify(quote_request.email.split("@")[0]) or "client"
        username, n = base, 1
        while User.objects.filter(username=username).exists():
            n += 1
            username = f"{base}{n}"
        first = quote_request.name.split(" ")[0][:60]
        user = User(username=username, email=quote_request.email.lower(), first_name=first)
        user.set_unusable_password()
        user.save()
        p = get_profile(user)
        p.phone, p.company = quote_request.phone, quote_request.company
        p.save()
        created = True
        send_invite(user, first)
    quote_request.user = user
    quote_request.save(update_fields=["user"])
    return user, created


def send_invite(user, name=""):
    """Email a set-password link (Django's own reset form skips accounts that have no password yet)."""
    site = urlparse(settings.SITE_URL)
    ctx = {"user": user, "name": name or user.first_name or user.username, "protocol": site.scheme or "https",
           "domain": site.netloc, "uid": urlsafe_base64_encode(force_bytes(user.pk)),
           "token": default_token_generator.make_token(user)}
    subject = render_to_string("registration/invite_subject.txt", ctx).strip()
    send_mail(subject, render_to_string("registration/invite_email.txt", ctx), settings.DEFAULT_FROM_EMAIL,
              [user.email], fail_silently=True)
