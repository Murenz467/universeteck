"""Check that real email works:   python manage.py send_test_email you@gmail.com"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send one test email using the current email settings."

    def add_arguments(self, parser):
        parser.add_argument("to", help="Address that should receive the test.")

    def handle(self, *args, **opts):
        self.stdout.write(f"Provider: {settings.EMAIL_PROVIDER}   From: {settings.DEFAULT_FROM_EMAIL}")
        try:
            n = send_mail("Universe Tech: email test", "If you can read this, your website can send email.",
                          settings.DEFAULT_FROM_EMAIL, [opts["to"]], fail_silently=False)
        except Exception as e:      # show the real reason (wrong key, domain not verified, ...)
            raise CommandError(f"Sending failed: {e}")
        self.stdout.write(self.style.SUCCESS(f"Sent {n} email to {opts['to']}. Check the inbox (and the spam folder)."))
