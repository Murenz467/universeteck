from django.urls import reverse
from django.utils import timezone
from core.audit import record
from notifications.utils import notify, notify_staff


def send_proposal(p):
    """Mark a proposal as sent and alert the client. Safe to call from admin or code."""
    if p.status == "changes":      # a revision after the client asked for changes
        p.version += 1
    p.status, p.sent_at, p.viewed_at = "sent", timezone.now(), None
    p.save()
    if p.request and p.request.status in ("new", "contacted"):
        p.request.status = "quoted"
        p.request.save(update_fields=["status"])
    label = f"updated proposal (v{p.version})" if p.version > 1 else "proposal"
    notify(p.client, f"New {label} for you: {p.title}", reverse("proposal", args=[p.pk]),
           subject=f"Proposal {p.number} from Universe Tech", kind="proposal", button="Review proposal")


def accept(p, comment=""):
    p.status, p.responded_at, p.client_comment = "accepted", timezone.now(), comment
    p.save()
    record(None, "proposal_accepted", user=p.client, detail=p.number)
    from contracts.services import get_or_create_draft
    contract = get_or_create_draft(p)
    notify_staff(f"Proposal accepted: {p.number} {p.title} ({p.client})",
                 f"{p.client} accepted proposal {p.number}. A draft contract {contract.number} is ready for you to "
                 f"review and send.", reverse("admin:contracts_contract_change", args=[contract.pk]), kind="proposal")
    notify(p.client, f"Thank you! We are preparing your contract for {p.title}.", reverse("proposal", args=[p.pk]),
           kind="proposal")
    return contract


def decline(p, comment=""):
    p.status, p.responded_at, p.client_comment = "declined", timezone.now(), comment
    p.save()
    notify_staff(f"Proposal declined: {p.number} {p.title}", f"{p.client} declined. Reason: {comment or '—'}",
                 reverse("admin:proposals_proposal_change", args=[p.pk]), kind="proposal")
    if p.request:
        p.request.status = "lost"
        p.request.save(update_fields=["status"])


def request_changes(p, comment):
    p.status, p.responded_at, p.client_comment = "changes", timezone.now(), comment
    p.save()
    notify_staff(f"Changes requested on {p.number} ({p.client})", comment,
                 reverse("admin:proposals_proposal_change", args=[p.pk]), kind="proposal")
