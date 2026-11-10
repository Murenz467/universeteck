from django.urls import path
from . import views
urlpatterns = [
    path("", views.case_list, name="portfolio"),
    path("<slug:slug>/", views.case_detail, name="case_detail"),
]
