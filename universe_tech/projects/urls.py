from django.urls import path
from . import views
urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("<int:pk>/", views.project_detail, name="project"),
    path("milestones/<int:pk>/approve/", views.approve_milestone, name="approve_milestone"),
    path("milestones/<int:pk>/changes/", views.milestone_changes, name="milestone_changes"),
    path("files/<int:pk>/", views.download_deliverable, name="download_deliverable"),
    path("attachments/<int:pk>/", views.download_attachment, name="download_attachment"),
]
