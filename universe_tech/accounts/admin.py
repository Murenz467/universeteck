from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from core.audit import record

User = get_user_model()
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class SafeUserAdmin(UserAdmin):
    """Stops privilege escalation: only a superuser can create staff, assign groups/permissions or touch
    superuser accounts. Others with 'change user' can only fix names/emails/passwords of normal clients."""
    list_display = ("username", "email", "first_name", "is_staff", "is_superuser", "is_active", "last_login")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(is_superuser=False, is_staff=False)

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            ro += ["is_staff", "is_superuser", "groups", "user_permissions", "is_active"]
        return ro

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        sensitive = {"is_staff", "is_superuser", "is_active", "password"} & set(form.changed_data)
        if sensitive:
            record(request, "user_changed", detail=f"{obj.username}: {', '.join(sorted(sensitive))}")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if "groups" in form.changed_data or "user_permissions" in form.changed_data:
            record(request, "user_roles_changed", detail=form.instance.username)


@admin.register(Group)
class SafeGroupAdmin(GroupAdmin):
    def has_module_permission(self, request): return request.user.is_superuser
    def has_view_permission(self, request, obj=None): return request.user.is_superuser
    def has_add_permission(self, request): return request.user.is_superuser
    def has_change_permission(self, request, obj=None): return request.user.is_superuser
    def has_delete_permission(self, request, obj=None): return request.user.is_superuser
