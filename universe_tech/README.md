# Universe Tech platform

Public website + client portal + staff tools, built with Django.

## START HERE (the easy way)
**Windows:** double-click **`START_WINDOWS.bat`**. **Mac/Linux:** run `bash start_mac_linux.sh`.

That one file does everything, in the right order:
1. installs what the site needs  2. prepares the database  3. adds the services, your real portfolio projects, pricing and FAQ
4. asks you **once** to create your admin username and password  5. starts the website and opens it in your browser.

Next time, double-click the same file again. Nothing is deleted. Stop the site with `Ctrl+C`.

| Where | Address |
|---|---|
| Website | http://127.0.0.1:8000 |
| Admin (edit pricing, FAQ, portfolio, testimonials) | http://127.0.0.1:8000/admin/ |
| Staff dashboard | http://127.0.0.1:8000/staff/ |

## Put it online
See **DEPLOY.md** for the full, step-by-step Railway guide (database, uploads volume, email, domain, backups).

## Run locally (the manual way)
Debug mode is OFF by default (secure). For local work copy `.env.example` to `.env` (it contains `DEBUG=1`), or run commands as `DEBUG=1 python manage.py ...`.
```
pip install -r requirements.txt
python manage.py setup_site           # migrate + starter content + admin account, in the right order
python manage.py runserver
python manage.py test                 # runs the end-to-end tests
```

## How a project flows
1. **Lead** – visitor sends the quote form (spam-protected). Staff are alerted; the visitor gets a confirmation email.
2. **Proposal** – Admin > Quote requests > action *Create draft PROPOSAL*. This also creates the client account
   (and emails a set-password link) if they do not have one. Fill in scope, deliverables and **phases with prices**,
   then set status to *Sent* (or use the *Send to client* action). The client is notified, can read it online,
   **accept, request changes or decline**. You are told when they open it and when they answer.
3. **Contract** – when the client accepts, a draft contract is generated from the proposal. Review/edit the text,
   then *Send to client*. The client signs with their name (date, time and IP are recorded together with a SHA-256
   fingerprint, so any later change to the text is detected). Signed contracts are locked and cannot be deleted.
4. **Project** – signing automatically creates the project, one milestone per proposal phase (with due dates and
   prices) and the **deposit invoice**.
5. **Progress** – in Admin > Projects: change a milestone to *In progress* / *Ready for approval*, post **updates**
   (with optional file attachments), upload **deliverables**. Every change is written to the client's timeline and
   triggers an in-app alert + email. The client approves a phase or **requests changes** with a comment.
6. **Invoices** – approving a phase creates its invoice (phase price minus its share of the deposit; the last invoice
   always makes the total match the contract). The client reports payment (MoMo/Airtel/bank reference); you confirm in
   Admin > Invoices (*Confirm payment received*) and they get a receipt. Invoices, proposals and contracts have
   *Print / save as PDF* buttons.

Staff dashboard: `/staff/` (pipeline, proposals waiting, contracts to sign, payments to confirm, late projects, money).

## Daily reminders (optional but recommended)
Schedule `python manage.py send_reminders` once a day (Railway cron / crontab). It nudges clients about unsigned
contracts, expiring proposals, phases waiting for approval and overdue invoices (never repeats the same reminder
within a few days).

