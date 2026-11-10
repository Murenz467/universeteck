from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Append-only security log: who did what, from where, when. Visible (read-only) in the admin."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="+")
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=60, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    detail = models.CharField(max_length=300, blank=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.created:%Y-%m-%d %H:%M} {self.action} {self.username}"
