import hashlib
from django.conf import settings
from django.db import models
from django.utils import timezone


class Contract(models.Model):
    STATUS = [("draft", "Draft"), ("sent", "Awaiting client signature"), ("signed", "Signed"),
              ("declined", "Declined"), ("cancelled", "Cancelled")]
    proposal = models.OneToOneField("proposals.Proposal", null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="contract")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contracts")
    number = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=160)
    body = models.TextField(help_text="The full agreement. Headings start with '## ', bullet points with '- '. "
                                      "It is locked once the contract is sent.")
    total_amount = models.PositiveIntegerField(default=0, help_text="Total price in RWF.")
    deposit_percent = models.PositiveSmallIntegerField(default=40)
    start_date = models.DateField(null=True, blank=True, help_text="Planned project start. Defaults to the signing date.")
    status = models.CharField(max_length=10, choices=STATUS, default="draft")
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    company_signed_by = models.CharField(max_length=120, blank=True,
                                         help_text="Name of the person signing for Universe Tech.")
    company_signed_at = models.DateTimeField(null=True, blank=True)
    signed_name = models.CharField(max_length=140, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_ip = models.GenericIPAddressField(null=True, blank=True)
    signature_hash = models.CharField(max_length=64, blank=True)
    internal_notes = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.number} {self.title}"

    def save(self, *args, **kw):
        super().save(*args, **kw)
        if not self.number:
            self.number = f"UT-C-{self.pk:04d}"
            super().save(update_fields=["number"])

    @property
    def deposit_amount(self):
        return round(self.total_amount * self.deposit_percent / 100)

    @property
    def is_locked(self):
        return self.status in ("sent", "signed")

    def fingerprint(self, name=None, when=None):
        """SHA-256 over the agreement text and the signature details; proves the text was not altered after signing."""
        name, when = name or self.signed_name, when or self.signed_at
        raw = f"{self.number}|{self.total_amount}|{self.body}|{name}|{when.isoformat() if when else ''}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def integrity_ok(self):
        return self.status == "signed" and self.signature_hash == self.fingerprint()
