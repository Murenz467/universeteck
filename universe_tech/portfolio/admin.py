from django.contrib import admin
from .models import CaseStudy

@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ("title", "client_name", "category", "is_published", "order")
    prepopulated_fields = {"slug": ("title",)}
