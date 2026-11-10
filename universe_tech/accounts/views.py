from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from billing.models import Invoice
from contracts.models import Contract
from projects.models import Milestone
from proposals.models import Proposal
from quotes.models import Quotation
from support.models import Ticket
from .forms import RegisterForm, ProfileForm


def register(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    u = request.user
    proposals = Proposal.objects.filter(client=u).exclude(status="draft")
    contracts = Contract.objects.filter(client=u).exclude(status="draft")
    invoices = Invoice.objects.filter(client=u).exclude(status="draft")
    projects = list(u.projects.all())

    todo = []   # everything waiting on the client, most important first
    for c in contracts.filter(status="sent"):
        todo.append(("Sign your contract", c.title, reverse("contract", args=[c.pk]), "Contract"))
    for p in proposals.filter(status="sent"):
        todo.append(("Review your proposal", p.title + (" (expires soon)" if p.is_expired else ""),
                     reverse("proposal", args=[p.pk]), "Proposal"))
    for m in Milestone.objects.filter(project__client=u, status="ready").select_related("project"):
        todo.append(("Approve a milestone", f"{m.title} — {m.project.title}", reverse("project", args=[m.project_id]),
                     "Milestone"))
    for i in invoices.filter(status="sent"):
        todo.append(("Pay invoice " + i.number, f"{i.total:,} RWF" + (" — overdue" if i.is_overdue else ""),
                     reverse("invoice", args=[i.pk]), "Invoice"))
    for q in Quotation.objects.filter(client=u, status="sent"):
        todo.append(("Review your quotation", q.title, reverse("quotation", args=[q.pk]), "Quotation"))
    for t in Ticket.objects.filter(client=u, status="answered"):
        todo.append(("Read our reply", t.subject, reverse("ticket", args=[t.pk]), "Support"))

    return render(request, "accounts/dashboard.html", {
        "todo": todo, "projects": projects,
        "active_projects": [p for p in projects if p.status != "completed"],
        "done_projects": [p for p in projects if p.status == "completed"],
        "proposals": proposals[:5], "contracts": contracts[:5], "invoices": invoices[:5],
        "quotations": Quotation.objects.filter(client=u).exclude(status="draft"),
        "requests": u.quote_requests.all()[:5], "recent": u.notifications.all()[:5]})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your details were saved.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})
