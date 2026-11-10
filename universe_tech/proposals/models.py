from datetime import timedelta
from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

DEFAULT_PAYMENT_TERMS = (
    "A deposit is invoiced when the contract is signed. The balance is invoiced as each phase is approved by you. "
    "Invoices are payable within 7 days by MTN MoMo, Airtel Money or bank transfer."
)


class Proposal(models.Model):
    STATUS = [("draft", "Draft"), ("sent", "Sent to client"), ("changes", "Changes requested"),
              ("accepted", "Accepted"), ("declined", "Declined")]
    request = models.ForeignKey("quotes.QuoteRequest", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="proposals")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="proposals",
                               help_text="The customer account that will see this proposal.")
    number = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=160)
    summary = models.TextField("Executive summary", blank=True,
                               help_text="Two or three sentences: what we understood and what we will deliver.")
    objectives = models.TextField(blank=True, help_text="The goals this project must achieve for the client.")
    scope = models.TextField("Scope of work", blank=True, help_text="What is included. Be specific.")
    deliverables = models.TextField(blank=True, help_text="One deliverable per line.")
    assumptions = models.TextField("What we need from you", blank=True,
                                   help_text="Content, access, decisions or approvals the client must provide.")
    exclusions = models.TextField("Not included", blank=True, help_text="Anything that is out of scope.")
    timeline_note = models.CharField(max_length=240, blank=True)
    payment_terms = models.TextField(default=DEFAULT_PAYMENT_TERMS)
    deposit_percent = models.PositiveSmallIntegerField(default=40, validators=[MaxValueValidator(100)])
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    version = models.PositiveSmallIntegerField(default=1)
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    client_comment = models.TextField("Client's last comment", blank=True)
    internal_notes = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.number} {self.title}"

    def save(self, *args, **kw):
        creating = self.pk is None
        if creating and not self.valid_until:
            self.valid_until = timezone.localdate() + timedelta(days=getattr(settings, "PROPOSAL_VALID_DAYS", 14))
        super().save(*args, **kw)
        if not self.number:
            self.number = f"UT-P-{self.pk:04d}"
            super().save(update_fields=["number"])

    @property
    def total(self):
        return sum(p.amount for p in self.phases.all())

    @property
    def deposit_amount(self):
        return round(self.total * self.deposit_percent / 100)

    @property
    def duration_days(self):
        return sum(p.duration_days for p in self.phases.all())

    @property
    def duration_weeks(self):
        return max(1, round(self.duration_days / 7)) if self.duration_days else 0

    @property
    def deliverable_list(self):
        return [l.strip(" -•\t") for l in self.deliverables.splitlines() if l.strip()]

    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.localdate()
                    and self.status in ("sent", "changes"))

    @property
    def can_respond(self):
        return self.status == "sent" and not self.is_expired


class ProposalPhase(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="phases")
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    duration_days = models.PositiveSmallIntegerField(default=7, help_text="Working time for this phase, in days.")
    amount = models.PositiveIntegerField(default=0, help_text="Price for this phase in RWF.")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title
