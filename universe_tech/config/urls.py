from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.views.static import serve
from core.ratelimit import lockout_login
from core.sitemaps import SITEMAPS

admin.site.site_header = "Universe Tech Admin"
admin.site.site_title = "Universe Tech"

urlpatterns = [
    path(f"{settings.ADMIN_URL}login/", lockout_login(admin.site.login)),   # brute-force lock on the admin too
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("core.urls")),
    path("", include("trust.urls")),
    path("services/", include("services.urls")),
    path("quote/", include("quotes.urls")),
    path("portfolio/", include("portfolio.urls")),
    path("projects/", include("projects.urls")),
    path("proposals/", include("proposals.urls")),
    path("contracts/", include("contracts.urls")),
    path("billing/", include("billing.urls")),
    path("accounts/", include("accounts.urls")),
    path("support/", include("support.urls")),
    path("notifications/", include("notifications.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    # Only portfolio and trust (logos, client photos) images are public. Client files (deliverables, attachments) are served by
    # permission-checked views, never directly from /media/.
    re_path(r"^media/(?P<path>(?:portfolio|trust)/.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
