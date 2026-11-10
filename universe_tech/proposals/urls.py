from django.urls import path
from . import views
urlpatterns = [
    path("", views.proposal_list, name="proposal_list"),
    path("<int:pk>/", views.proposal_detail, name="proposal"),
    path("<int:pk>/respond/", views.proposal_respond, name="proposal_respond"),
]
