from urllib.parse import quote_plus
from django.conf import settings


def site(request):
    c = dict(settings.CONTACT)
    c["phone_digits"] = c["phone"].lstrip("+")
    c["whatsapp_only_digits"] = c["whatsapp_only"].lstrip("+")
    c["map_embed"] = f"https://www.google.com/maps?q={quote_plus(c['address'])}&output=embed"
    c["map_link"] = f"https://www.google.com/maps/search/?api=1&query={quote_plus(c['address'])}"
    c["social"] = settings.SOCIAL
    c["url"] = settings.SITE_URL
    c["payment_names"] = [m[0] for m in settings.PAYMENT_METHODS] or ["MTN MoMo", "Airtel Money", "Bank transfer"]
    return {"site": c}
