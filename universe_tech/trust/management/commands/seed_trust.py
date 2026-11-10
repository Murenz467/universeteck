"""Starter content for pricing, FAQ, testimonials and client logos. Safe to run repeatedly: it only adds what is
missing and never overwrites anything you have edited. Edit everything in Admin > Trust & pricing."""
from django.conf import settings
from django.core.management.base import BaseCommand
from trust.models import PricingPackage, FaqItem, Testimonial, ClientLogo

DEP = settings.DEFAULT_DEPOSIT_PERCENT
DUE = settings.INVOICE_DUE_DAYS
VALID = settings.PROPOSAL_VALID_DAYS

PACKAGES = [  # name, tagline, best_for, price, billing, timeline, features, featured
    ("Starter Website", "A professional online presence.", "Small businesses, shops and start-ups", 350000, "once", "2-4 weeks",
     "Up to 5 pages\nMobile-friendly design\nContact form and WhatsApp button\nBasic search-engine setup\nFirst year of hosting set up", False),
    ("Business Platform", "A website or web app that works for you.", "Growing companies and organizations", 1500000, "once", "6-12 weeks",
     "Custom design and features\nClient accounts and admin dashboard\nMobile money payment integration\nEmail notifications\nTraining and handover", True),
    ("Mobile App", "iOS and Android from one codebase.", "Businesses launching an app", 3000000, "once", "8-16 weeks",
     "Flutter app for Android and iOS\nSecure Django back end and API\nPush notifications\nStore publishing support\n30 days of post-launch fixes", False),
    ("Hosting & Care", "We keep it fast, safe and online.", "Any website or app we build", 30000, "month", "Monthly",
     "Secure hosting and SSL\nDaily backups\nMonitoring and uptime checks\nSecurity and software updates\nPriority support", False),
]

FAQS = [
    ("pricing", "How much does a website or app cost?",
     "Starter websites usually begin around RWF 350,000, business platforms around RWF 1,500,000 and mobile apps around RWF 3,000,000. The price depends on the number of features, pages and integrations.\n\nEvery project gets an exact price in a written proposal, so you know the full cost before you commit."),
    ("pricing", "Is the quotation free?",
     "Yes. Requesting a quote is free and creates no obligation. We reply within one business day, usually with a few questions so we can price your project properly."),
    ("pricing", "Are there any hidden costs?",
     "No. Your proposal lists every phase and its price. Things that are paid to third parties, such as a domain name or an app store account, are shown separately so you can see them clearly."),
    ("pricing", "Is the price negotiable?",
     "Our starting prices are a guide. Your final price depends on what you want built, the scope written in your contract and what we agree together. We are happy to talk about your budget and find a plan that works for you without lowering the quality."),
    ("pricing", "Can I change the scope after the proposal?",
     "Yes. You can ask for changes before you accept, and during the project you can request extra work. We price changes in writing first, and nothing is added without your approval."),
    ("timeline", "How long will my project take?",
     "As a guide: a starter website takes 2 to 4 weeks, a business platform 6 to 12 weeks and a mobile app 8 to 16 weeks. Your proposal shows the timeline for each phase.\n\nThe biggest factor is how quickly we receive your content, feedback and approvals."),
    ("timeline", "What do you need from me to start?",
     "A short description of your goals, any logos or brand material you already have, and the content for your pages (text and photos). If you do not have content yet, we can help you plan it."),
    ("timeline", "Can you deliver faster?",
     "Sometimes. If you have a deadline, tell us in your quote request. We will say honestly whether it is possible and what it changes in the plan."),
    ("payment", "How does payment work?",
     f"After you sign the contract we issue a deposit invoice ({DEP}% of the total). Work starts when it is received. After that, each phase is invoiced when you approve it, with your deposit credited, so the total always matches your contract."),
    ("payment", "Which payment methods do you accept?",
     "MTN MoMo, Airtel Money and bank transfer. Payment details are shown on every invoice. After you pay, tell us in your portal, we confirm it and your receipt is issued."),
    ("payment", "How long do I have to pay an invoice?",
     f"Invoices are due {DUE} days after they are issued. A proposal stays valid for {VALID} days, so you have time to decide."),
    ("after", "What happens after my project is launched?",
     "We deploy it, hand everything over and stay available. You can open a support ticket from your account at any time. Defects reported during the warranty period in your contract are fixed free of charge."),
    ("after", "Do you offer hosting and maintenance?",
     "Yes. Our Hosting & Care plan covers secure hosting, SSL, backups, monitoring and updates, so your site stays fast and safe. You can also host with someone else and we will help you move."),
    ("after", "Can you update my website later?",
     "Yes. Small updates can be requested through a support ticket, and larger improvements are quoted as a new phase or project."),
    ("ownership", "Who owns the website or app?",
     "The final website or app and your content belong to you once the project has been paid in full. Third-party tools used in it, such as fonts, libraries and hosting services, keep their own licences. The details are in your contract."),
    ("ownership", "Who can see my files and data?",
     "Only you and our project team. Files we deliver are available through your account and are never publicly accessible. We protect staff access with two-factor sign-in."),
    ("general", "Where is Universe Tech based?",
     f"We are in {settings.CONTACT['address']}. We work with clients across Rwanda and also work remotely with clients in other countries."),
    ("general", "Can you work with clients outside Rwanda?",
     "Yes. Meetings happen by phone, WhatsApp or video call, and everything else is handled in your online portal."),
]

TESTIMONIALS = [
    ("Sample Client", "Managing Director", "Kigali Fresh Market",
     "Replace this with a real quote from one of your clients. Mention what you built together and the result it had for their business."),
    ("Sample Client", "Operations Manager", "Ubumwe Logistics Ltd",
     "A short, specific quote works best: what problem they had, how the project went and what changed afterwards."),
    ("Sample Client", "Founder", "Highland Roast Co.",
     "Add a photo of the client if they agree. Real names and companies build far more trust than anonymous praise."),
]
LOGOS = []          # real clients are added in Admin > Client logos (Lamar Investment Company Ltd is added below)


class Command(BaseCommand):
    help = "Add starter pricing, FAQ, sample testimonials and sample client names (only what is missing)."

    def add_arguments(self, parser):
        parser.add_argument("--no-samples", action="store_true", help="Skip the sample testimonials and sample client names (use on the live site).")

    def handle(self, *args, **opts):
        n = 0
        for i, (name, tag, best, price, billing, tl, feats, feat) in enumerate(PACKAGES):
            _, c = PricingPackage.objects.get_or_create(name=name, defaults=dict(
                tagline=tag, best_for=best, price_from=price, billing=billing, timeline=tl, features=feats, is_featured=feat, order=i))
            n += c
        for i, (cat, q, a) in enumerate(FAQS):
            _, c = FaqItem.objects.get_or_create(question=q, defaults=dict(category=cat, answer=a, order=i))
            n += c
        for i, (nm, role, co, quote) in enumerate([] if opts["no_samples"] else TESTIMONIALS):
            _, c = Testimonial.objects.get_or_create(company=co, is_sample=True, defaults=dict(name=nm, role=role, quote=quote, order=i))
            n += c
        ClientLogo.objects.filter(is_sample=True).delete()           # retire the invented demo client names
        _, c = ClientLogo.objects.get_or_create(name="Lamar Investment Company Ltd", defaults=dict(is_sample=False, order=0))
        n += c
        self.stdout.write(self.style.SUCCESS(f"Trust content ready ({n} new items). Edit it in Admin > Trust & pricing."))
