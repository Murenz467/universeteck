from django.conf import settings
from django.db import models
from services.models import Service

class QuoteRequest(models.Model):
    BUDGETS = [("", "Not sure yet"), ("small", "Under 500,000 RWF"), ("medium", "500,000 – 2,000,000 RWF"),
               ("large", "2,000,000 – 10,000,000 RWF"), ("xl", "Over 10,000,000 RWF")]
    STATUS = [("new", "New"), ("contacted", "Contacted"), ("quoted", "Quotation sent"),
              ("won", "Won"), ("lost", "Lost")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="quote_requests")
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=120, blank=True)
    services = models.ManyToManyField(Service, blank=True)
    budget = models.CharField(max_length=10, choices=BUDGETS, blank=True)
    details = models.TextField("Tell us about your project")
    status = models.CharField(max_length=12, choices=STATUS, default="new")
    internal_notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    limit_choices_to={"is_staff": True}, related_name="assigned_leads")
    follow_up_date = models.DateField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.name} ({self.created:%Y-%m-%d})"

class Quotation(models.Model):
    STATUS = [("draft", "Draft"), ("sent", "Sent"), ("accepted", "Accepted"), ("declined", "Declined")]
    request = models.ForeignKey(QuoteRequest, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="quotations")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quotations",
                               help_text="The customer account that will see this quotation.")
    number = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=140)
    intro = models.TextField(blank=True)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def save(self, *args, **kw):
        super().save(*args, **kw)
        if not self.number:
            self.number = f"UT-Q-{self.pk:04d}"
            super().save(update_fields=["number"])

    @property
    def total(self):
        return sum(i.line_total for i in self.items.all())

    def __str__(self):
        return f"{self.number} {self.title}"

class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.PositiveIntegerField(help_text="Price in RWF")

    @property
    def line_total(self):
        return self.quantity * self.unit_price

class LeadNote(models.Model):
    request = models.ForeignKey(QuoteRequest, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]
