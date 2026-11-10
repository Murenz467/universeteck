from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from .models import Proposal, ProposalPhase
from . import services


class PhaseInline(admin.TabularInline):
    model = ProposalPhase
    extra = 2


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "client", "status", "total_display", "valid_until", "viewed_at", "version")
    list_filter = ("status",)
    search_fields = ("number", "title", "client__username", "client__email")
    inlines = [PhaseInline]
    actions = ["send_to_client"]
    readonly_fields = ("number", "sent_at", "viewed_at", "responded_at", "client_comment", "version", "client_view")
    fieldsets = (
        (None, {"fields": ("number", "client", "request", "title", "status", "valid_until", "client_view")}),
        ("Proposal content", {"fields": ("summary", "objectives", "scope", "deliverables", "assumptions",
                                         "exclusions", "timeline_note")}),
        ("Commercial terms", {"fields": ("deposit_percent", "payment_terms")}),
        ("Client activity", {"fields": ("sent_at", "viewed_at", "responded_at", "client_comment", "version")}),
        ("Internal", {"fields": ("internal_notes",)}),
    )

    @admin.display(description="Total")
    def total_display(self, obj):
        return f"{obj.total:,} RWF"

    @admin.display(description="Client view")
    def client_view(self, obj):
        if not obj.pk:
            return "Save first, then preview here."
        return format_html('<a href="{}" target="_blank">Preview exactly what the client sees →</a>',
                           reverse("proposal", args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        was_sent = "status" in form.changed_data and obj.status == "sent"
        if was_sent:
            obj.status = Proposal.objects.get(pk=obj.pk).status if change else "draft"  # let service decide
        super().save_model(request, obj, form, change)
        self._send_after_save = was_sent

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if getattr(self, "_send_after_save", False):
            services.send_proposal(form.instance)
            self._send_after_save = False
            messages.success(request, "Proposal sent. The client has been notified.")

    @admin.action(description="Send selected proposals to the client")
    def send_to_client(self, request, queryset):
        n = 0
        for p in queryset.exclude(status__in=["accepted", "declined"]):
            if not p.phases.exists():
                messages.warning(request, f"{p.number} has no phases/prices yet, so it was not sent.")
                continue
            services.send_proposal(p)
            n += 1
        self.message_user(request, f"Sent {n} proposal(s).")

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not (obj and obj.status == "accepted")
