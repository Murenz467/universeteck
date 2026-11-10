"""End-to-end test of the client journey: lead -> proposal -> contract -> project -> milestones -> invoices."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from billing.models import Invoice
from contracts.models import Contract
from notifications.models import Notification
from projects.models import Project
from proposals.models import Proposal, ProposalPhase
from proposals import services as proposal_services
from contracts import services as contract_services
from quotes.models import QuoteRequest

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", SITE_URL="http://testserver")
class JourneyTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("boss", "boss@ut.rw", "pw12345678", is_staff=True, is_superuser=True)
        self.client_user = User.objects.create_user("amina", "amina@x.rw", "pw12345678", first_name="Amina")
        self.other = User.objects.create_user("eve", "eve@x.rw", "pw12345678")
        p = Proposal.objects.create(client=self.client_user, title="Website for Amina Ltd", summary="A site.",
                                    scope="Five pages.", deliverables="Design\nWebsite", deposit_percent=30)
        ProposalPhase.objects.create(proposal=p, title="Design", duration_days=7, amount=300000, order=0)
        ProposalPhase.objects.create(proposal=p, title="Build", duration_days=14, amount=700000, order=1)
        self.p = p

    # ---- helpers
    def login(self, user):
        self.client.force_login(user)

    def test_full_journey(self):
        # 1. staff sends proposal -> client notified (in-app + email)
        proposal_services.send_proposal(self.p)
        self.p.refresh_from_db()
        self.assertEqual((self.p.status, self.p.number), ("sent", f"UT-P-{self.p.pk:04d}"))
        self.assertTrue(Notification.objects.filter(user=self.client_user, kind="proposal").exists())
        self.assertTrue(any("amina@x.rw" in m.to for m in mail.outbox))

        # strangers cannot see it; the client can, and opening it notifies staff
        self.login(self.other)
        self.assertEqual(self.client.get(reverse("proposal", args=[self.p.pk])).status_code, 404)
        self.login(self.client_user)
        r = self.client.get(reverse("proposal", args=[self.p.pk]))
        self.assertContains(r, "1,000,000 RWF")
        self.assertContains(r, "300,000 RWF")      # deposit 30%
        self.p.refresh_from_db()
        self.assertIsNotNone(self.p.viewed_at)
        self.assertTrue(Notification.objects.filter(user=self.staff, message__contains="opened proposal").exists())

        # 2. client accepts -> draft contract exists but is hidden from the client
        self.client.post(reverse("proposal_respond", args=[self.p.pk]), {"action": "accept"})
        self.p.refresh_from_db()
        self.assertEqual(self.p.status, "accepted")
        c = self.p.contract
        self.assertEqual((c.status, c.total_amount), ("draft", 1000000))
        self.assertIn("Phase 1: Design", c.body)
        self.assertEqual(self.client.get(reverse("contract", args=[c.pk])).status_code, 404)

        # 3. staff sends contract; client signs; project + deposit invoice appear
        contract_services.send_contract(c)
        r = self.client.get(reverse("contract", args=[c.pk]))
        self.assertContains(r, "Sign this contract")
        bad = self.client.post(reverse("contract_sign", args=[c.pk]), {"signed_name": "Amina K"})  # no agree box
        c.refresh_from_db(); self.assertEqual(c.status, "sent")
        self.client.post(reverse("contract_sign", args=[c.pk]), {"signed_name": "Amina Uwase", "agree": "1"},
                         REMOTE_ADDR="10.1.2.3")
        c.refresh_from_db()
        self.assertEqual((c.status, c.signed_name, c.signed_ip), ("signed", "Amina Uwase", "10.1.2.3"))
        self.assertTrue(c.integrity_ok)
        project = Project.objects.get(contract=c)
        self.assertEqual(project.milestones.count(), 2)
        self.assertEqual(project.target_date, project.start_date + timedelta(days=21))
        dep = Invoice.objects.get(project=project, kind="deposit")
        self.assertEqual((dep.total, dep.status), (300000, "sent"))

        # signed text can't be tampered with unnoticed
        Contract.objects.filter(pk=c.pk).update(body=c.body + "\nExtra clause")
        c.refresh_from_db(); self.assertFalse(c.integrity_ok)
        Contract.objects.filter(pk=c.pk).update(body=c.body.replace("\nExtra clause", ""))

        # 4. client reports payment, staff confirms -> receipt
        self.client.post(reverse("invoice_pay", args=[dep.pk]), {"method": "momo", "reference": "MP123"})
        dep.refresh_from_db(); self.assertEqual(dep.status, "submitted")
        from billing import services as bs
        bs.mark_paid(dep); dep.refresh_from_db()
        self.assertEqual(dep.status, "paid")
        self.assertContains(self.client.get(reverse("invoice", args=[dep.pk])), "PAID")

        # 5. staff works through phases; client sees notifications + timeline
        m1, m2 = list(project.milestones.all())
        m1.status = "in_progress"; m1.save()
        project.refresh_from_db(); self.assertEqual(project.status, "in_progress")
        m1.status = "ready"; m1.save()
        self.assertTrue(Notification.objects.filter(user=self.client_user, message__contains="Ready for your approval").exists())
        # client asks for changes, staff fixes, client approves
        self.client.post(reverse("milestone_changes", args=[m1.pk]), {"comment": "Make logo bigger"})
        m1.refresh_from_db(); self.assertEqual((m1.status, m1.client_feedback), ("changes", "Make logo bigger"))
        m1.status = "ready"; m1.save()
        self.client.post(reverse("approve_milestone", args=[m1.pk]))
        m1.refresh_from_db(); self.assertEqual(m1.status, "approved")
        inv1 = m1.invoice                              # 300,000 - 30% credit = 210,000
        self.assertEqual(inv1.total, 210000)
        # another client can't approve it / other client can't open project
        self.login(self.other)
        self.assertEqual(self.client.get(reverse("project", args=[project.pk])).status_code, 404)
        self.login(self.client_user)

        # last phase: total billed always equals the contract
        m2.status = "ready"; m2.save()
        self.client.post(reverse("approve_milestone", args=[m2.pk]))
        project.refresh_from_db()
        self.assertEqual(project.status, "completed")
        billed = sum(i.total for i in project.invoices.all())
        self.assertEqual(billed, 1000000)
        r = self.client.get(reverse("project", args=[project.pk]))
        self.assertContains(r, "100% complete")
        self.assertContains(r, "Approved: Build")

        # dashboard and lists render
        for name in ["dashboard", "project_list", "proposal_list", "contract_list", "invoice_list", "notifications",
                     "profile"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_changes_decline_and_expiry(self):
        proposal_services.send_proposal(self.p)
        self.login(self.client_user)
        self.client.post(reverse("proposal_respond", args=[self.p.pk]), {"action": "changes", "comment": ""})
        self.p.refresh_from_db(); self.assertEqual(self.p.status, "sent")      # comment required
        self.client.post(reverse("proposal_respond", args=[self.p.pk]), {"action": "changes", "comment": "Cheaper"})
        self.p.refresh_from_db(); self.assertEqual(self.p.status, "changes")
        proposal_services.send_proposal(self.p); self.p.refresh_from_db()
        self.assertEqual((self.p.status, self.p.version), ("sent", 2))
        Proposal.objects.filter(pk=self.p.pk).update(valid_until=timezone.localdate() - timedelta(days=1))
        self.client.post(reverse("proposal_respond", args=[self.p.pk]), {"action": "accept"})
        self.p.refresh_from_db(); self.assertEqual(self.p.status, "sent")      # expired: cannot accept

    def test_private_files_and_staff_preview(self):
        proposal_services.send_proposal(self.p)
        self.login(self.staff)
        self.assertEqual(self.client.get(reverse("proposal", args=[self.p.pk])).status_code, 200)   # preview ok
        self.assertContains(self.client.get(reverse("staff_dashboard")), "Proposals awaiting reply")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("proposal", args=[self.p.pk])).status_code, 302)    # login required
        self.assertEqual(self.client.get("/media/private/deliverables/x.pdf").status_code, 404)      # never public

    def test_email_opt_out_and_invite(self):
        self.client_user.profile.email_notifications = False
        self.client_user.profile.save()
        mail.outbox.clear()
        proposal_services.send_proposal(self.p)
        self.assertEqual([m for m in mail.outbox if "amina@x.rw" in m.to], [])               # no email...
        self.assertTrue(Notification.objects.filter(user=self.client_user).exists())          # ...still in-app
        from accounts.utils import get_or_invite_client
        lead = QuoteRequest.objects.create(name="Jean Claude", email="jc@x.rw", details="App")
        user, created = get_or_invite_client(lead)
        self.assertTrue(created and not user.has_usable_password())
        self.assertTrue(any("jc@x.rw" in m.to for m in mail.outbox))

    def test_public_pages(self):
        for name in ["home", "about", "pricing", "faq", "how_we_work", "services", "portfolio", "contact", "quote", "terms", "privacy", "login", "register",
                     "password_reset"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get("/robots.txt").status_code, 200)
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("root", "root@ut.rw", "pw12345678")
        self.cl = User.objects.create_user("ben", "ben@x.rw", "pw12345678")
        self.client.force_login(self.admin)

    def test_admin_pages_render(self):
        for model in ["proposals_proposal", "contracts_contract", "billing_invoice", "projects_project",
                      "projects_milestone", "notifications_notification", "quotes_quoterequest"]:
            self.assertEqual(self.client.get(reverse(f"admin:{model}_changelist")).status_code, 200, model)
        for model in ["proposals_proposal", "billing_invoice", "projects_project"]:
            self.assertEqual(self.client.get(reverse(f"admin:{model}_add")).status_code, 200, model)

    def test_admin_send_flows(self):
        # create a proposal through the admin form with phases, set status=sent -> client is notified once items exist
        data = {"client": self.cl.pk, "title": "App", "status": "sent", "deposit_percent": 30,
                "payment_terms": "x", "valid_until": "2030-01-01",
                "phases-TOTAL_FORMS": 1, "phases-INITIAL_FORMS": 0, "phases-MIN_NUM_FORMS": 0,
                "phases-MAX_NUM_FORMS": 1000, "phases-0-title": "Build", "phases-0-duration_days": 10,
                "phases-0-amount": 500000, "phases-0-order": 0}
        r = self.client.post(reverse("admin:proposals_proposal_add"), data)
        self.assertEqual(r.status_code, 302)
        p = Proposal.objects.get(title="App")
        self.assertEqual(p.status, "sent")
        self.assertEqual(p.total, 500000)
        self.assertTrue(Notification.objects.filter(user=self.cl, kind="proposal").exists())

        # admin action: send contract; invoice admin action: send + confirm
        p.status = "accepted"; p.save()
        c = contract_services.get_or_create_draft(p)
        self.client.post(reverse("admin:contracts_contract_changelist"),
                         {"action": "send_to_client", "_selected_action": [c.pk]})
        c.refresh_from_db(); self.assertEqual(c.status, "sent")
        self.assertEqual(self.client.get(reverse("admin:contracts_contract_change", args=[c.pk])).status_code, 200)

        inv = Invoice.objects.create(client=self.cl, title="Hosting")
        from billing.models import InvoiceItem
        InvoiceItem.objects.create(invoice=inv, description="Year", unit_price=60000)
        self.client.post(reverse("admin:billing_invoice_changelist"),
                         {"action": "send_invoices", "_selected_action": [inv.pk]})
        inv.refresh_from_db(); self.assertEqual(inv.status, "sent"); self.assertTrue(inv.due_date)
        self.client.post(reverse("admin:billing_invoice_changelist"),
                         {"action": "confirm_paid", "_selected_action": [inv.pk]})
        inv.refresh_from_db(); self.assertEqual(inv.status, "paid")

    def test_lead_to_proposal_action_and_reminders(self):
        lead = QuoteRequest.objects.create(name="Sam", email="sam@x.rw", details="Need a site")
        r = self.client.post(reverse("admin:quotes_quoterequest_changelist"),
                             {"action": "create_draft_proposal", "_selected_action": [lead.pk]}, follow=True)
        self.assertEqual(r.status_code, 200)
        lead.refresh_from_db()
        self.assertIsNotNone(lead.user)
        self.assertEqual(Proposal.objects.filter(client=lead.user, request=lead).count(), 1)
        from django.core.management import call_command
        call_command("send_reminders")


class SetupSiteTests(TestCase):
    def test_setup_site_is_repeatable(self):
        from django.core.management import call_command
        from services.models import ServiceCategory
        for _ in range(2):
            call_command("setup_site", "--no-input", verbosity=0)
        self.assertEqual(ServiceCategory.objects.count(), 4)


class DeployHelpers(TestCase):
    def test_healthz(self):
        r = self.client.get("/healthz")
        self.assertEqual(r.status_code, 200); self.assertEqual(r.content, b"ok")

    def test_setup_site_if_empty_does_not_overwrite(self):
        from django.core.management import call_command
        from services.models import ServiceCategory
        call_command("setup_site", "--production", "--no-input", "--if-empty", verbosity=0)
        ServiceCategory.objects.filter(slug="hosting-devops").update(name="My Edited Name")
        call_command("setup_site", "--production", "--no-input", "--if-empty", verbosity=0)
        self.assertEqual(ServiceCategory.objects.get(slug="hosting-devops").name, "My Edited Name")
