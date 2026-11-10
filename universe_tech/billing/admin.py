from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from .models import Invoice, InvoiceItem
from . import services
from notifications.utils import notify


class ItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "client", "status", "total_display", "due_date", "overdue")
    list_filter = ("status", "kind")
    search_fields = ("number", "title", "client__username", "client__email", "payment_reference")
    inlines = [ItemInline]
    actions = ["send_invoices", "confirm_paid", "send_reminders"]
    readonly_fields = ("number", "submitted_at", "paid_at", "last_reminder", "client_view")
    fieldsets = (
        (None, {"fields": ("number", "client", "project", "kind", "title", "status", "issue_date", "due_date",
                           "notes", "client_view")}),
        ("Payment", {"fields": ("payment_method", "payment_reference", "submitted_at", "paid_at", "last_reminder")}),
    )

    @admin.display(description="Total")
    def total_display(self, obj):
        return f"{obj.total:,} RWF"

    @admin.display(boolean=True, description="Overdue")
    def overdue(self, obj):
        return obj.is_overdue

    @admin.display(description="Client view")
    def client_view(self, obj):
        if not obj.pk:
            return "Save first, then preview here."
        return format_html('<a href="{}" target="_blank">Preview exactly what the client sees →</a>',
                           reverse("invoice", args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        became = "status" in form.changed_data and obj.status in ("sent", "paid")
        self._target = obj.status if became else None
        if became:      # the notification is sent after the line items are saved (see save_related)
            obj.status = Invoice.objects.get(pk=obj.pk).status if change else "draft"
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        target, self._target = getattr(self, "_target", None), None
        if target:
            (services._issue if target == "sent" else services.mark_paid)(form.instance)
    @admin.action(description="Send selected draft invoices to the client")
    def send_invoices(self, request, queryset):
        n = 0
        for inv in queryset.filter(status="draft"):
            if inv.items.exists():
                services._issue(inv)
                n += 1
        self.message_user(request, f"Sent {n} invoice(s). Drafts without items were skipped.")

    @admin.action(description="Confirm payment received (marks paid, sends receipt)")
    def confirm_paid(self, request, queryset):
        n = 0
        for inv in queryset.exclude(status__in=["paid", "cancelled", "draft"]):
            services.mark_paid(inv)
            n += 1
        self.message_user(request, f"Marked {n} invoice(s) as paid and sent receipts.")

    @admin.action(description="Send payment reminder")
    def send_reminders(self, request, queryset):
        from django.utils import timezone
        n = 0
        for inv in queryset.filter(status="sent"):
            notify(inv.client, f"Reminder: invoice {inv.number} ({inv.total:,} RWF) is awaiting payment.",
                   reverse("invoice", args=[inv.pk]), kind="invoice", button="Pay now")
            inv.last_reminder = timezone.localdate()
            inv.save(update_fields=["last_reminder"])
            n += 1
        self.message_user(request, f"Reminded {n} client(s).")

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not (obj and obj.status in ("sent", "submitted", "paid"))
