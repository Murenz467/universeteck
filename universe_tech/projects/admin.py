from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from notifications.utils import notify
from .models import Project, Milestone, Deliverable, ProjectUpdate


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0
    fields = ("order", "title", "due_date", "amount", "status", "description")


class UpdateInline(admin.StackedInline):
    model = ProjectUpdate
    extra = 0
    fields = ("title", "body", "attachment", "notify_client", "author", "created")
    readonly_fields = ("author", "created")
    ordering = ("-created",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_system=False)

    def get_extra(self, request, obj=None, **kw):
        return 1 if obj else 0


class DeliverableInline(admin.TabularInline):
    model = Deliverable
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "client", "status", "progress_pct", "target_date", "late", "manager")
    list_filter = ("status", "manager")
    search_fields = ("title", "client__username", "client__email")
    inlines = [MilestoneInline, UpdateInline]
    readonly_fields = ("contract", "completed_at", "client_view")
    fields = ("client", "title", "description", "status", "manager", "start_date", "target_date", "contract",
              "quotation", "completed_at", "client_view")

    @admin.display(description="Progress")
    def progress_pct(self, obj):
        return f"{obj.progress}%"

    @admin.display(boolean=True, description="Late")
    def late(self, obj):
        return obj.is_late

    @admin.display(description="Client view")
    def client_view(self, obj):
        if not obj.pk:
            return "Save first, then preview here."
        return format_html('<a href="{}" target="_blank">See what the client sees →</a>', reverse("project", args=[obj.pk]))

    def save_formset(self, request, form, formset, change):
        if formset.model is ProjectUpdate:
            for obj in formset.save(commit=False):
                is_new = obj.pk is None
                if is_new:
                    obj.author, obj.is_system = request.user, False
                obj.save()
                if is_new and obj.notify_client:
                    notify(obj.project.client, f"Update on {obj.project.title}: {obj.title}",
                           reverse("project", args=[obj.project_id]), subject=f"Project update: {obj.title}",
                           kind="project", button="Read the update")
            for obj in formset.deleted_objects:
                obj.delete()
            return
        for obj in formset.save(commit=False):   # milestones: model.save() already notifies on status change
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "due_date", "amount")
    list_filter = ("status",)
    search_fields = ("title", "project__title")
    inlines = [DeliverableInline]
    actions = ["mark_in_progress", "mark_ready"]

    @admin.action(description="Start work (notifies the client)")
    def mark_in_progress(self, request, queryset):
        for m in queryset.filter(status__in=["pending", "changes"]):
            m.status = "in_progress"
            m.save()

    @admin.action(description="Mark ready for client approval (notifies the client)")
    def mark_ready(self, request, queryset):
        n = 0
        for m in queryset.filter(status__in=["in_progress", "changes"]):
            m.status = "ready"
            m.save()
            n += 1
        self.message_user(request, f"{n} milestone(s) sent to the client for approval.")
