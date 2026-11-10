from django.urls import path
from . import views
urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("terms/", views.terms, name="terms"),
    path("privacy/", views.privacy, name="privacy"),
    path("robots.txt", views.robots, name="robots"),
    path("healthz", views.healthz, name="healthz"),
    path("staff/", views.staff_dashboard, name="staff_dashboard"),
]
