from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from notifications.utils import notify, notify_staff


def log(project, title, body="", author=None, system=True):
    from .models import ProjectUpdate
    return ProjectUpdate.objects.create(project=project, title=title, body=body, author=author,
                                        is_system=system, notify_client=False)


def create_project_from_contract(contract):
    from .models import Project, Milestone
    from billing.services import create_deposit_invoice
    project, created = Project.objects.get_or_create(
        contract=contract,
        defaults=dict(client=contract.client, title=contract.title,
                      description=contract.proposal.summary if contract.proposal else "",
                      start_date=contract.start_date or timezone.localdate()))
    if not created:
        return project
    cursor = project.start_date
    if contract.proposal:
        for i, ph in enumerate(contract.proposal.phases.all()):
            cursor = cursor + timedelta(days=ph.duration_days)
            Milestone.objects.create(project=project, title=ph.title, description=ph.description,
                                     due_date=cursor, amount=ph.amount, order=i)
        project.target_date = cursor
        project.save(update_fields=["target_date"])
    log(project, "Project created", f"Contract {contract.number} signed by {contract.signed_name}. "
        f"{project.milestones.count()} phase(s) planned.")
    create_deposit_invoice(project, contract)
    return project


def on_project_status(project, old):
    label = project.get_status_display()
    if project.status == "completed" and not project.completed_at:
        project.completed_at = timezone.now()
        type(project).objects.filter(pk=project.pk).update(completed_at=project.completed_at)
    log(project, f"Project status: {label}")
    if getattr(project, "_silent", False):
        return
    url = reverse("project", args=[project.pk])
    if project.status == "completed":
        notify(project.client, f"🎉 Your project “{project.title}” is complete. Thank you for working with us!", url,
               subject=f"Project complete: {project.title}", kind="project", button="View project")
    elif project.status == "on_hold":
        notify(project.client, f"Your project “{project.title}” has been put on hold.", url, kind="project")
    else:
        notify(project.client, f"Project status changed to “{label}”: {project.title}", url, kind="project")


def on_milestone_status(m, old):
    from billing.services import invoice_for_milestone
    project, url = m.project, reverse("project", args=[m.project_id])
    if m.status == "in_progress":
        log(project, f"Started: {m.title}")
        notify(project.client, f"Work has started on “{m.title}” ({project.title}).", url, kind="milestone")
        if project.status == "planning":
            project.status, project._silent = "in_progress", True
            project.save()
    elif m.status == "ready":
        log(project, f"Ready for your approval: {m.title}")
        notify(project.client, f"Ready for your approval: {m.title} ({project.title})", url,
               subject=f"Approval needed: {m.title}", kind="milestone", button="Review and approve")
    elif m.status == "approved":
        log(project, f"Approved: {m.title}", "Approved by the client.")
        notify_staff(f"Milestone approved: {m.title} ({project.client})", project.title,
                     reverse("admin:projects_project_change", args=[project.pk]), kind="milestone")
        invoice_for_milestone(m)
        if not project.milestones.exclude(status="approved").exists() and project.status != "completed":
            project.status = "completed"
            project.save()
    elif m.status == "changes":
        log(project, f"Changes requested: {m.title}", m.client_feedback)
        notify_staff(f"Changes requested on “{m.title}” ({project.client})", m.client_feedback,
                     reverse("admin:projects_project_change", args=[project.pk]), kind="milestone")
