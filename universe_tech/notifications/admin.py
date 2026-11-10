from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "message", "is_read", "created")
    list_filter = ("is_read", "kind")
    search_fields = ("message", "user__username", "user__email")
