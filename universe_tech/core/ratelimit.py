"""Small cache-based throttling: per-IP / per-user limits and login lock-outs. No extra packages needed."""
import functools
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render
from .utils import client_ip


def _key(scope, ident):
    return f"rl:{scope}:{ident}"


def count(scope, ident):
    return cache.get(_key(scope, ident), 0)


def hit(scope, ident, window):
    k = _key(scope, ident)
    if cache.add(k, 1, window):
        return 1
    try:
        return cache.incr(k)
    except ValueError:
        cache.set(k, 1, window)
        return 1


def clear(scope, ident):
    cache.delete(_key(scope, ident))


def blocked_response(request, retry_after=60):
    resp = render(request, "429.html", status=429)
    resp["Retry-After"] = str(retry_after)
    return resp


def ratelimit(scope, limit, window, by="ip", methods=("POST",)):
    """Allow `limit` requests per `window` seconds, then answer 429. by="ip" or "user"."""
    def deco(view):
        @functools.wraps(view)
        def wrapped(request, *a, **kw):
            if request.method in methods:
                ident = client_ip(request) if by == "ip" or not request.user.is_authenticated else request.user.pk
                if hit(scope, ident, window) > limit:
                    return blocked_response(request, window)
            return view(request, *a, **kw)
        return wrapped
    return deco


def lockout_login(view):
    """Wrap a login view: after LOGIN_MAX_FAILURES wrong passwords for one username+IP the account is locked
    for LOGIN_LOCK_MINUTES, and one IP is limited overall so passwords cannot be sprayed across many usernames."""
    window = settings.LOGIN_LOCK_MINUTES * 60

    @functools.wraps(view)
    def wrapped(request, *a, **kw):
        if request.method != "POST":
            return view(request, *a, **kw)
        ip = client_ip(request)
        who = f"{ip}|{request.POST.get('username', '').strip().lower()[:150]}"
        if count("login", who) >= settings.LOGIN_MAX_FAILURES or count("login-ip", ip) >= settings.LOGIN_MAX_FAILURES * 6:
            from .audit import record
            record(request, "login_blocked", username=request.POST.get("username", "")[:150])
            return blocked_response(request, window)
        resp = view(request, *a, **kw)
        if resp.status_code == 200:                    # form re-displayed with errors = failed attempt
            hit("login", who, window)
            hit("login-ip", ip, window)
        elif 300 <= resp.status_code < 400:
            clear("login", who)
        return resp
    return wrapped
