from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from core.ratelimit import ratelimit
from django.conf import settings
from . import services
from .models import Invoice


@login_required
def invoice_list(request):
    invs = Invoice.objects.filter(client=request.user).exclude(status="draft").prefetch_related("items")
    outstanding = sum(i.total for i in invs if i.status in ("sent", "submitted"))
    paid = sum(i.total for i in invs if i.status == "paid")
    return render(request, "billing/list.html", {"invoices": invs, "outstanding": outstanding, "paid": paid})


@login_required
def invoice_detail(request, pk):
    qs = Invoice.objects.select_related("client", "project").prefetch_related("items")
    if request.user.has_perm("billing.view_invoice"):
        inv = get_object_or_404(qs, pk=pk)
    else:
        inv = get_object_or_404(qs.exclude(status="draft"), pk=pk, client=request.user)
    return render(request, "billing/detail.html", {
        "inv": inv, "methods": Invoice.METHODS, "pay_options": settings.PAYMENT_METHODS,
        "preview": inv.client_id != request.user.id, "company": settings.COMPANY})


@login_required
@require_POST
@ratelimit("pay", 20, 3600, by="user")
def invoice_pay(request, pk):
    inv = get_object_or_404(Invoice, pk=pk, client=request.user, status="sent")
    method = request.POST.get("method", "")
    ref = request.POST.get("reference", "").strip()[:120]
    if method not in dict(Invoice.METHODS) or not ref:
        messages.error(request, "Please choose how you paid and enter the transaction reference.")
    else:
        services.report_payment(inv, method, ref)
        messages.success(request, "Thank you. We will confirm your payment shortly and send your receipt.")
    return redirect("invoice", pk=inv.pk)
