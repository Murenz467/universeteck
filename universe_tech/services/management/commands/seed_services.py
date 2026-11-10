from django.core.management.base import BaseCommand
from django.utils.text import slugify
from services.models import ServiceCategory, Service

DATA = [   # (name, slug, tagline, services)
    ("Software & Engineering", "software-engineering", "Custom systems built around how your business really works.", [
        "Custom Software", "APIs & Integrations", "Database Systems", "Automation", "UI/UX Design"]),
    ("Branding & Creative", "branding-creative", "A brand that looks as good as your product works.", [
        "Logo Design", "Letterhead Design", "Brochures & Flyers", "Business Profiles",
        "Social Media Graphics", "Brand Identity", "UI Designs"]),
    ("Web & Mobile Applications", "web-mobile-applications", "Fast, responsive web and mobile apps for modern businesses.", [
        "Website Development", "Web Applications", "Mobile Applications"]),
    ("Hosting & DevOps", "hosting-devops", "Reliable infrastructure, set up and looked after.", [
        "Web Hosting", "Domain Registration", "SSL Certificates", "Cloud & Server Setup",
        "Deployment", "CI/CD Pipelines", "Backups", "Monitoring & Logging", "Maintenance & Support"]),
]

class Command(BaseCommand):
    help = "Create the Universe Tech service catalog (safe to re-run)."

    def handle(self, *args, **opts):
        for i, (name, cslug, tag, items) in enumerate(DATA):
            cat, _ = ServiceCategory.objects.update_or_create(
                slug=cslug, defaults={"name": name, "tagline": tag, "order": i})
            for j, s in enumerate(items):
                Service.objects.update_or_create(
                    slug=slugify(s), defaults={"category": cat, "name": s, "order": j})
        self.stdout.write(self.style.SUCCESS("Service catalog ready."))
