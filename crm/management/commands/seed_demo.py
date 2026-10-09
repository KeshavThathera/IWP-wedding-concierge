from django.core.management.base import BaseCommand

from crm.seed import DEMO_EMAIL, DEMO_PASSWORD, DEMO_USERNAME, seed_demo


class Command(BaseCommand):
    help = "Replace CRM data with the fictional demo conversations and leads, and create the demo staff user."

    def handle(self, *args, **options):
        seed_demo()
        self.stdout.write(self.style.SUCCESS(f"Demo data loaded. Staff login: {DEMO_USERNAME} / {DEMO_PASSWORD} ({DEMO_EMAIL})"))
