from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from .models import Contract
from . import services


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "client", "status", "total_amount", "sent_at", "signed_at")
    list_filter = ("status",)
    search_fields = ("number", "title", "client__username", "client__email", "signed_name")
    actions = ["send_to_client", "regenerate_text"]
    readonly_fields = ("number", "sent_at", "viewed_at", "company_signed_at", "signed_name", "signed_at",
                       "signed_ip", "signature_hash", "client_view")
    fieldsets = (
        (None, {"fields": ("number", "proposal", "client", "title", "status", "start_date", "client_view")}),
        ("Agreement", {"fields": ("body",)}),
        ("Price", {"fields": ("total_amount", "deposit_percent")}),
        ("Signatures", {"fields": ("company_signed_by", "company_signed_at", "signed_name", "signed_at",
                                   "signed_ip", "signature_hash")}),
        ("Internal", {"fields": ("internal_notes",)}),
    )

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_locked:       # the agreed text can never change after sending
            ro += ["body", "total_amount", "deposit_percent", "proposal", "client", "title", "start_date",
                   "company_signed_by"]
        return ro

    @admin.display(description="Client view")
    def client_view(self, obj):
        if not obj.pk:
            return "Save first, then preview here."
        return format_html('<a href="{}" target="_blank">Preview exactly what the client sees →</a>',
                           reverse("contract", args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        send_now = "status" in form.changed_data and obj.status == "sent"
        if send_now:
            obj.status = "draft"
        super().save_model(request, obj, form, change)
        if send_now:
            services.send_contract(obj)
            messages.success(request, "Contract sent. The client has been notified.")

    @admin.action(description="Send selected draft contracts to the client")
    def send_to_client(self, request, queryset):
        n = 0
        for c in queryset.filter(status="draft"):
            services.send_contract(c)
            n += 1
        self.message_user(request, f"Sent {n} contract(s).")

    @admin.action(description="Regenerate agreement text from the proposal (drafts only)")
    def regenerate_text(self, request, queryset):
        n = 0
        for c in queryset.filter(status="draft", proposal__isnull=False):
            services.regenerate_body(c)
            n += 1
        self.message_user(request, f"Regenerated {n} draft contract(s).")

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not (obj and obj.status == "signed")
