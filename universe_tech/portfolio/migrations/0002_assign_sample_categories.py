"""Spread the SAMPLE case studies over all four service categories. Only touches the sample slugs."""
from django.db import migrations

WEB_MOBILE = ["sample-online-marketplace", "sample-ride-booking-app", "sample-school-portal"]


def forwards(apps, schema_editor):
    Cat, Case = apps.get_model("services", "ServiceCategory"), apps.get_model("portfolio", "CaseStudy")
    cat = Cat.objects.filter(slug="web-mobile-applications").first()
    if cat:
        Case.objects.filter(slug__in=WEB_MOBILE).update(category=cat)


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0001_initial"), ("services", "0002_web_mobile_category")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
