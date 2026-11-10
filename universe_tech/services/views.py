from django.shortcuts import render
from .models import ServiceCategory

def service_list(request):
    cats = ServiceCategory.objects.prefetch_related("services")
    return render(request, "services.html", {"categories": cats})
