from django.db import models
from services.models import ServiceCategory

class CaseStudy(models.Model):
    title = models.CharField(max_length=140)
    slug = models.SlugField(unique=True)
    client_name = models.CharField(max_length=120, blank=True)
    category = models.ForeignKey(ServiceCategory, null=True, blank=True, on_delete=models.SET_NULL)
    summary = models.CharField(max_length=220)
    body = models.TextField(help_text="Challenge, solution and results.")
    image = models.ImageField(upload_to="portfolio/", blank=True)
    live_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]
        verbose_name_plural = "case studies"

    def __str__(self):
        return self.title
