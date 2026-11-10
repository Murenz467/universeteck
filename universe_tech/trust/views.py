import json
from django.conf import settings
from django.shortcuts import render
from .models import FaqItem, PricingPackage

JOURNEY = [
    ("Tell us what you need", "You send a quote request, or call or WhatsApp us. It costs nothing and creates no obligation.",
     "A clear conversation about your goals, budget and timeline.", "i-bulb"),
    ("Receive a written proposal", "We prepare a proposal that lists the work in phases, with a price for each phase and a timeline.",
     "Read it in your portal. Accept it, ask for changes or decline. A proposal stays valid for {days} days.", "i-check"),
    ("Sign the contract online", "Once you accept, we generate the contract from the proposal. You sign by typing your name.",
     "A fingerprint of the signed text is recorded, so nobody can quietly change it afterwards.", "i-shield"),
    ("Pay the deposit", "A {dep}% deposit invoice is created automatically when the contract is signed.",
     "Pay by MTN MoMo, Airtel Money or bank transfer. Work begins once it is received.", "i-clock"),
    ("Approve each phase", "We build phase by phase. When a phase is ready, it appears in your portal with the deliverables.",
     "Approve it, or request changes. Nothing is billed for a phase until you approve it.", "i-users"),
    ("Pay as you approve", "Approving a phase creates its invoice, with your deposit credit already applied. Invoices are due in {due} days.",
     "Tell us you have paid. We confirm and issue a receipt. The final invoice always matches your contract total.", "i-bolt"),
    ("Launch and get support", "We deploy your project, hand everything over and stay available.",
     "Open a support ticket any time, and choose hosting and maintenance if you want us to keep it running.", "i-headset"),
]


def pricing(request):
    packages = list(PricingPackage.objects.filter(is_published=True))
    return render(request, "trust/pricing.html", {
        "packages": packages,
        "deposit": settings.DEFAULT_DEPOSIT_PERCENT,
        "due_days": settings.INVOICE_DUE_DAYS,
        "valid_days": settings.PROPOSAL_VALID_DAYS,
        "rate": settings.RWF_PER_USD,
    })


def faq(request):
    items = list(FaqItem.objects.filter(is_published=True))
    groups = []
    for key, label in FaqItem.CATEGORIES:
        qs = [i for i in items if i.category == key]
        if qs:
            groups.append({"key": key, "label": label, "items": qs})
    ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": i.question, "acceptedAnswer": {"@type": "Answer", "text": i.answer}} for i in items]},
        ensure_ascii=False).replace("<", "\\u003c")
    return render(request, "trust/faq.html", {"groups": groups, "faq_ld": ld, "count": len(items)})


def how_we_work(request):
    steps = [{"n": i, "title": t, "what": w.format(days=settings.PROPOSAL_VALID_DAYS, dep=settings.DEFAULT_DEPOSIT_PERCENT,
                                                    due=settings.INVOICE_DUE_DAYS),
              "you": y.format(days=settings.PROPOSAL_VALID_DAYS, dep=settings.DEFAULT_DEPOSIT_PERCENT, due=settings.INVOICE_DUE_DAYS),
              "icon": ic} for i, (t, w, y, ic) in enumerate(JOURNEY, 1)]
    return render(request, "trust/process.html", {"steps": steps})
