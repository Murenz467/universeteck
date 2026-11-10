"""Add Universe Tech's real projects to the portfolio.

    python manage.py seed_portfolio            # adds any project that is missing (never overwrites your edits)
    python manage.py seed_portfolio --remove   # deletes these projects again

The text comes from Charles Murenzi's CV. Each project starts with a simple cover image made from its name and
technology. Replace it with a real screenshot in Admin > Case studies whenever you like.
"""
import shutil
from django.conf import settings
from django.core.management.base import BaseCommand
from services.models import ServiceCategory

SW, BR, WM, HO = "software-engineering", "branding-creative", "web-mobile-applications", "hosting-devops"
OLD_SAMPLES = ["sample-online-marketplace", "sample-ride-booking-app", "sample-coffee-brand", "sample-managed-hosting",
               "sample-hr-system", "sample-school-portal", "sample-restaurant-brand", "sample-cloud-deployment",
               "sample-customer-portal"]

PROJECTS = [  # slug, title, client, category, cover, summary, body
    ("lamar-investment-website", "Lamar Investment Company Website", "Lamar Investment Company Ltd", WM, "lamar-website",
     "A production website for a Kigali cleaning-services company, with a quote-request system, admin tools and an FAQ chatbot.",
     "Lamar Investment Company Ltd is a cleaning-services company in Kigali. We designed, built and launched its website from start to finish under a signed proposal.\n\n"
     "Visitors can send inquiries and quote requests, and the team manages partners, team members and inquiries from a simple admin interface. A rule-based FAQ chatbot answers common questions about services, service areas, quotes, health and safety, and bookings.\n\n"
     "The site runs on Railway with a custom domain, Cloudflare DNS, SSL and business email, and uses repeatable deployment and startup tasks so updates are safe and quick.\n\n"
     "Technology: Django, Railway, Cloudflare."),
    ("joblink-gig-marketplace", "JobLink: Hyperlocal Gig Marketplace", "", WM, "joblink",
     "A two-sided mobile marketplace that connects informal workers with clients across Rwanda, with mobile money and real-time chat.",
     "JobLink connects informal workers with people who need them. Matching follows Rwanda's own location hierarchy of Province, District, Sector, Cell and Village, so clients find help close to them.\n\n"
     "The platform includes MTN MoMo and Airtel Money payments, Firebase push notifications, Cloudinary media storage and real-time chat built on Django Channels. Workers are verified with a phone OTP, an ID and a selfie, and the app supports job workflows, reviews and dispute handling.\n\n"
     "A companion Django website gives staff a dashboard and a nearby-worker search that uses haversine distance. The backend runs on Railway and the Android app was prepared through the Google Play release pipeline.\n\n"
     "Technology: Flutter, Django REST Framework, Django Channels, Railway."),
    ("ishare-ride-sharing", "ISHARE: Ride-Sharing App", "", WM, "ishare",
     "A ride-sharing platform for the Rwandan market, with a Flutter app and a Django REST backend on Railway.",
     "ISHARE is a ride-sharing platform built for the Rwandan market, with a mobile app and a Django REST backend deployed on Railway.\n\n"
     "As part of release preparation we worked through Google Play Console policy requirements and closed gaps in the backend endpoints, so the app was ready to publish.\n\n"
     "Technology: Flutter, Django REST Framework, Railway."),
    ("lamar-brand-identity", "Brand Identity & Company Profile for Lamar", "Lamar Investment Company Ltd", BR, "lamar-brand",
     "A logo, brand guidelines, mockups and a company profile brochure for a Kigali cleaning-services company.",
     "Alongside the website, we produced the brand assets Lamar Investment Company Ltd needed to look professional everywhere: a logo, brand guidelines, mockups and a company profile brochure.\n\n"
     "The guidelines keep the look consistent across the website, print and everyday business materials."),
    ("lamar-deployment-email", "Deployment, Domain & Business Email for Lamar", "Lamar Investment Company Ltd", HO, "lamar-hosting",
     "Hosting on Railway with a custom domain, Cloudflare DNS, SSL and business email, set up so deployments are repeatable.",
     "We deployed Lamar's website on Railway and configured everything around it: the custom domain, Cloudflare DNS, SSL certificate and business email.\n\n"
     "Startup and deployment tasks are repeatable, so updates reach the live site the same way every time.\n\n"
     "Technology: Railway, Cloudflare DNS, SSL, business email."),
    ("smartjob-job-matching", "SmartJob: Job Matching Platform", "", SW, "smartjob",
     "A job-matching web platform with separate employer and job-seeker roles, application tracking, search and filtering.",
     "SmartJob serves two kinds of users. Employers post jobs and manage applications, while job seekers search, filter and apply.\n\n"
     "We implemented the two roles, application status management, search, filtering and pagination so large lists stay fast and easy to browse.\n\n"
     "Technology: Django."),
    ("autorent-fleetadmin", "AutoRent / FleetAdmin: Car Rental System", "", SW, "autorent",
     "A car-rental management system with socket-based notifications.",
     "AutoRent / FleetAdmin is a rental management system for a car-rental business, with socket-based notifications that keep users updated as things change.\n\n"
     "Technology: Java Swing, MySQL."),
]


class Command(BaseCommand):
    help = "Add (or with --remove, delete) Universe Tech's real portfolio projects."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true", help="Delete these projects.")

    def handle(self, *args, **opts):
        from portfolio.models import CaseStudy
        if opts["remove"]:
            n, _ = CaseStudy.objects.filter(slug__in=[p[0] for p in PROJECTS]).delete()
            self.stdout.write(self.style.SUCCESS(f"Removed {n} projects."))
            return
        if not ServiceCategory.objects.filter(slug=WM).exists():
            self.stderr.write("Service categories missing. Run: python manage.py seed_services")
            return
        CaseStudy.objects.filter(slug__in=OLD_SAMPLES).delete()      # the made-up demo projects are retired
        media = settings.MEDIA_ROOT / "portfolio"
        media.mkdir(parents=True, exist_ok=True)
        src = settings.BASE_DIR / "static" / "img" / "cases"
        added = 0
        for order, (slug, title, client, cat, cover, summary, body) in enumerate(PROJECTS):
            target = media / f"{cover}.jpg"
            if not target.exists():
                shutil.copyfile(src / f"{cover}.jpg", target)
            _, created = CaseStudy.objects.get_or_create(slug=slug, defaults={
                "title": title, "client_name": client, "summary": summary, "body": body,
                "category": ServiceCategory.objects.filter(slug=cat).first(),
                "image": f"portfolio/{cover}.jpg", "is_published": True, "order": order})
            added += created
        self.stdout.write(self.style.SUCCESS(f"Portfolio ready ({added} new, {len(PROJECTS)} projects in total)."))
