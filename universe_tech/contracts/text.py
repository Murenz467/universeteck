"""Standard agreement text, generated from an accepted proposal. Staff can edit it before sending.

NOTE: this is a sensible commercial template, not legal advice. Have a lawyer in Rwanda review it once
and adjust the wording to your needs."""
from django.conf import settings


def _money(n):
    return f"{int(n):,} RWF"


def build_body(proposal, start_date=None):
    co = settings.COMPANY
    client = proposal.client
    client_name = client.get_full_name() or client.username
    company = getattr(getattr(client, "profile", None), "company", "") or ""
    party = f"{client_name}" + (f" ({company})" if company else "")
    phases = list(proposal.phases.all())
    total = proposal.total
    deposit = proposal.deposit_amount
    L = []
    a = L.append
    a("## 1. Parties")
    a(f"This agreement is made between {co['legal_name']}, of {co['address']} (\"Universe Tech\"), and "
      f"{party}, email {client.email} (\"the Client\").")
    a("")
    a("## 2. The project")
    a(f"Universe Tech will deliver the project \"{proposal.title}\" described in proposal {proposal.number} "
      f"(version {proposal.version}), which forms part of this agreement.")
    if proposal.summary:
        a(""); a(proposal.summary)
    if proposal.scope:
        a(""); a("Scope of work:"); a(proposal.scope)
    if proposal.deliverable_list:
        a(""); a("Deliverables:")
        L.extend(f"- {d}" for d in proposal.deliverable_list)
    if proposal.exclusions:
        a(""); a("Not included in this agreement:"); a(proposal.exclusions)
    a("")
    a("## 3. Phases and timeline")
    if phases:
        for i, ph in enumerate(phases, 1):
            a(f"- Phase {i}: {ph.title} — about {ph.duration_days} day(s) — {_money(ph.amount)}")
        a(f"Estimated total duration: {proposal.duration_days} day(s) from the start date. "
          "Dates depend on the Client supplying what is needed on time (see section 5).")
    else:
        a("Phases will be agreed in writing before work starts.")
    if start_date:
        a(f"Planned start date: {start_date:%d %B %Y}.")
    a("")
    a("## 4. Fees and payment")
    a(f"The total price is {_money(total)}. {proposal.deposit_percent}% ({_money(deposit)}) is invoiced as a deposit "
      "when this agreement is signed, and work begins once the deposit is received.")
    a("The remaining balance is invoiced phase by phase, when the Client approves each phase, with the deposit "
      "credited proportionally. Invoices are payable within "
      f"{settings.INVOICE_DUE_DAYS} days by MTN MoMo, Airtel Money or bank transfer. All amounts are in Rwandan francs.")
    if proposal.payment_terms:
        a(proposal.payment_terms)
    a("Domain names, hosting, paid licences and other third-party costs are not included unless listed in the scope.")
    a("")
    a("## 5. Client responsibilities")
    a("The Client will provide content, access, feedback and approvals promptly, and will name one person who can "
      "make decisions for the Client. Delays by the Client move the timeline by the same amount.")
    if proposal.assumptions:
        a(proposal.assumptions)
    a("")
    a("## 6. Reviews and approvals")
    a("When a phase is ready, Universe Tech will mark it ready for approval on the Client portal. The Client has "
      "5 working days to approve it or to request specific changes through the portal. Reasonable corrections to "
      "work that does not match the agreed scope are included. New features or changes of direction are quoted "
      "separately as a change request before work begins.")
    a("")
    a("## 7. Ownership")
    a("On full payment, the Client owns the final deliverables made specifically for them. Universe Tech keeps "
      "ownership of its pre-existing tools, code libraries and know-how, and grants the Client a lasting licence to "
      "use them as part of the deliverables. Universe Tech may show the finished work in its portfolio unless the "
      "Client asks in writing for it to stay private.")
    a("")
    a("## 8. Confidentiality")
    a("Each party will keep the other's non-public business information confidential and use it only for this project.")
    a("")
    a("## 9. Support after delivery")
    a("Universe Tech will fix defects in the delivered work that are reported within 30 days of final approval, free "
      "of charge. Ongoing maintenance, hosting and new features are available under a separate agreement.")
    a("")
    a("## 10. Changes and termination")
    a("Either party may end this agreement by written notice if the other party seriously breaches it and does not "
      "correct the breach within 14 days. If the Client ends the project early, the Client pays for work completed "
      "and approved up to that date, and the deposit is not refundable beyond the value of work done.")
    a("")
    a("## 11. Liability")
    a("Universe Tech's total liability under this agreement is limited to the amount the Client has paid for the "
      "affected phase. Neither party is liable for indirect or consequential loss.")
    a("")
    a("## 12. Governing law")
    a("This agreement is governed by the laws of the Republic of Rwanda. The parties will first try to settle any "
      "dispute in good faith before going to court.")
    a("")
    a("## 13. Whole agreement and electronic signature")
    a("This agreement and proposal "
      f"{proposal.number} are the whole agreement between the parties. Changes must be in writing. The Client agrees that "
      "typing their name and confirming on the Client portal is a valid electronic signature. The date, time and "
      "network address of signing are recorded.")
    return "\n".join(L)
