from django.contrib import admin
from .models import Testimonial, ClientLogo, FaqItem, PricingPackage


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "rating", "is_sample", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("is_sample", "is_published")


@admin.register(ClientLogo)
class ClientLogoAdmin(admin.ModelAdmin):
    list_display = ("name", "website", "is_sample", "is_published", "order")
    list_editable = ("is_published", "order")


@admin.register(FaqItem)
class FaqAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("category", "is_published")
    search_fields = ("question", "answer")


@admin.register(PricingPackage)
class PricingPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "price_from", "billing", "is_featured", "is_published", "order")
    list_editable = ("is_published", "order")
