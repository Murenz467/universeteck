from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.ratelimit import ratelimit
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from notifications.utils import notify_staff
from .forms import TicketForm, ReplyForm
from .models import Ticket, TicketMessage

@login_required
def ticket_list(request):
    return render(request, "support/list.html", {"tickets": request.user.tickets.all()})

@login_required
@ratelimit("ticket_new", 10, 3600, by="user")
def ticket_new(request):
    initial = {}
    pid = request.GET.get("project", "")
    if pid.isdigit() and request.user.projects.filter(pk=pid).exists():
        initial["project"] = int(pid)
    form = TicketForm(request.POST or None, user=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        t = form.save(commit=False)
        t.client = request.user
        t.save()
        TicketMessage.objects.create(ticket=t, author=request.user, body=form.cleaned_data["message"])
        notify_staff(f"New support ticket #{t.pk}: {t.subject}", form.cleaned_data["message"],
                     reverse("admin:support_ticket_change", args=[t.pk]), kind="support")
        messages.success(request, "Ticket opened. We will reply soon.")
        return redirect("ticket", pk=t.pk)
    return render(request, "support/new.html", {"form": form})

@login_required
@ratelimit("ticket_reply", 40, 3600, by="user")
def ticket_detail(request, pk):
    t = get_object_or_404(Ticket, pk=pk, client=request.user)
    form = ReplyForm(request.POST or None)
    if request.method == "POST":
        if request.POST.get("action") == "close":
            t.status = "closed"
            t.save()
            messages.success(request, "Ticket closed.")
            return redirect("ticket_list")
        if form.is_valid():
            TicketMessage.objects.create(ticket=t, author=request.user, body=form.cleaned_data["body"])
            t.status = "open"
            t.save()
            notify_staff(f"Reply on ticket #{t.pk}: {t.subject}", form.cleaned_data["body"],
                         reverse("admin:support_ticket_change", args=[t.pk]), kind="support")
            return redirect("ticket", pk=t.pk)
    return render(request, "support/detail.html", {"t": t, "form": form})
