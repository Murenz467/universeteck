from django.shortcuts import render
from services.models import ServiceCategory

STEPS = [
    ("Discover", "Tell us about your needs and goals."),
    ("Plan", "We suggest a plan that fits your budget and timeline."),
    ("Design", "We create designs for your approval."),
    ("Build", "We develop and test your solution."),
    ("Deploy", "We launch your project and make it live."),
    ("Support", "We provide ongoing maintenance when you need it."),
]
WHY = [
    ("One technology partner", "Software, branding and hosting from one team."),
    ("Business-focused solutions", "We build what moves your business forward."),
    ("Professional delivery", "On-time, reliable work you can approve at each stage."),
    ("Scalable systems", "Solutions that grow as your business grows."),
    ("Long-term support", "We stay with you after launch."),
]

def home(request):
    from portfolio.models import CaseStudy
    cats = ServiceCategory.objects.prefetch_related("services")
    projects = CaseStudy.objects.filter(is_published=True).select_related("category")[:4]
    return render(request, "home.html", {"categories": cats, "steps": STEPS, "why": WHY, "projects": projects})

VISION = ("To be the most trusted technology partner for businesses across Rwanda and East Africa, "
          "turning good ideas into digital products that grow, last and make a real difference.")
MISSION = ("To design, build and host reliable software, web and mobile applications and strong brand identities "
           "that are affordable, secure and delivered on time, and to stay beside every client long after launch.")
OBJECTIVES = [
    ("Deliver quality that lasts", "Ship clean, tested and secure systems that clients can depend on every day."),
    ("Make technology affordable", "Give small and growing Rwandan businesses access to professional digital tools at fair prices."),
    ("Keep every project transparent", "Clear proposals, signed contracts, phase-by-phase approval and honest progress updates."),
    ("Build local capacity", "Create opportunities for young Rwandan developers and designers to grow real-world skills."),
    ("Support clients beyond launch", "Offer hosting, maintenance and improvement so every product keeps performing."),
    ("Grow regionally", "Expand our services from Kigali to businesses across East Africa."),
]
VALUES = [
    ("Integrity", "We say what we can do, price it clearly and keep our word.", "i-shield"),
    ("Excellence", "We care about the details users notice and the foundations they never see.", "i-bulb"),
    ("Reliability", "On-time delivery and systems that stay up when you need them.", "i-clock"),
    ("Partnership", "Your success is our success. We work with you, not just for you.", "i-users"),
    ("Innovation", "We use modern tools and fresh thinking to solve practical problems.", "i-bolt"),
    ("Support", "Real people who answer, and help that continues after go-live.", "i-headset"),
]
EXPERTISE = ["Flutter mobile apps", "Django & REST APIs", "Web platforms", "Cloud hosting & deployment",
             "Brand identity & UI/UX", "Secure client portals"]


def about(request):
    return render(request, "about.html", {
        "vision": VISION, "mission": MISSION, "objectives": OBJECTIVES, "values": VALUES,
        "steps": STEPS, "why": WHY, "expertise": EXPERTISE})


def contact(request):
    return render(request, "contact.html")


def terms(request):
    return render(request, "legal/terms.html")


def privacy(request):
    return render(request, "legal/privacy.html")


def healthz(request):
    """Lightweight check used by Railway. No database access, so it answers even while the database restarts."""
    from django.http import HttpResponse
    return HttpResponse("ok", content_type="text/plain")


def robots(request):
    from django.http import HttpResponse
    from django.conf import settings
    body = ("User-agent: *\nDisallow: /accounts/\nDisallow: /projects/\nDisallow: /billing/\n"
            f"Disallow: /contracts/\nDisallow: /proposals/\nSitemap: {settings.SITE_URL}/sitemap.xml\n")
    return HttpResponse(body, content_type="text/plain")

# ---------- staff dashboard ----------
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone


