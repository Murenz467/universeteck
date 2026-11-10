from django.urls import path
from . import views
urlpatterns = [
    path("", views.request_quote, name="quote"),
    path("<int:pk>/", views.quotation_detail, name="quotation"),
    path("<int:pk>/respond/", views.quotation_respond, name="quotation_respond"),
]
