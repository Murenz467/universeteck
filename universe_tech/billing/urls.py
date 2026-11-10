from django.urls import path
from . import views
urlpatterns = [
    path("", views.invoice_list, name="invoice_list"),
    path("<int:pk>/", views.invoice_detail, name="invoice"),
    path("<int:pk>/pay/", views.invoice_pay, name="invoice_pay"),
]
