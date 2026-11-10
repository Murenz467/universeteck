from django.contrib import admin
from django.urls import reverse
from notifications.utils import notify
from .models import Ticket, TicketMessage

class MessageInline(admin.StackedInline):
    model = TicketMessage
    extra = 1
    fields = ("body", "author", "is_staff", "created")
    readonly_fields = ("author", "is_staff", "created")

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "client", "status", "updated")
    list_filter = ("status",)
    search_fields = ("subject", "client__username", "client__email")
    inlines = [MessageInline]

    def save_formset(self, request, form, formset, change):
        if formset.model is not TicketMessage:
            return super().save_formset(request, form, formset, change)
        replied = False
        for obj in formset.save(commit=False):
            if obj.pk is None and obj.body.strip():
                obj.author, obj.is_staff = request.user, True
                obj.save()
                replied = True
        for obj in formset.deleted_objects:
            obj.delete()
        if replied:
            t = form.instance
            if t.status != "closed":
                t.status = "answered"
                t.save()
            notify(t.client, f"New reply on your ticket: {t.subject}",
                   reverse("ticket", args=[t.pk]), subject=f"Re: {t.subject}", kind="support", button="Read the reply")
