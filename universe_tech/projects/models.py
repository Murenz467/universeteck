from django.conf import settings
from django.db import models
from django.utils import timezone
from core.validators import validate_upload


class Project(models.Model):
    STATUS = [("planning", "Planning"), ("in_progress", "In progress"), ("review", "In review"),
              ("completed", "Completed"), ("on_hold", "On hold")]
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    quotation = models.OneToOneField("quotes.Quotation", null=True, blank=True, on_delete=models.SET_NULL)
    contract = models.OneToOneField("contracts.Contract", null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="project")
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                limit_choices_to={"is_staff": True}, related_name="managed_projects",
                                help_text="The Universe Tech person the client deals with.")
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="planning")
    start_date = models.DateField(null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._old_status = self.status

    def __str__(self):
        return self.title

    def save(self, *args, **kw):
        adding = self._state.adding
        super().save(*args, **kw)
        if not adding and self.status != self._old_status:
            from .services import on_project_status
            on_project_status(self, self._old_status)
        self._old_status = self.status

    @property
    def progress(self):
        ms = list(self.milestones.all())
        return int(100 * sum(1 for m in ms if m.status == "approved") / len(ms)) if ms else 0

    @property
    def next_milestone(self):
        return self.milestones.exclude(status="approved").first()

    @property
    def is_late(self):
        return bool(self.target_date and self.target_date < timezone.localdate() and self.status != "completed")

    @property
    def days_left(self):
        return (self.target_date - timezone.localdate()).days if self.target_date else None


class Milestone(models.Model):
    STATUS = [("pending", "Pending"), ("in_progress", "In progress"),
              ("ready", "Ready for your approval"), ("changes", "Changes requested"), ("approved", "Approved")]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    amount = models.PositiveIntegerField(default=0, help_text="Price of this phase in RWF (from the contract).")
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    order = models.PositiveSmallIntegerField(default=0)
    client_feedback = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order", "due_date"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._old_status = self.status

    def __str__(self):
        return f"{self.project}: {self.title}"

    def save(self, *args, **kw):
        adding = self._state.adding
        super().save(*args, **kw)
        if not adding and self.status != self._old_status:
            from .services import on_milestone_status
            on_milestone_status(self, self._old_status)
        self._old_status = self.status

    def approve(self):
        self.status, self.approved_at = "approved", timezone.now()
        self.save()

    @property
    def is_overdue(self):
        return bool(self.due_date and self.due_date < timezone.localdate() and self.status != "approved")


def _private_path(instance, filename):
    return f"private/{instance.__class__.__name__.lower()}s/{filename}"


class Deliverable(models.Model):
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name="deliverables")
    title = models.CharField(max_length=140)
    file = models.FileField(upload_to=_private_path, validators=[validate_upload])
    uploaded = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ProjectUpdate(models.Model):
    """A message on the client's project timeline: a progress note from staff, or an automatic system entry."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="updates")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to=_private_path, blank=True, validators=[validate_upload])
    is_system = models.BooleanField(default=False, editable=False)
    notify_client = models.BooleanField("Notify the client", default=True,
                                        help_text="Sends an alert and email when this update is first saved.")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title
