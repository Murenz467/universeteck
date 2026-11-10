from django import template
from django.conf import settings
from services.models import ServiceCategory
from ..models import Testimonial, ClientLogo, FaqItem

register = template.Library()


@register.inclusion_tag("trust/_testimonials.html")
def testimonials(limit=3):
    items = list(Testimonial.objects.filter(is_published=True)[:limit])
    return {"items": items, "has_sample": any(t.is_sample for t in items)}


@register.inclusion_tag("trust/_logos.html")
def client_logos():
    items = list(ClientLogo.objects.filter(is_published=True)[:12])
    return {"items": items, "has_sample": any(c.is_sample for c in items)}


@register.inclusion_tag("trust/_faq_list.html")
def faq_preview(category="", limit=4):
    qs = FaqItem.objects.filter(is_published=True)
    if category:
        qs = qs.filter(category=category)
    return {"items": list(qs[:limit])}


@register.filter
def usd(rwf):
    """Rough US$ equivalent for international visitors, e.g. 350000 -> 240."""
    try:
        v = int(rwf) / settings.RWF_PER_USD
    except (TypeError, ValueError, ZeroDivisionError):
        return ""
    return int(round(v / 10.0) * 10) if v >= 100 else int(round(v))


@register.inclusion_tag("trust/_footer_services.html")
def footer_services():
    return {"cats": list(ServiceCategory.objects.all()[:6])}
