from django.urls import path
from . import views

urlpatterns = [
    path("pricing/", views.pricing, name="pricing"),
    path("faq/", views.faq, name="faq"),
    path("how-we-work/", views.how_we_work, name="how_we_work"),
]
