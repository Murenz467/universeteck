"""ONE command that prepares everything, in the right order. Safe to run any time (nothing is deleted or overwritten)."""
import sys
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create/upgrade the database, add starter content and make sure an admin account exists."

    def add_arguments(self, parser):
        parser.add_argument("--no-input", action="store_true", help="Never ask questions (for servers and tests).")
        parser.add_argument("--if-empty", action="store_true", help="Do the starter content only on a brand-new database (safe to run on every deploy).")
        parser.add_argument("--production", action="store_true", help="Live site: no sample testimonials or sample client names.")

    def handle(self, *args, **opts):
        prod = opts["production"]
        if opts["if_empty"]:
            call_command("migrate", verbosity=0)
            from services.models import ServiceCategory
            if ServiceCategory.objects.exists():
                self.stdout.write("Site already set up. Nothing to add.")
                self._admin(opts)
                return
        steps = [("Preparing the database", "migrate", {"verbosity": 0}),
                 ("Adding the services", "seed_services", {})]
        steps.append(("Adding the portfolio projects", "seed_portfolio", {}))
        steps.append(("Adding pricing and FAQ" if prod else "Adding pricing, FAQ and testimonials", "seed_trust",
                      {"no_samples": True} if prod else {}))
        steps = [(f"{i}/{len(steps)}  {t}", c, k) for i, (t, c, k) in enumerate(steps, 1)]
        for label, cmd, kw in steps:
            self.stdout.write(self.style.MIGRATE_HEADING(label))
            call_command(cmd, stdout=self.stdout, stderr=self.stderr, **kw)
        self._admin(opts)
        from django.conf import settings
        self.stdout.write(self.style.SUCCESS(f"\nAll set. Site: {settings.SITE_URL}   Admin: {settings.SITE_URL}/{settings.ADMIN_URL}"))

    def _admin(self, opts):
        """Make sure an admin account exists. On a server, set DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD for the
        first deploy, then delete those three variables."""
        import os
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            if os.environ.get("DJANGO_SUPERUSER_USERNAME") and os.environ.get("DJANGO_SUPERUSER_PASSWORD"):
                call_command("createsuperuser", interactive=False)
                self.stdout.write(self.style.SUCCESS("Admin account created. Now delete the DJANGO_SUPERUSER_* variables."))
                return
            if opts["no_input"] or not sys.stdin.isatty():
                self.stdout.write(self.style.WARNING("No admin account yet. Create one with:  python manage.py createsuperuser"))
            else:
                self.stdout.write(self.style.MIGRATE_HEADING("Create your admin account (you only do this once)"))
                call_command("createsuperuser")
