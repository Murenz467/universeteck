from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from portfolio.models import CaseStudy


class StaticSitemap(Sitemap):
    priority, changefreq = 0.8, "monthly"

    def items(self):
        return ["home", "about", "services", "pricing", "how_we_work", "faq", "portfolio", "contact", "quote"]

    def location(self, name):
        return reverse(name)


class CaseSitemap(Sitemap):
    priority = 0.6

    def items(self):
        return CaseStudy.objects.filter(is_published=True)

    def location(self, obj):
        return reverse("case_detail", args=[obj.slug])


SITEMAPS = {"static": StaticSitemap, "cases": CaseSitemap}
