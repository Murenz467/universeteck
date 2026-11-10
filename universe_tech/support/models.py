from django.conf import settings
from django.db import models

class Ticket(models.Model):
    STATUS = [("open", "Open (awaiting us)"), ("answered", "Answered"), ("closed", "Closed")]
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets")
    project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL)
    subject = models.CharField(max_length=160)
    status = models.CharField(max_length=10, choices=STATUS, default="open")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return f"#{self.pk} {self.subject}"

class TicketMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    is_staff = models.BooleanField(default=False)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]
