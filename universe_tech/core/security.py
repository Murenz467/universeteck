"""Security middleware: response headers (CSP etc.), staff two-factor enforcement, idle log-out, no-store caching."""
import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.utils.http import urlencode

PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
PRIVATE_PREFIXES = ("/accounts/", "/proposals/", "/contracts/", "/billing/", "/projects/", "/support/",
                    "/notifications/", "/staff/")


def _csp_header():
    return "; ".join(f"{k} {v}" for k, v in settings.CSP.items())


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.csp = _csp_header()
        self.csp_name = "Content-Security-Policy-Report-Only" if settings.CSP_REPORT_ONLY else "Content-Security-Policy"

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault(self.csp_name, self.csp)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        path = request.path
        if path.startswith("/" + settings.ADMIN_URL) or path.startswith(PRIVATE_PREFIXES):
            add_never_cache_headers(response)           # never let browsers/proxies keep private pages
            response.headers["Cache-Control"] = "no-store, private, max-age=0"
        return response


class StaffGuardMiddleware:
    """For staff accounts: log out after STAFF_IDLE_MINUTES of inactivity, and require a two-factor code
    before they can open the admin, the staff dashboard or any page that shows other clients' data."""

    def __init__(self, get_response):
        self.get_response = get_response
        admin = "/" + settings.ADMIN_URL
        self.protected = (admin, "/staff/", "/proposals/", "/contracts/", "/billing/", "/projects/")
        self.exempt = (admin + "login/", admin + "logout/", "/accounts/2fa/", "/accounts/logout/")

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and user.is_staff:
            now = time.time()
            last = request.session.get("ut_last")
            if last and now - last > settings.STAFF_IDLE_MINUTES * 60:
                logout(request)
                return redirect(f"{reverse('login')}?{urlencode({'next': request.path})}")
            request.session["ut_last"] = now
            path = request.path
            if (settings.STAFF_2FA_REQUIRED and path.startswith(self.protected)
                    and not path.startswith(self.exempt) and not self.two_factor_ok(request)):
                return redirect(f"{reverse('two_factor')}?{urlencode({'next': request.get_full_path()})}")
        return self.get_response(request)

    @staticmethod
    def two_factor_ok(request):
        data = request.session.get("ut_2fa")
        return bool(data and data.get("uid") == request.user.pk
                    and time.time() - data.get("at", 0) < settings.STAFF_2FA_HOURS * 3600)
