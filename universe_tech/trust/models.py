from django.db import models


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField("Job title", max_length=100, blank=True)
    company = models.CharField(max_length=120, blank=True)
    quote = models.TextField(max_length=500)
    photo = models.ImageField(upload_to="trust/people/", blank=True, help_text="Optional square photo.")
    rating = models.PositiveSmallIntegerField(default=5, help_text="1 to 5 stars.")
    is_sample = models.BooleanField(default=False, help_text="Tick for placeholder text. It is shown with a 'Sample' tag. "
                                    "Untick (or delete) once you have a real client quote.")
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]

    def __str__(self):
        return f"{self.name} ({self.company})" if self.company else self.name

    @property
    def stars(self):
        return range(max(0, min(5, self.rating)))


class ClientLogo(models.Model):
    name = models.CharField(max_length=120)
    logo = models.ImageField(upload_to="trust/logos/", blank=True,
                             help_text="PNG/JPG/WebP with a plain or transparent background. Without a logo the name is shown as text.")
    website = models.URLField(blank=True)
    is_sample = models.BooleanField(default=False, help_text="Placeholder name. Delete it when you add real clients.")
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class FaqItem(models.Model):
    CATEGORIES = [("pricing", "Pricing"), ("timeline", "Timelines"), ("payment", "Payments"),
                  ("after", "After launch"), ("ownership", "Ownership & rights"), ("general", "General")]
    category = models.CharField(max_length=12, choices=CATEGORIES, default="general")
    question = models.CharField(max_length=200)
    answer = models.TextField(help_text="Plain text. A blank line starts a new paragraph.")
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category", "order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class PricingPackage(models.Model):
    BILLING = [("once", "one-time"), ("month", "per month")]
    name = models.CharField(max_length=80)
    tagline = models.CharField(max_length=160, blank=True)
    best_for = models.CharField(max_length=160, blank=True, help_text="e.g. Small businesses and start-ups")
    price_from = models.PositiveIntegerField(help_text="Starting price in RWF. Shown as 'From RWF ...'.")
    billing = models.CharField(max_length=5, choices=BILLING, default="once")
    timeline = models.CharField(max_length=60, blank=True, help_text="e.g. 2-4 weeks")
    features = models.TextField(help_text="One feature per line.")
    is_featured = models.BooleanField(default=False, help_text="Highlights the package as the most popular.")
    cta_label = models.CharField(max_length=40, default="Get a Quote")
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "price_from"]

    def __str__(self):
        return self.name

    @property
    def icon(self):
        n = self.name.lower()
        if "mobile" in n or "app" in n:
            return "i-bolt"
        if "host" in n or "care" in n or "support" in n:
            return "i-headset"
        if "business" in n or "platform" in n:
            return "i-users"
        return "i-bulb"

    @property
    def feature_list(self):
        return [ln.strip() for ln in self.features.splitlines() if ln.strip()]
