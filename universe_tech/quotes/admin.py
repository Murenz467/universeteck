from django.conf import settings
from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from notifications.utils import notify
from .models import QuoteRequest, LeadNote, Quotation, QuotationItem

class LeadNoteInline(admin.StackedInline):
    model = LeadNote
    extra = 1
    fields = ("body", "author", "created")
    readonly_fields = ("author", "created")

@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "email", "phone", "status", "assigned_to", "follow_up_date", "overdue", "created")
    list_filter = ("status", "assigned_to", "budget", "services")
    list_editable = ("status", "assigned_to", "follow_up_date")
    search_fields = ("name", "company", "email", "details")
    date_hierarchy = "created"
    filter_horizontal = ("services",)
    inlines = [LeadNoteInline]
    actions = ["link_customers", "create_draft_quotation", "create_draft_proposal"]

    @admin.display(boolean=True, description="Follow-up overdue")
    def overdue(self, obj):
        return bool(obj.follow_up_date and obj.follow_up_date < timezone.localdate()
                    and obj.status not in ("won", "lost"))

    def save_formset(self, request, form, formset, change):
        for obj in formset.save(commit=False):
            if isinstance(obj, LeadNote) and obj.pk is None:
                obj.author = request.user
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

    @admin.action(description="Link to customer account (match by email)")
    def link_customers(self, request, queryset):
        U, n = get_user_model(), 0
        for r in queryset.filter(user__isnull=True):
            u = U.objects.filter(email__iexact=r.email).first()
            if u:
                r.user = u
                r.save(update_fields=["user"])
                n += 1
        self.message_user(request, f"Linked {n} request(s). Others have no account with that email yet.")

    @admin.action(description="Create draft quotation (needs a linked customer)")
    def create_draft_quotation(self, request, queryset):
        made = skipped = 0
        for r in queryset:
            if not r.user:
                skipped += 1
                continue
            q = Quotation.objects.create(request=r, client=r.user, title=f"Quotation for {r.name}")
            for s in r.services.all():
                QuotationItem.objects.create(quotation=q, description=s.name, unit_price=0)
            made += 1
        level = messages.SUCCESS if made else messages.WARNING
        self.message_user(request, f"Created {made} draft quotation(s); skipped {skipped} with no linked customer. "
                          "Open Quotations to set prices and send.", level)

    @admin.action(description="Create draft PROPOSAL (invites the client to the portal if needed)")
    def create_draft_proposal(self, request, queryset):
        from accounts.utils import get_or_invite_client
        from proposals.models import Proposal, ProposalPhase
        made, invited = [], 0
        for r in queryset:
            user, created = get_or_invite_client(r, request)
            invited += created
            p = Proposal.objects.create(
                request=r, client=user, title=f"{', '.join(s.name for s in r.services.all()[:2]) or 'Project'} for "
                                              f"{r.company or r.name}", summary=r.details[:600],
                deposit_percent=settings.DEFAULT_DEPOSIT_PERCENT)
            for i, s in enumerate(r.services.all()):
                ProposalPhase.objects.create(proposal=p, title=s.name, order=i, amount=0)
            made.append(p)
        links = ", ".join(f'<a href="{reverse("admin:proposals_proposal_change", args=[p.pk])}">{p.number}</a>' for p in made)
        self.message_user(request, mark_safe(f"Created {len(made)} draft proposal(s): {links}. "
                          f"{invited} new client account(s) were created and sent a set-password email."))

class ItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 2

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "client", "status", "valid_until")
    list_filter = ("status",)
    search_fields = ("number", "title", "client__username", "client__email")
    inlines = [ItemInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if "status" in form.changed_data and obj.status == "sent":
            notify(obj.client, f"Your quotation {obj.number} is ready: {obj.title}",
                   reverse("quotation", args=[obj.pk]), subject=f"Quotation {obj.number} from Universe Tech")
