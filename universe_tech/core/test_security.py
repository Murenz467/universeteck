"""Security regression tests: least privilege, 2FA, lockouts, headers, uploads, IP handling."""
import re
import subprocess
import sys
import time
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

from accounts import totp
from accounts.models import StaffTOTP
from accounts.roles import sync_roles
from billing.models import Invoice, InvoiceItem
from contracts.models import Contract
from core.models import AuditEvent
from core.utils import client_ip
from core.validators import validate_upload
from notifications.models import Notification
from proposals.models import Proposal

User = get_user_model()


class Base(TestCase):
    def setUp(self):
        cache.clear()
        sync_roles()
        self.owner = User.objects.create_superuser("owner", "o@ut.rw", "Str0ng-pass-123")
        self.cust = User.objects.create_user("cust", "c@x.rw", "Str0ng-pass-123")
        self.p = Proposal.objects.create(client=self.cust, title="Secret deal", status="sent")
        self.c = Contract.objects.create(client=self.cust, title="Secret contract", body="x", status="sent")
        self.inv = Invoice.objects.create(client=self.cust, title="Secret invoice", status="sent")
        InvoiceItem.objects.create(invoice=self.inv, description="d", unit_price=1000)

    def staff(self, group, name=None):
        u = User.objects.create_user(name or group.replace(" ", "").lower(), f"{group[:3]}@ut.rw", "Str0ng-pass-123",
                                     is_staff=True)
        u.groups.add(Group.objects.get(name=group))
        return u


