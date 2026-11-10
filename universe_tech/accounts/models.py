from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=120, blank=True)
    email_notifications = models.BooleanField(
        "Email me about my projects", default=True,
        help_text="You always see alerts on the website. This controls the extra email copy.")

    def __str__(self):
        return f"Profile of {self.user}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


def get_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


class StaffTOTP(models.Model):
    """Authenticator-app device for a staff member (two-factor sign-in) plus single-use recovery codes."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totp")
    secret = models.CharField(max_length=40)
    confirmed = models.BooleanField(default=False)
    last_step = models.BigIntegerField(default=0)
    recovery_hashes = models.TextField(blank=True)      # JSON list of SHA-256 hashes; plain codes are shown only once
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"2FA for {self.user} ({'on' if self.confirmed else 'pending'})"
