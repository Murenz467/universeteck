from django.core.management.base import BaseCommand
from accounts.roles import ROLES, sync_roles


class Command(BaseCommand):
    help = "Create or refresh the least-privilege staff groups (Sales, Project Manager, Finance, Support, Content Editor)."

    def handle(self, *a, **o):
        sync_roles()
        self.stdout.write(self.style.SUCCESS("Roles ready: " + ", ".join(ROLES)))
