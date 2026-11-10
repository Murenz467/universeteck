from django.conf import settings
from django.db import models


class Notification(models.Model):
    KINDS = [("system", "General"), ("proposal", "Proposal"), ("contract", "Contract"), ("project", "Project"),
             ("milestone", "Milestone"), ("invoice", "Invoice"), ("support", "Support"), ("quote", "Quotation")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=12, choices=KINDS, default="system")
    message = models.CharField(max_length=240)
    url = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{self.user}: {self.message}"