@staff_member_required
def staff_dashboard(request):
    from billing.models import Invoice
    from contracts.models import Contract
    from projects.models import Project, Milestone, ProjectUpdate
    from proposals.models import Proposal
    from quotes.models import QuoteRequest, Quotation
    from support.models import Ticket
    today = timezone.localdate()
    live = QuoteRequest.objects.exclude(status__in=["won", "lost"])
    due = live.filter(follow_up_date__lte=today).order_by("follow_up_date")
    by_status = dict(QuoteRequest.objects.values_list("status").annotate(n=Count("id")))
    pipeline = [(label, by_status.get(key, 0)) for key, label in QuoteRequest.STATUS]
    if not request.user.has_perm("quotes.view_quoterequest"):
        pipeline = []

    def admin_url(name, qs=""):
        return reverse(f"admin:{name}_changelist") + qs

    unpaid = Invoice.objects.filter(status__in=["sent", "submitted"])
    paid_total = sum(i.total for i in Invoice.objects.filter(status="paid").prefetch_related("items"))
    owed_total = sum(i.total for i in unpaid.prefetch_related("items"))
    N, M = QuoteRequest.objects, Milestone.objects
    raw = [   # (label, count, link, permission needed to see it)
        ("New leads", N.filter(status="new").count(), admin_url("quotes_quoterequest", "?status__exact=new"), "quotes.view_quoterequest"),
        ("Follow-ups due", due.count(), admin_url("quotes_quoterequest"), "quotes.view_quoterequest"),
        ("Proposals awaiting reply", Proposal.objects.filter(status="sent").count(), admin_url("proposals_proposal", "?status__exact=sent"), "proposals.view_proposal"),
        ("Changes requested", Proposal.objects.filter(status="changes").count(), admin_url("proposals_proposal", "?status__exact=changes"), "proposals.view_proposal"),
        ("Contracts to sign", Contract.objects.filter(status="sent").count(), admin_url("contracts_contract", "?status__exact=sent"), "contracts.view_contract"),
        ("Active projects", Project.objects.exclude(status="completed").count(), admin_url("projects_project"), "projects.view_project"),
        ("Awaiting client approval", M.filter(status="ready").count(), admin_url("projects_milestone", "?status__exact=ready"), "projects.view_milestone"),
        ("Changes requested on work", M.filter(status="changes").count(), admin_url("projects_milestone", "?status__exact=changes"), "projects.view_milestone"),
        ("Overdue milestones", M.filter(due_date__lt=today).exclude(status="approved").count(), admin_url("projects_milestone"), "projects.view_milestone"),
        ("Payments to confirm", Invoice.objects.filter(status="submitted").count(), admin_url("billing_invoice", "?status__exact=submitted"), "billing.view_invoice"),
        ("Open tickets", Ticket.objects.filter(status="open").count(), admin_url("support_ticket", "?status__exact=open"), "support.view_ticket"),
        ("Quotations awaiting reply", Quotation.objects.filter(status="sent").count(), admin_url("quotes_quotation", "?status__exact=sent"), "quotes.view_quotation"),
    ]
    can = request.user.has_perm
    stats = [(label, n, url) for label, n, url, perm in raw if can(perm)]
    if not can("quotes.view_quoterequest"):
        pipeline = []
    return render(request, "staff/dashboard.html", {
        "stats": stats, "pipeline": pipeline, "due": due[:8] if can("quotes.view_quoterequest") else [], "today": today,
        "recent": QuoteRequest.objects.select_related("assigned_to")[:8] if can("quotes.view_quoterequest") else [],
        "pipeline_visible": can("quotes.view_quoterequest"), "projects_visible": can("projects.view_project"),
        "money": [("Collected", paid_total), ("Waiting to be paid", owed_total)] if can("billing.view_invoice") else [],
        "late_projects": [p for p in Project.objects.exclude(status="completed").select_related("client")
                          if p.is_late][:6] if can("projects.view_project") else [],
        "activity": ProjectUpdate.objects.select_related("project")[:8] if can("projects.view_projectupdate") else []})
