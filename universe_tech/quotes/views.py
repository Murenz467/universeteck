from django.conf import settings
from django.contrib import messages
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.mail import send_mail
from core.utils import client_ip
from notifications.utils import notify_staff
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from projects.models import Project
from services.models import Service, ServiceCategory
from .forms import QuoteForm
from .models import Quotation

def request_quote(request):
    selected = set()
    if request.method == "POST":
        form = QuoteForm(request.POST)
        selected = {int(i) for i in request.POST.getlist("services") if i.isdigit()}
        key = f"quote-rate-{client_ip(request)}"
        if request.POST.get("website"):                      # honeypot: bots fill hidden fields
            messages.success(request, "Request received. We will contact you within one business day.")
            return redirect("quote")
        if cache.get(key, 0) >= 8:
            messages.error(request, "Too many requests from your connection. Please try again in an hour or call us.")
        elif form.is_valid():
            cache.set(key, cache.get(key, 0) + 1, 3600)
            q = form.save(commit=False)
            if request.user.is_authenticated:
                q.user = request.user
            q.save()
            form.save_m2m()
            notify_staff(
                f"New quote request from {q.name}",
                f"{q.name} <{q.email}> {q.phone}\nCompany: {q.company}\n"
                f"Services: {', '.join(s.name for s in q.services.all())}\n\n{q.details}",
                reverse("admin:quotes_quoterequest_change", args=[q.pk]), kind="quote")
            send_mail("We received your request — Universe Tech",
                      f"Hello {q.name.split(' ')[0]},\n\nThank you for contacting Universe Tech. We received your "
                      "request and will contact you within one business day.\n\n"
                      "If it is urgent, call or WhatsApp us on "
                      f"{settings.CONTACT['phone_display']}.\n\nUniverse Tech", settings.DEFAULT_FROM_EMAIL,
                      [q.email], fail_silently=True)
            messages.success(request, "Request received. We will contact you within one business day.")
            return redirect("quote")
    else:
        initial = {"services": Service.objects.filter(slug=request.GET.get("slug", request.GET.get("service", "")))}
        selected = {s.pk for s in initial["services"]}
        if request.user.is_authenticated:
            u = request.user
            initial.update(name=u.get_full_name() or u.username, email=u.email)
        form = QuoteForm(initial=initial)
    categories = ServiceCategory.objects.prefetch_related(
        Prefetch("services", queryset=Service.objects.filter(is_active=True)))
    return render(request, "quote.html", {"form": form, "categories": categories, "selected": selected})

@login_required
def quotation_detail(request, pk):
    q = get_object_or_404(Quotation.objects.exclude(status="draft"), pk=pk, client=request.user)
    return render(request, "quotes/quotation_detail.html", {"q": q})

@login_required
@require_POST
def quotation_respond(request, pk):
    q = get_object_or_404(Quotation, pk=pk, client=request.user, status="sent")
    if request.POST.get("action") == "accept":
        q.status = "accepted"
        q.save(update_fields=["status"])
        project, _ = Project.objects.get_or_create(
            quotation=q, defaults={"client": request.user, "title": q.title})
        messages.success(request, "Quotation accepted. Your project has been created.")
        return redirect("project", pk=project.pk)
    q.status = "declined"
    q.save(update_fields=["status"])
    messages.success(request, "Quotation declined.")
    return redirect("dashboard")
