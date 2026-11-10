from django.contrib import admin
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created", "action", "username", "ip", "detail")
    list_filter = ("action",)
    search_fields = ("username", "ip", "detail", "action")
    date_hierarchy = "created"

    # read-only for everybody, including superusers: a log you can edit is not a log
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
