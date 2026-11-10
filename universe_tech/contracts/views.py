from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from core.audit import record
from core.ratelimit import ratelimit
from core.utils import client_ip
from notifications.utils import notify_staff
from support.models import Ticket, TicketMessage
from . import services
from .models import Contract


@login_required
def contract_list(request):
    return render(request, "contracts/list.html", {
        "contracts": Contract.objects.filter(client=request.user).exclude(status="draft")})


@login_required
def contract_detail(request, pk):
    if request.user.has_perm("contracts.view_contract"):
        c = get_object_or_404(Contract.objects.select_related("client", "proposal"), pk=pk)
    else:
        c = get_object_or_404(Contract.objects.select_related("client", "proposal").exclude(status="draft"),
                              pk=pk, client=request.user)
    preview = c.client_id != request.user.id
    if not preview and c.status == "sent" and c.viewed_at is None:
        c.viewed_at = timezone.now()
        c.save(update_fields=["viewed_at"])
        notify_staff(f"{c.client} opened contract {c.number}", c.title,
                     reverse("admin:contracts_contract_change", args=[c.pk]), kind="contract")
    project = getattr(c, "project", None)
    return render(request, "contracts/detail.html", {"c": c, "preview": preview, "project": project})


@login_required
@require_POST
@ratelimit("sign", 10, 3600, by="user")
def contract_sign(request, pk):
    with transaction.atomic():
        c = get_object_or_404(Contract.objects.select_for_update(), pk=pk, client=request.user, status="sent")
        name = request.POST.get("signed_name", "").strip()
        if len(name) < 3 or not request.POST.get("agree"):
            messages.error(request, "Please type your full name and tick the box to confirm you agree.")
            return redirect("contract", pk=c.pk)
        project = services.sign_contract(c, name[:140], client_ip(request))
    messages.success(request, "Thank you. The contract is signed and your project has started.")
    return redirect("project", pk=project.pk)


@login_required
@require_POST
@ratelimit("contract_changes", 10, 3600, by="user")
def contract_changes(request, pk):
    c = get_object_or_404(Contract, pk=pk, client=request.user, status="sent")
    comment = request.POST.get("comment", "").strip()[:2000]
    if not comment:
        messages.error(request, "Please write what you would like to discuss or change.")
        return redirect("contract", pk=c.pk)
    t = Ticket.objects.create(client=request.user, subject=f"Contract {c.number}: questions / changes")
    TicketMessage.objects.create(ticket=t, author=request.user, body=comment)
    notify_staff(f"Contract questions: {c.number} ({c.client})", comment,
                 reverse("admin:support_ticket_change", args=[t.pk]), kind="contract")
    messages.success(request, "Sent. We will reply on your support ticket.")
    return redirect("ticket", pk=t.pk)
