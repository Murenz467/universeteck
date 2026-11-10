import hashlib
import json
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from core.audit import record
from core.ratelimit import blocked_response, clear, count, hit
from . import totp
from .models import StaffTOTP


def _hash(code):
    return hashlib.sha256(code.strip().replace("-", "").replace(" ", "").lower().encode()).hexdigest()


def make_recovery_codes(n=8):
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]
    return codes, json.dumps([_hash(c) for c in codes])


def mark_verified(request):
    request.session.cycle_key()
    request.session["ut_2fa"] = {"uid": request.user.pk, "at": time.time()}


def _next(request):
    n = request.POST.get("next") or request.GET.get("next") or ""
    return n if n and url_has_allowed_host_and_scheme(n, allowed_hosts={request.get_host()}) else "/staff/"


@login_required
def two_factor(request):
    """One URL for both steps: first-time setup (scan QR, confirm a code) and normal verification."""
    if not request.user.is_staff:
        return redirect("dashboard")
    device, _ = StaffTOTP.objects.get_or_create(user=request.user, defaults={"secret": totp.new_secret()})
    ident = str(request.user.pk)
    ctx = {"next": _next(request), "setup": not device.confirmed}

    if request.method == "POST":
        if count("2fa", ident) >= 5:
            return blocked_response(request, 600)
        code = request.POST.get("code", "")
        ok, step = False, totp.verify(device.secret, code, device.last_step)
        if step:
            device.last_step, ok = step, True
        elif device.confirmed:                                # a recovery code instead of an app code
            hashes = json.loads(device.recovery_hashes or "[]")
            if _hash(code) in hashes and len(code.strip()) >= 12:
                hashes.remove(_hash(code))
                device.recovery_hashes, ok = json.dumps(hashes), True
                record(request, "2fa_recovery_code_used", detail=f"{len(hashes)} codes left")
        if ok:
            clear("2fa", ident)
            first_time = not device.confirmed
            device.confirmed = True
            codes = None
            if first_time:
                codes, device.recovery_hashes = make_recovery_codes()
            device.save()
            mark_verified(request)
            record(request, "2fa_enabled" if first_time else "2fa_ok")
            if codes:        # show recovery codes once, then continue
                return render(request, "accounts/2fa_codes.html", {"codes": codes, "next": ctx["next"]})
            return redirect(ctx["next"])
        hit("2fa", ident, 600)
        record(request, "2fa_failed")
        messages.error(request, "That code is not valid. Check the time on your phone and try again.")

    if ctx["setup"]:
        import segno
        uri = totp.provisioning_uri(device.secret, request.user.email or request.user.username)
        ctx.update(secret=" ".join(device.secret[i:i + 4] for i in range(0, len(device.secret), 4)),
                   qr=segno.make(uri, error="m").svg_inline(scale=5, dark="#04462e", border=2, omitsize=False))
    return render(request, "accounts/2fa.html", ctx)
