import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Optional local .env file (never commit it). Real environment variables always win.
_env = BASE_DIR / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

TESTING = "test" in sys.argv[1:2]

# SECURE BY DEFAULT: debug mode must be switched on explicitly (DEBUG=1) for local development only.
DEBUG = os.environ.get("DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or TESTING:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production-" + "x" * 20
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY is not set. Generate one with:  python -c \"import secrets; print(secrets.token_urlsafe(64))\"  "
            "and set it as an environment variable. (For local development use DEBUG=1.)")

# Public address of the live site, e.g. https://universetech.rw  (used in emails, robots.txt and canonical links).
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000").rstrip("/")
_site = urlparse(SITE_URL)
_site_host = _site.hostname or ""
_live_site = bool(_site_host) and _site_host not in ("localhost", "127.0.0.1")

_hosts = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
if not _hosts:   # never default to "*": a wrong Host header can poison password-reset links
    _hosts = ["localhost", "127.0.0.1", "[::1]", "testserver"] if (DEBUG or TESTING) else ["localhost", "127.0.0.1"]
    if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
        _hosts.append(os.environ["RAILWAY_PUBLIC_DOMAIN"])
if _live_site:   # the live domain and its www. twin are always allowed, so a typo in ALLOWED_HOSTS cannot take the site down
    _bare = _site_host[4:] if _site_host.startswith("www.") else _site_host
    for _h in (_bare, "www." + _bare):
        if _h not in _hosts:
            _hosts.append(_h)
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    _hosts.append("healthcheck.railway.app")   # Railway checks /healthz with this host name
ALLOWED_HOSTS = _hosts
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    CSRF_TRUSTED_ORIGINS.append("https://" + os.environ["RAILWAY_PUBLIC_DOMAIN"])
if _live_site:
    for _h in (_bare, "www." + _bare):
        _o = f"{_site.scheme}://{_h}"
        if _o not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_o)

# Where the admin lives. Change it (e.g. ADMIN_URL=ut-control-7x2/) to avoid automated scans. Must end with "/".
ADMIN_URL = os.environ.get("ADMIN_URL", "admin/").lstrip("/")
if not ADMIN_URL.endswith("/"):
    ADMIN_URL += "/"

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "django.contrib.humanize", "django.contrib.sitemaps",
    "core.apps.CoreConfig", "services", "quotes", "accounts.apps.AccountsConfig", "portfolio", "projects", "support", "notifications",
    "proposals", "contracts", "billing", "trust",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.security.SecurityHeadersMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.security.StaffGuardMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "notifications.context.unread",
        "core.context.site",
    ]},
}]
DATABASES = {"default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
PASSWORD_HASHERS = [      # Argon2 first; older PBKDF2 hashes are upgraded automatically at next login
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en"
TIME_ZONE = "Africa/Kigali"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_NAME = "Universe Tech"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))   # on Railway: point this at a Volume so uploads survive redeploys
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"
# EMAIL_PROVIDER: console (local, prints emails) | resend | brevo | smtp.
# Railway's Free/Hobby plans block SMTP, so on those use "resend" or "brevo" (they send over HTTPS).
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "console").lower()
ANYMAIL = {}
if EMAIL_PROVIDER == "resend":
    EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
    ANYMAIL = {"RESEND_API_KEY": os.environ.get("RESEND_API_KEY", "")}
elif EMAIL_PROVIDER == "brevo":
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    ANYMAIL = {"BREVO_API_KEY": os.environ.get("BREVO_API_KEY", "")}
elif EMAIL_PROVIDER == "smtp":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
if EMAIL_PROVIDER in ("resend", "brevo"):
    INSTALLED_APPS.append("anymail")      # only needed (and only loaded) when a web email service is used
if not (DEBUG or TESTING) and EMAIL_BACKEND.endswith("console.EmailBackend"):
    print("WARNING: EMAIL_PROVIDER is not set, so emails are only printed in the log and NOT delivered.", file=sys.stderr)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Universe Tech <info@universetech.rw>")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "info@universetech.rw")

# Public contact details shown on the website (contact page, footer, WhatsApp button).
CONTACT = {
    "phone": "+250724685138",               # calls + WhatsApp
    "phone_display": "+250 724 685 138",
    "whatsapp_only": "+250793487065",        # WhatsApp only
    "whatsapp_only_display": "+250 793 487 065",
    "email": os.environ.get("CONTACT_EMAIL", ""),   # shown on the website; set CONTACT_EMAIL=info@universetech.rw once the mailbox exists
    "address": "Gishushu, Gasabo, Kigali, Rwanda",
}