## Environment variables
| Variable | Purpose |
|---|---|
| `SECRET_KEY` | **required** in production (the site refuses to start without it) |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | your domains, e.g. `universetech.rw,www.universetech.rw` / `https://universetech.rw,...` (Railway's own domain is added automatically) |
| `DEBUG` | leave unset in production (off). `DEBUG=1` only on your own computer |
| `SITE_URL` | public URL used in emails, e.g. `https://universetech.rw` |
| `EMAIL_BACKEND`, `EMAIL_HOST`... , `DEFAULT_FROM_EMAIL`, `NOTIFY_EMAIL` | real email (default prints emails to the console) |
| `CONTACT_EMAIL` | shown on the website once your professional email exists |
| `MOMO_DETAILS`, `AIRTEL_DETAILS`, `BANK_DETAILS` | payment instructions shown on invoices |
| `COMPANY_LEGAL_NAME`, `COMPANY_REPRESENTATIVE`, `COMPANY_TIN` | used in contracts and invoices |
| `DEFAULT_DEPOSIT_PERCENT`, `INVOICE_DUE_DAYS`, `PROPOSAL_VALID_DAYS` | business defaults |
| `SSL_REDIRECT=1`, `HSTS_SECONDS=31536000` | turn on once HTTPS works |

## Production notes
* Client files (deliverables/attachments) are stored under `media/private/` and are only downloadable through
  permission-checked links. Only `media/portfolio/` is public. On Railway attach a **volume** to `media/`,
  otherwise uploaded files disappear on every deploy.
* The contract text in `contracts/text.py` is a sensible template, **not legal advice** – have a lawyer review it once.


## Security (what protects the site)
**Least privilege**
* Staff get *only* the permissions of the group(s) you give them in Admin > Users > Groups:
  **Sales** (leads, quotations, proposals), **Project Manager** (projects, milestones, files, updates, contracts, tickets),
  **Finance** (invoices), **Support** (tickets), **Content Editor** (services, portfolio). Groups are created/refreshed
  automatically on `migrate` (or `python manage.py setup_roles`). Nobody except superusers can delete contracts,
  proposals or invoices, and paid/sent/signed records are locked.
* Keep **superusers to one or two owners**. Only superusers can create staff, assign groups or edit superusers
  (the user admin hides superusers and makes `is_staff`/`is_superuser`/groups read-only for everybody else).
* Staff can see another client's proposal/contract/invoice/project only with the matching *view* permission.
* Clients can only ever open their own records (every query is filtered by owner). Client files are only
  downloadable through permission-checked links, never from `/media/`.

**Sign-in protection**
* Staff must pass **two-factor sign-in** (authenticator app) before the admin, `/staff/` or any client-data page.
  First time: log in, you are sent to `/accounts/2fa/`, scan the QR, confirm a code, and **save the 8 recovery codes**.
  Lost phone and codes? On the server run `python manage.py reset_2fa <username>`.
* 5 wrong passwords for a username+IP lock it for 15 minutes (also on the admin login); one IP is capped overall.
  Registration, password reset, support tickets, signing, payments and proposal replies are rate-limited.
* Staff are logged out after 60 minutes idle (`STAFF_IDLE_MINUTES`). Passwords: Argon2 hashing, minimum 10 characters,
  common/numeric/similar passwords rejected.
* Set `ADMIN_URL=some-secret-path/` to move the admin away from `/admin/`.

**Browser and server hardening**
* Content-Security-Policy (no inline scripts), clickjacking protection, `nosniff`, referrer and permissions policies,
  `no-store` caching on private pages, secure + HttpOnly + SameSite cookies, HSTS and HTTPS redirect (turn on with
  `SSL_REDIRECT=1` and `HSTS_SECONDS=31536000` after confirming HTTPS works).
* `ALLOWED_HOSTS` is never `*`; the site refuses to start in production without `SECRET_KEY`.
* Uploads are limited to an allow-list of file types, checked against their real content, max 25 MB.
* Real client IP is read safely behind Railway (`TRUSTED_PROXY_COUNT=1`) so forged `X-Forwarded-For` values are ignored.
* Email subjects are sanitised against header injection; redirects are validated.

**Audit trail**: Admin > Audit events (read-only) records logins, failures, lock-outs, 2FA events, contract sent/signed,
invoices paid, proposals accepted and changes to user roles, each with time and IP.

**Your checklist after deploying**
1. Set `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL`; leave `DEBUG` unset.
2. Log in as owner, complete 2FA setup, store recovery codes safely.
3. Create staff accounts and give each only the group they need.
4. Turn on `SSL_REDIRECT=1`, then `HSTS_SECONDS`. Optionally change `ADMIN_URL`.
5. Back up the database regularly and keep dependencies updated (`pip-audit -r requirements.txt`).
#   u n i v e r s e t e c k  
 