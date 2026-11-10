from django.contrib import admin
from .models import ServiceCategory, Service

class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0
    prepopulated_fields = {"slug": ("name",)}

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceInline]