class LeastPrivilege(Base):
    def test_roles_exist_and_have_no_delete_on_legal_or_money_records(self):
        for name in ["Sales", "Project Manager", "Finance", "Support", "Content Editor"]:
            self.assertTrue(Group.objects.filter(name=name).exists(), name)
        perms = {p.codename for g in Group.objects.all() for p in g.permissions.all()}
        for forbidden in ["delete_contract", "delete_invoice", "delete_proposal", "delete_user", "add_user",
                          "change_user", "delete_auditevent", "change_auditevent"]:
            self.assertNotIn(forbidden, perms)

    def test_staff_without_role_sees_nothing(self):
        u = User.objects.create_user("nobody", "n@ut.rw", "Str0ng-pass-123", is_staff=True)
        self.client.force_login(u)
        for name in ["proposals_proposal", "contracts_contract", "billing_invoice", "quotes_quoterequest"]:
            self.assertEqual(self.client.get(reverse(f"admin:{name}_changelist")).status_code, 403, name)
        for name in ["proposal", "contract", "invoice"]:
            pk = {"proposal": self.p.pk, "contract": self.c.pk, "invoice": self.inv.pk}[name]
            self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 404, name)

    def test_each_role_sees_only_its_area(self):
        sales, fin, sup = self.staff("Sales"), self.staff("Finance"), self.staff("Support")
        self.client.force_login(sales)
        self.assertEqual(self.client.get(reverse("admin:proposals_proposal_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:billing_invoice_changelist")).status_code, 403)
        self.assertEqual(self.client.get(reverse("invoice", args=[self.inv.pk])).status_code, 404)
        self.client.force_login(fin)
        self.assertEqual(self.client.get(reverse("admin:billing_invoice_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("invoice", args=[self.inv.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:proposals_proposal_add")).status_code, 403)   # view only
        self.client.force_login(sup)
        self.assertEqual(self.client.get(reverse("proposal", args=[self.p.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("admin:support_ticket_changelist")).status_code, 200)

    def test_nobody_but_superuser_can_delete_contracts_or_manage_users(self):
        pm = self.staff("Project Manager")
        self.client.force_login(pm)
        r = self.client.post(reverse("admin:contracts_contract_delete", args=[self.c.pk]), {"post": "yes"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:auth_user_changelist")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:auth_group_changelist")).status_code, 403)

    def test_user_admin_cannot_escalate(self):
        from django.contrib.auth.models import Permission
        mgr = self.staff("Support", "hr")
        mgr.user_permissions.add(*Permission.objects.filter(codename__in=["view_user", "change_user"]))
        self.client.force_login(mgr)
        listing = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(listing, "owner")                           # superusers hidden
        self.assertEqual(self.client.get(reverse("admin:auth_user_change", args=[self.owner.pk])).status_code, 302)
        # trying to promote a normal client is ignored: the fields are read-only for non-superusers
        self.client.post(reverse("admin:auth_user_change", args=[self.cust.pk]), {
            "username": "cust", "email": "c@x.rw", "is_superuser": "on", "is_staff": "on", "is_active": "on",
            "date_joined_0": "2026-01-01", "date_joined_1": "00:00:00"})
        self.cust.refresh_from_db()
        self.assertFalse(self.cust.is_superuser or self.cust.is_staff)

    def test_audit_log_is_read_only(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("admin:core_auditevent_changelist")).status_code, 200)
        ev = AuditEvent.objects.create(action="x")
        self.assertEqual(self.client.get(reverse("admin:core_auditevent_change", args=[ev.pk])).status_code, 200)
        r = self.client.post(reverse("admin:core_auditevent_delete", args=[ev.pk]), {"post": "yes"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:core_auditevent_add")).status_code, 403)


class LoginProtection(Base):
    def test_lockout_after_failures_even_with_correct_password(self):
        for _ in range(5):
            r = self.client.post(reverse("login"), {"username": "cust", "password": "wrong"})
            self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse("login"), {"username": "cust", "password": "Str0ng-pass-123"})
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r["Retry-After"], "900")
        self.assertTrue(AuditEvent.objects.filter(action="login_blocked").exists())
        self.assertEqual(AuditEvent.objects.filter(action="login_failed").count(), 5)

    def test_success_resets_counter_and_other_users_unaffected(self):
        for _ in range(3):
            self.client.post(reverse("login"), {"username": "cust", "password": "wrong"})
        r = self.client.post(reverse("login"), {"username": "cust", "password": "Str0ng-pass-123"})
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "ghost", "password": "wrong"})
        self.assertEqual(self.client.post(reverse("login"), {"username": "owner", "password": "Str0ng-pass-123"}).status_code, 302)

    def test_admin_login_is_locked_too(self):
        url = "/admin/login/"
        for _ in range(5):
            self.client.post(url, {"username": "owner", "password": "bad", "next": "/admin/"})
        self.assertEqual(self.client.post(url, {"username": "owner", "password": "Str0ng-pass-123", "next": "/admin/"}).status_code, 429)

    def test_password_reset_and_register_throttled(self):
        for _ in range(5):
            self.client.post(reverse("password_reset"), {"email": "c@x.rw"})
        self.assertEqual(self.client.post(reverse("password_reset"), {"email": "c@x.rw"}).status_code, 429)

    def test_password_policy_and_hasher(self):
        self.assertTrue(self.cust.password.startswith("argon2"))
        r = self.client.post(reverse("register"), {"username": "newb", "first_name": "N", "email": "n@x.rw",
                                                   "password1": "12345678", "password2": "12345678"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newb").exists())


@override_settings(STAFF_2FA_REQUIRED=True)
class TwoFactor(Base):
    def test_staff_must_complete_2fa(self):
        self.client.force_login(self.owner)
        r = self.client.get("/staff/")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r["Location"].startswith(reverse("two_factor")))
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.assertEqual(self.client.get(reverse("proposal", args=[self.p.pk])).status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)       # ordinary pages unaffected

    def test_setup_verify_replay_and_recovery(self):
        self.client.force_login(self.owner)
        page = self.client.get(reverse("two_factor"))
        self.assertContains(page, "<svg")                                    # QR code
        dev = StaffTOTP.objects.get(user=self.owner)
        self.assertFalse(dev.confirmed)
        r = self.client.post(reverse("two_factor"), {"code": "000000", "next": "/staff/"})
        self.assertEqual(r.status_code, 200); dev.refresh_from_db(); self.assertFalse(dev.confirmed)
        now = time.time()
        r = self.client.post(reverse("two_factor"), {"code": totp.current_code(dev.secret, now), "next": "/staff/"})
        self.assertContains(r, "recovery codes")                              # shown once
        codes = re.findall(r"<code>([0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4})</code>", r.content.decode())
        self.assertEqual(len(codes), 8)
        self.assertEqual(self.client.get("/staff/").status_code, 200)         # now allowed
        self.assertEqual(self.client.get("/admin/").status_code, 200)

        # new browser: login again -> must verify; the SAME code cannot be replayed
        c2 = self.client_class(); c2.force_login(self.owner)
        r = c2.post(reverse("two_factor"), {"code": totp.current_code(dev.secret, now), "next": "/staff/"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(c2.get("/staff/").status_code, 302)
        r = c2.post(reverse("two_factor"), {"code": totp.current_code(dev.secret, now + 30), "next": "/staff/"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(c2.get("/staff/").status_code, 200)

        # recovery code works exactly once
        c3 = self.client_class(); c3.force_login(self.owner)
        self.assertEqual(c3.post(reverse("two_factor"), {"code": codes[0], "next": "/staff/"}).status_code, 302)
        c4 = self.client_class(); c4.force_login(self.owner)
        self.assertEqual(c4.post(reverse("two_factor"), {"code": codes[0]}).status_code, 200)
        self.assertEqual(c4.get("/staff/").status_code, 302)

    def test_guessing_codes_is_throttled(self):
        self.client.force_login(self.owner)
        self.client.get(reverse("two_factor"))
        for _ in range(5):
            self.client.post(reverse("two_factor"), {"code": "123456"})
        self.assertEqual(self.client.post(reverse("two_factor"), {"code": "123456"}).status_code, 429)

    def test_2fa_flag_belongs_to_one_user(self):
        other = User.objects.create_user("o2", "o2@ut.rw", "Str0ng-pass-123", is_staff=True)
        self.client.force_login(self.owner)
        s = self.client.session; s["ut_2fa"] = {"uid": other.pk, "at": time.time()}; s.save()
        self.assertEqual(self.client.get("/staff/").status_code, 302)

    def test_totp_rfc_vector(self):
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"          # RFC 6238 test key "12345678901234567890"
        self.assertEqual(totp.current_code(secret, 59), "287082")
        self.assertEqual(totp.current_code(secret, 1111111109), "081804")


class IdleAndHeaders(Base):
    def test_staff_idle_timeout_logs_out(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get("/staff/").status_code, 200)
        s = self.client.session; s["ut_last"] = time.time() - 3 * 3600; s.save()
        r = self.client.get("/staff/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_security_headers(self):
        r = self.client.get("/")
        csp = r["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp); self.assertNotIn("script-src 'self' 'unsafe", csp)
        self.assertIn("frame-ancestors 'none'", csp); self.assertIn("object-src 'none'", csp)
        self.assertEqual(r["X-Frame-Options"], "DENY"); self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertIn("camera=()", r["Permissions-Policy"])
        self.assertEqual(r["Referrer-Policy"], "same-origin")
        self.client.force_login(self.cust)
        self.assertIn("no-store", self.client.get(reverse("dashboard"))["Cache-Control"])

    def test_pages_have_no_inline_scripts_or_handlers(self):
        """CSP forbids inline JS, so every page we ship must be free of it (otherwise features silently break)."""
        self.client.force_login(self.owner)
        urls = ["/", "/about/", "/services/", "/portfolio/", "/contact/", "/quote/", "/accounts/login/", "/accounts/register/",
                reverse("dashboard"), reverse("proposal", args=[self.p.pk]), reverse("contract", args=[self.c.pk]),
                reverse("invoice", args=[self.inv.pk]), "/staff/", "/admin/", "/admin/proposals/proposal/",
                "/admin/billing/invoice/add/", "/admin/auth/user/", "/admin/contracts/contract/%d/change/" % self.c.pk]
        for u in urls:
            html = self.client.get(u).content.decode()
            self.assertEqual(self.client.get(u).status_code, 200, u)
            self.assertFalse(re.search(r"<script(?![^>]*\bsrc=)", html), f"inline <script> on {u}")
            self.assertFalse(re.search(r"\son(click|load|submit|change|error)=", html), f"inline handler on {u}")

    def test_bad_host_header_rejected(self):
        self.assertEqual(self.client.get("/", HTTP_HOST="evil.example").status_code, 400)

    def test_open_redirect_blocked(self):
        self.client.force_login(self.cust)
        n = Notification.objects.create(user=self.cust, message="x", url="//evil.example/steal")
        r = self.client.get(reverse("notification_open", args=[n.pk]))
        self.assertTrue(r["Location"].endswith("/notifications/"), r["Location"])
        r = self.client.post(reverse("login") + "?next=//evil.example", {"username": "cust", "password": "Str0ng-pass-123", "next": "//evil.example"})
        self.assertNotIn("evil.example", r["Location"])


class MiscHardening(Base):
    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_client_ip_ignores_forged_forwarded_for(self):
        rf = RequestFactory()
        req = rf.get("/", HTTP_X_FORWARDED_FOR="6.6.6.6, 41.186.1.2", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(client_ip(req), "41.186.1.2")                      # attacker-added 6.6.6.6 is ignored
        with override_settings(TRUSTED_PROXY_COUNT=0):
            self.assertEqual(client_ip(req), "10.0.0.1")

    def test_upload_validation(self):
        validate_upload(SimpleUploadedFile("plan.pdf", b"%PDF-1.4 hello"))
        for name, data in [("evil.exe", b"MZ"), ("shell.php", b"<?php"), ("page.html", b"<script>"),
                           ("pic.svg", b"<svg onload=1>"), ("fake.pdf", b"MZ not a pdf"), ("noext", b"x")]:
            with self.assertRaises(ValidationError, msg=name):
                validate_upload(SimpleUploadedFile(name, data))
        with override_settings(MAX_UPLOAD_MB=1):
            with self.assertRaises(ValidationError):
                validate_upload(SimpleUploadedFile("big.pdf", b"%PDF" + b"0" * (1024 * 1024 + 1)))

    def test_email_subject_cannot_inject_headers(self):
        from django.core import mail
        from notifications.utils import notify_staff
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            notify_staff("Hello\r\nBcc: attacker@evil.example", "body")
            self.assertTrue(mail.outbox)
            self.assertNotIn("\n", mail.outbox[0].subject)

    def test_server_refuses_to_start_without_secret_key(self):
        env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "DEBUG": "0", "DJANGO_SETTINGS_MODULE": "config.settings"}
        out = subprocess.run([sys.executable, "-c", "import django; django.setup()"], env=env,
                             capture_output=True, text=True, cwd=".")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("SECRET_KEY is not set", out.stderr)

    def test_private_media_is_never_public(self):
        for p in ["/media/private/deliverables/a.pdf", "/media/private/projectupdates/a.pdf", "/media/db.sqlite3"]:
            self.assertEqual(self.client.get(p).status_code, 404, p)

    def test_strangers_cannot_reach_other_clients_records(self):
        other = User.objects.create_user("mallory", "m@x.rw", "Str0ng-pass-123")
        self.client.force_login(other)
        for name, pk in [("proposal", self.p.pk), ("contract", self.c.pk), ("invoice", self.inv.pk)]:
            self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 404, name)
        self.assertEqual(self.client.post(reverse("contract_sign", args=[self.c.pk]),
                                          {"signed_name": "Mallory X", "agree": "1"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("invoice_pay", args=[self.inv.pk]),
                                          {"method": "momo", "reference": "x"}).status_code, 404)
        self.c.refresh_from_db(); self.assertEqual(self.c.status, "sent")
