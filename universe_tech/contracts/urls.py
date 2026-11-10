from django.urls import path
from . import views
urlpatterns = [
    path("", views.contract_list, name="contract_list"),
    path("<int:pk>/", views.contract_detail, name="contract"),
    path("<int:pk>/sign/", views.contract_sign, name="contract_sign"),
    path("<int:pk>/changes/", views.contract_changes, name="contract_changes"),
]