# ---------------------------------------------------------------------------
# Business settings (contracts, invoices, payments)
# ---------------------------------------------------------------------------
COMPANY = {
    "legal_name": os.environ.get("COMPANY_LEGAL_NAME", "Universe Tech"),
    "representative": os.environ.get("COMPANY_REPRESENTATIVE", "Universe Tech Management"),
    "tin": os.environ.get("COMPANY_TIN", ""),          # Rwanda tax number, shown on invoices when set
    "address": CONTACT["address"],
}
# Social media links. All icons are shown in the footer; an icon becomes a clickable link once its address is set
# (FACEBOOK_URL, X_URL, INSTAGRAM_URL, LINKEDIN_URL, YOUTUBE_URL). Until then it is shown greyed out, not clickable.
SOCIAL = [
    ("Facebook", "i-fb", os.environ.get("FACEBOOK_URL", "")),
    ("X", "i-x", os.environ.get("X_URL", "")),
    ("Instagram", "i-ig", os.environ.get("INSTAGRAM_URL", "")),
    ("LinkedIn", "i-in", os.environ.get("LINKEDIN_URL", "")),
    ("YouTube", "i-yt", os.environ.get("YOUTUBE_URL", "")),
]
CURRENCY = "RWF"
INVOICE_DUE_DAYS = int(os.environ.get("INVOICE_DUE_DAYS", "7"))
DEFAULT_DEPOSIT_PERCENT = int(os.environ.get("DEFAULT_DEPOSIT_PERCENT", "40"))
PROPOSAL_VALID_DAYS = int(os.environ.get("PROPOSAL_VALID_DAYS", "14"))

# Where clients pay. Only the entries you set are shown on invoices.
PAYMENT_METHODS = [m for m in [
    ("MTN MoMo", os.environ.get("MOMO_DETAILS", "")),            # e.g. "Pay code 123456 (Universe Tech)"
    ("Airtel Money", os.environ.get("AIRTEL_DETAILS", "")),
    ("Bank transfer", os.environ.get("BANK_DETAILS", "")),       # e.g. "BK 0000-0000000-00, Universe Tech"
] if m[1]]

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")   # Railway & most hosts terminate TLS in front of Django
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = not (DEBUG or TESTING)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_NAME = "ut_session"
SECURE_SSL_REDIRECT = os.environ.get("SSL_REDIRECT", "0" if (DEBUG or TESTING) else "1") == "1"   # on automatically in production
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]
SECURE_HSTS_SECONDS = int(os.environ.get("HSTS_SECONDS", "0"))      # raise to 31536000 once HTTPS is confirmed working
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500

# Number of reverse proxies in front of Django (Railway = 1). Used to find the real client IP safely.
TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "0" if (DEBUG or TESTING) else "1"))

# Content-Security-Policy: scripts only from our own files; no inline scripts.
CSP_REPORT_ONLY = os.environ.get("CSP_REPORT_ONLY", "0") == "1"
CSP = {
    "default-src": "'self'",
    "script-src": "'self'",
    "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src": "'self' https://fonts.gstatic.com",
    "img-src": "'self' data:",
    "frame-src": "https://www.google.com https://maps.google.com",
    "connect-src": "'self'",
    "object-src": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
    "frame-ancestors": "'none'",
}

# Staff protections: two-factor sign-in and idle log-out for anyone who can see other people's data.
STAFF_2FA_REQUIRED = os.environ.get("STAFF_2FA_REQUIRED", "1") == "1" and not TESTING
STAFF_IDLE_MINUTES = int(os.environ.get("STAFF_IDLE_MINUTES", "60"))
STAFF_2FA_HOURS = 12
LOGIN_MAX_FAILURES = 5          # wrong passwords per username+IP before a temporary lock
LOGIN_LOCK_MINUTES = 15

# Shared throttle storage (works across gunicorn workers on one server). Use Redis if you scale to several servers.
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
    "LOCATION": os.environ.get("CACHE_DIR", "/tmp/universe_tech_cache"),
    "TIMEOUT": 3600}}
if TESTING:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
MAX_UPLOAD_MB = 25

LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "std"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}

# Approximate exchange rate used only to show "about US$ ..." next to prices. Update it from time to time.
RWF_PER_USD = int(os.environ.get("RWF_PER_USD", "1450"))
