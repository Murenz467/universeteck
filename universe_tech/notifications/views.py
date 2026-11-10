from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notification_list(request):
    only_unread = request.GET.get("filter") == "unread"
    qs = request.user.notifications.all()
    if only_unread:
        qs = qs.filter(is_read=False)
    return render(request, "notifications/list.html", {"items": qs[:100], "only_unread": only_unread})


@login_required
def notification_open(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    target = n.url or "notifications"
    if n.url and not url_has_allowed_host_and_scheme(n.url, allowed_hosts={request.get_host()}):
        target = "notifications"
    return redirect(target)


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications")
