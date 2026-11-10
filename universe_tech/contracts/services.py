from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from core.audit import record
from notifications.utils import notify, notify_staff
from .models import Contract
from .text import build_body


def get_or_create_draft(proposal):
    contract = getattr(proposal, "contract", None)
    if contract:
        return contract
    return Contract.objects.create(
        proposal=proposal, client=proposal.client, title=proposal.title,
        body=build_body(proposal), total_amount=proposal.total, deposit_percent=proposal.deposit_percent,
        company_signed_by=settings.COMPANY["representative"])


def regenerate_body(contract):
    if contract.status != "draft" or not contract.proposal:
        raise ValueError("Only draft contracts linked to a proposal can be regenerated.")
    contract.body = build_body(contract.proposal, contract.start_date)
    contract.total_amount = contract.proposal.total
    contract.deposit_percent = contract.proposal.deposit_percent
    contract.save()


def send_contract(contract):
    contract.status = "sent"
    contract.sent_at = timezone.now()
    contract.viewed_at = None
    contract.company_signed_at = timezone.now()           # Universe Tech signs first, client countersigns
    contract.company_signed_by = contract.company_signed_by or settings.COMPANY["representative"]
    contract.save()
    record(None, "contract_sent", detail=f"{contract.number} to {contract.client.username}")
    notify(contract.client, f"Your contract is ready to sign: {contract.title}",
           reverse("contract", args=[contract.pk]), subject=f"Contract {contract.number} from Universe Tech",
           kind="contract", button="Review and sign")


def sign_contract(contract, name, ip):
    """Client signs: lock the record, create the project, deposit invoice and notifications."""
    now = timezone.now()
    contract.signed_name, contract.signed_at, contract.signed_ip, contract.status = name, now, ip, "signed"
    contract.signature_hash = contract.fingerprint(name, now)
    contract.save()
    from projects.services import create_project_from_contract
    project = create_project_from_contract(contract)
    record(None, "contract_signed", user=contract.client,
           detail=f"{contract.number} as '{name}' ip={ip} sha256={contract.signature_hash[:16]}")
    notify(contract.client, f"Contract {contract.number} signed. Your project “{project.title}” has started.",
           reverse("project", args=[project.pk]), subject=f"Contract {contract.number} signed", kind="contract",
           button="Open my project")
    notify_staff(f"Contract signed: {contract.number} ({contract.client})",
                 f"{contract.signed_name} signed {contract.number}. Project “{project.title}” was created automatically "
                 "with a deposit invoice.", reverse("admin:projects_project_change", args=[project.pk]), kind="contract")
    return project
