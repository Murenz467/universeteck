"""Existing sites had 3 service categories. Add the 4th (Web & Mobile Applications) and move its services into it,
without touching anything else the owner may have edited. Fresh databases are filled by `seed_services`."""
from django.db import migrations

MOVE = ["website-development", "web-applications", "mobile-applications"]


def forwards(apps, schema_editor):
    Cat, Svc = apps.get_model("services", "ServiceCategory"), apps.get_model("services", "Service")
    if not Cat.objects.exists() or Cat.objects.filter(slug="web-mobile-applications").exists():
        return
    cat = Cat.objects.create(name="Web & Mobile Applications", slug="web-mobile-applications",
                             tagline="Fast, responsive web and mobile apps for modern businesses.", order=2)
    for i, slug in enumerate(MOVE):
        Svc.objects.filter(slug=slug).update(category=cat, order=i)
    # keep the display order: Software, Branding, Web & Mobile, Hosting
    for c in Cat.objects.filter(slug="hosting-devops"):
        c.order = 3
        c.save(update_fields=["order"])


class Migration(migrations.Migration):
    dependencies = [("services", "0001_initial")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
