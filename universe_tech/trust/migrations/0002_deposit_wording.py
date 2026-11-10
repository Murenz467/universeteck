"""Payment FAQ now says the deposit is 40% (it used to say '30% by default'). Only touches the untouched seeded text."""
from django.db import migrations


def forwards(apps, schema_editor):
    Faq = apps.get_model("trust", "FaqItem")
    for q in Faq.objects.filter(question="How does payment work?", answer__contains="30% by default"):
        q.answer = q.answer.replace("deposit invoice (30% by default)", "deposit invoice (40% of the total)")
        q.save(update_fields=["answer"])


class Migration(migrations.Migration):
    dependencies = [("trust", "0001_initial")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
