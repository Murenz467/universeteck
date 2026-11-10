from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from core.ratelimit import ratelimit
from notifications.utils import notify_staff
from . import services
from .models import Proposal


@login_required
def proposal_list(request):
    return render(request, "proposals/list.html", {
        "proposals": Proposal.objects.filter(client=request.user).exclude(status="draft")})


@login_required
def proposal_detail(request, pk):
    qs = Proposal.objects.prefetch_related("phases").select_related("client")
    if request.user.has_perm("proposals.view_proposal"):          # staff preview needs an explicit permission
        p = get_object_or_404(qs, pk=pk)
    else:
        p = get_object_or_404(qs.exclude(status="draft"), pk=pk, client=request.user)
    preview = p.client_id != request.user.id
    if not preview and p.viewed_at is None and p.status == "sent":
        p.viewed_at = timezone.now()
        p.save(update_fields=["viewed_at"])
        notify_staff(f"{p.client} opened proposal {p.number}", p.title,
                     reverse("admin:proposals_proposal_change", args=[p.pk]), kind="proposal")
    contract = getattr(p, "contract", None)
    if contract and (contract.status == "draft" and not request.user.is_staff):
        contract = None
    return render(request, "proposals/detail.html", {"p": p, "preview": preview, "contract": contract})


@login_required
@require_POST
@ratelimit("proposal_respond", 20, 3600, by="user")
def proposal_respond(request, pk):
    p = get_object_or_404(Proposal, pk=pk, client=request.user, status="sent")
    action, comment = request.POST.get("action"), request.POST.get("comment", "").strip()[:2000]
    if p.is_expired:
        messages.error(request, "This proposal has expired. Please contact us and we will refresh it.")
    elif action == "accept":
        services.accept(p, comment)
        messages.success(request, "Proposal accepted. We will send your contract shortly.")
    elif action == "changes":
        if not comment:
            messages.error(request, "Please tell us what you would like changed.")
        else:
            services.request_changes(p, comment)
            messages.success(request, "Thanks. We will revise the proposal and send it back to you.")
    elif action == "decline":
        services.decline(p, comment)
        messages.success(request, "Proposal declined. Thank you for considering Universe Tech.")
    return redirect("proposal", pk=p.pk)
