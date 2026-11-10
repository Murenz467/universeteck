from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from accounts.models import StaffTOTP


class Command(BaseCommand):
    help = "Remove a staff member's two-factor device (lost phone and recovery codes). They set it up again at next sign-in."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **o):
        try:
            u = get_user_model().objects.get(username=o["username"])
        except get_user_model().DoesNotExist:
            raise CommandError("No such user.")
        n, _ = StaffTOTP.objects.filter(user=u).delete()
        self.stdout.write(self.style.SUCCESS(f"2FA reset for {u.username}." if n else "That user had no 2FA device."))
