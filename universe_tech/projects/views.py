from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
from .models import Project, Milestone, Deliverable, ProjectUpdate


def _project_for(request, pk):
    qs = Project.objects.select_related("client", "manager", "contract")
    if request.user.has_perm("projects.view_project"):
        return get_object_or_404(qs, pk=pk)
    return get_object_or_404(qs, pk=pk, client=request.user)


@login_required
def project_list(request):
    return render(request, "projects/list.html", {"projects": request.user.projects.all()})


@login_required
def project_detail(request, pk):
    project = _project_for(request, pk)
    return render(request, "projects/project_detail.html", {
        "project": project,
        "preview": project.client_id != request.user.id,
        "milestones": project.milestones.prefetch_related("deliverables"),
        "updates": project.updates.select_related("author")[:30],
        "invoices": project.invoices.exclude(status="draft"),
        "proposal": getattr(project.contract, "proposal", None) if project.contract else None})


@login_required
@require_POST
def approve_milestone(request, pk):
    m = get_object_or_404(Milestone, pk=pk, project__client=request.user)
    if m.status == "ready":
        m.approve()
        messages.success(request, f"You approved “{m.title}”. Thank you!")
    return redirect("project", pk=m.project_id)


@login_required
@require_POST
def milestone_changes(request, pk):
    m = get_object_or_404(Milestone, pk=pk, project__client=request.user)
    comment = request.POST.get("comment", "").strip()[:2000]
    if m.status != "ready":
        return redirect("project", pk=m.project_id)
    if not comment:
        messages.error(request, "Please describe the changes you would like.")
    else:
        m.status, m.client_feedback = "changes", comment
        m.save()
        messages.success(request, "Thanks. Your feedback was sent to the team.")
    return redirect("project", pk=m.project_id)


def _send(request, field_file, name):
    try:
        return FileResponse(field_file.open("rb"), as_attachment=True, filename=name)
    except (FileNotFoundError, ValueError):
        raise Http404("File is not available.")


@login_required
def download_deliverable(request, pk):
    d = get_object_or_404(Deliverable.objects.select_related("milestone__project"), pk=pk)
    if not (request.user.has_perm("projects.view_deliverable") or d.milestone.project.client_id == request.user.id):
        raise Http404
    return _send(request, d.file, d.file.name.rsplit("/", 1)[-1])


@login_required
def download_attachment(request, pk):
    u = get_object_or_404(ProjectUpdate.objects.select_related("project"), pk=pk)
    if not (request.user.has_perm("projects.view_projectupdate") or u.project.client_id == request.user.id) \
            or not u.attachment:
        raise Http404
    return _send(request, u.attachment, u.attachment.name.rsplit("/", 1)[-1])
