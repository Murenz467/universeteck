"""Daily reminders. Run from a scheduler (Railway cron, crontab, etc.):  python manage.py send_reminders"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone
from billing.models import Invoice
from contracts.models import Contract
from notifications.utils import notify_once, notify_staff
from projects.models import Milestone
from proposals.models import Proposal


class Command(BaseCommand):
    help = "Remind clients about unsigned contracts, expiring proposals, pending approvals and unpaid invoices."

    def handle(self, *args, **opts):
        today, now, n = timezone.localdate(), timezone.now(), 0
        for c in Contract.objects.filter(status="sent", sent_at__lte=now - timedelta(days=3)):
            n += notify_once(c.client, f"Reminder: contract {c.number} is waiting for your signature.",
                             reverse("contract", args=[c.pk]), kind="contract", button="Review and sign")
        for p in Proposal.objects.filter(status="sent", valid_until__isnull=False,
                                         valid_until__lte=today + timedelta(days=3), valid_until__gte=today):
            n += notify_once(p.client, f"Your proposal {p.number} expires on {p.valid_until:%d %b}.",
                             reverse("proposal", args=[p.pk]), kind="proposal", button="Review proposal")
        for m in Milestone.objects.filter(status="ready").select_related("project__client"):
            n += notify_once(m.project.client, f"“{m.title}” is still waiting for your approval.",
                             reverse("project", args=[m.project_id]), within_days=4, kind="milestone")
        late = Invoice.objects.filter(status="sent", due_date__lt=today)
        for i in late:
            n += notify_once(i.client, f"Invoice {i.number} ({i.total:,} RWF) is overdue.",
                             reverse("invoice", args=[i.pk]), within_days=5, kind="invoice", button="Pay now")
        self.stdout.write(self.style.SUCCESS(f"Sent {n} reminder(s)."))
