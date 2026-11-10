from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from .models import PricingPackage, FaqItem, Testimonial


class TrustPages(TestCase):
    def test_pages_render_empty_and_seeded(self):
        for n in ["pricing", "faq", "how_we_work", "home"]:
            self.assertEqual(self.client.get(reverse(n)).status_code, 200)
        call_command("seed_trust"); call_command("seed_trust")      # idempotent
        self.assertEqual(PricingPackage.objects.count(), 4)
        r = self.client.get(reverse("pricing"))
        self.assertContains(r, "Starting from"); self.assertContains(r, "350,000"); self.assertContains(r, "Most popular"); self.assertContains(r, "US$240")
        r = self.client.get(reverse("faq"))
        self.assertContains(r, "Who owns the website or app?"); self.assertContains(r, "application/ld+json")
        self.assertContains(self.client.get(reverse("home")), "Sample")

    def test_unpublished_hidden_and_no_script_injection(self):
        FaqItem.objects.create(question="Hidden?", answer="x", is_published=False)
        FaqItem.objects.create(question="Shown?", answer="</script><script>alert(1)</script>")
        Testimonial.objects.create(name="A", quote="q", is_published=False)
        r = self.client.get(reverse("faq"))
        self.assertNotContains(r, "Hidden?")
        self.assertNotIn("</script><script>alert(1)", r.content.decode())

    def test_process_uses_real_settings(self):
        r = self.client.get(reverse("how_we_work"))
        self.assertContains(r, "40%"); self.assertContains(r, "14 days")
