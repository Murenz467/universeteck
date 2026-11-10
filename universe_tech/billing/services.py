from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from core.audit import record
from notifications.utils import notify, notify_staff
from .models import Invoice, InvoiceItem


def _issue(inv):
    inv.status = "sent"
    inv.issue_date = timezone.localdate()
    inv.due_date = None
    inv.save()
    notify(inv.client, f"New invoice {inv.number}: {inv.total:,} RWF — {inv.title}", reverse("invoice", args=[inv.pk]),
           subject=f"Invoice {inv.number} from Universe Tech", kind="invoice", button="View invoice")


def create_deposit_invoice(project, contract):
    if not contract.deposit_amount:
        return None
    inv = Invoice.objects.create(client=contract.client, project=project, kind="deposit",
                                 title=f"Deposit ({contract.deposit_percent}%) — {project.title}",
                                 notes=f"Deposit for contract {contract.number}. Work begins once it is received.")
    InvoiceItem.objects.create(invoice=inv, description=f"Deposit — {contract.deposit_percent}% of {contract.number}",
                               unit_price=contract.deposit_amount)
    _issue(inv)
    return inv


def invoice_for_milestone(milestone):
    """Called when a client approves a phase. Bills the phase price minus its share of the deposit."""
    project, contract = milestone.project, milestone.project.contract
    if not contract or not milestone.amount or Invoice.objects.filter(milestone=milestone).exists():
        return None
    total = contract.total_amount or sum(m.amount for m in project.milestones.all())
    credit = round(contract.deposit_amount * milestone.amount / total) if total else 0
    amount = milestone.amount - credit
    others_open = project.milestones.exclude(pk=milestone.pk).exclude(status="approved").exists()
    if not others_open:      # last phase: bill exactly what remains so the total always matches the contract
        billed = sum(i.total for i in project.invoices.exclude(status="cancelled"))
        amount = max(contract.total_amount - billed, 0)
    if amount <= 0:
        return None
    inv = Invoice.objects.create(client=project.client, project=project, milestone=milestone, kind="milestone",
                                 title=f"{milestone.title} — {project.title}")
    InvoiceItem.objects.create(invoice=inv, description=f"Phase approved: {milestone.title}"
                               + (f" (after deposit credit of {credit:,} RWF)" if credit else ""),
                               unit_price=amount)
    _issue(inv)
    return inv


def report_payment(inv, method, reference):
    inv.status, inv.payment_method, inv.payment_reference = "submitted", method, reference
    inv.submitted_at = timezone.now()
    inv.save()
    notify_staff(f"Payment reported: {inv.number} ({inv.client})",
                 f"{inv.client} says they paid {inv.total:,} RWF by {inv.get_payment_method_display()}. "
                 f"Reference: {reference}. Please check and confirm.",
                 reverse("admin:billing_invoice_change", args=[inv.pk]), kind="invoice")


def mark_paid(inv):
    inv.status, inv.paid_at = "paid", timezone.now()
    inv.save()
    record(None, "invoice_paid", detail=f"{inv.number} {inv.total} RWF client={inv.client.username}")
    notify(inv.client, f"Payment received for {inv.number}. Thank you! Your receipt is ready.",
           reverse("invoice", args=[inv.pk]), subject=f"Receipt for invoice {inv.number}", kind="invoice",
           button="View receipt")
