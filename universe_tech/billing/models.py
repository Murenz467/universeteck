from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class Invoice(models.Model):
    STATUS = [("draft", "Draft"), ("sent", "Awaiting payment"), ("submitted", "Payment reported"),
              ("paid", "Paid"), ("cancelled", "Cancelled")]
    KIND = [("deposit", "Deposit"), ("milestone", "Phase payment"), ("other", "Other")]
    METHODS = [("momo", "MTN MoMo"), ("airtel", "Airtel Money"), ("bank", "Bank transfer"), ("cash", "Cash")]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="invoices")
    milestone = models.OneToOneField("projects.Milestone", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="invoice")
    number = models.CharField(max_length=20, unique=True, blank=True)
    kind = models.CharField(max_length=10, choices=KIND, default="other")
    title = models.CharField(max_length=160)
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=10, choices=METHODS, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True, help_text="Transaction ID / reference")
    submitted_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    last_reminder = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.number} {self.title}"

    def save(self, *args, **kw):
        if not self.due_date and self.status != "draft":
            self.due_date = self.issue_date + timedelta(days=settings.INVOICE_DUE_DAYS)
        super().save(*args, **kw)
        if not self.number:
            self.number = f"UT-I-{self.pk:04d}"
            super().save(update_fields=["number"])

    @property
    def total(self):
        return sum(i.line_total for i in self.items.all())

    @property
    def is_overdue(self):
        return bool(self.due_date and self.due_date < timezone.localdate() and self.status in ("sent", "submitted"))

    @property
    def can_pay(self):
        return self.status == "sent"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.PositiveIntegerField(help_text="Price in RWF.")

    @property
    def line_total(self):
        return self.quantity * self.unit_price
