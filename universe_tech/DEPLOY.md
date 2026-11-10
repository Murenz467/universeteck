# Putting Universe Tech online (Railway) — step by step

You do this once. After that, every time you push a change to GitHub, the site updates by itself.

**What you need:** a GitHub account, a Railway account, a card for Railway (the Hobby plan costs about $5/month, check railway.com/pricing), and later your domain `universetech.rw`.

---

## Step 1. Put the code on GitHub
1. On github.com create a **private** repository called `universe-tech` (empty, no README).
2. In PowerShell, inside the project folder:
```powershell
git init
git add .
git commit -m "Universe Tech website"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/universe-tech.git
git push -u origin main
```
Your `.env` file, database and private files are already excluded by `.gitignore`. Check on GitHub that there is **no `.env` file** in the repository.

## Step 2. Create the project on Railway
1. railway.com → **New Project** → **Deploy from GitHub repo** → choose `universe-tech`.
2. In the same project click **+ New** → **Database** → **Add PostgreSQL**.
3. Open your website service → **Variables** → **New Variable**:
   `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (use the exact name of your Postgres service if it is different).

## Step 3. Add a Volume (so uploaded files are never lost)
Website service → **Volumes** (or right-click the service canvas → **Add Volume**) → mount path `/data`.
Then add the variable `MEDIA_ROOT` = `/data/media`.

## Step 4. Add your settings
Website service → **Variables** → **Raw Editor**. Copy the lines from **`.env.production.example`** and fill them in:

| Variable | What to put |
|---|---|
| `SECRET_KEY` | Run `python -c "import secrets; print(secrets.token_urlsafe(64))"` and paste the result. Never share it. |
| `SITE_URL` | For the first test, the address Railway gives you (Step 5). Later `https://universetech.rw`. |
| `ADMIN_URL` | A secret admin address of your choice, e.g. `ut-control-k8m2q/` (keep the `/` at the end). |
| `DJANGO_SUPERUSER_USERNAME`, `_EMAIL`, `_PASSWORD` | Your first admin login. **Delete these three variables after the first successful deploy.** Use a long password. |
| `MOMO_DETAILS`, `AIRTEL_DETAILS`, `BANK_DETAILS` | How clients pay, as they should appear on invoices. |
| `COMPANY_TIN` | Your tax number, if you have one. |

Do **not** add `DEBUG`.

## Step 5. First launch
1. Website service → **Settings** → **Networking** → **Generate Domain**. Copy the address (`something.up.railway.app`).
2. Set `SITE_URL=https://something.up.railway.app` (your real generated address) and let it redeploy.
3. Wait until the deployment turns green. Open the address: you should see the website.
4. Go to `https://YOUR-ADDRESS/YOUR_ADMIN_URL`, sign in, and **set up two-factor** with an authenticator app. Save the 8 recovery codes somewhere safe.
5. Now **delete the three `DJANGO_SUPERUSER_*` variables**.

On the very first start the site adds the services, your real portfolio projects (Lamar, JobLink, ISHARE, SmartJob, AutoRent), pricing packages and FAQ. It does **not** add fake testimonials or fake client names.

## Step 6. Make the content real (in the admin)
- **Portfolio → Case studies:** replace each project's simple cover image with a real screenshot, and add the live website address for Lamar. Add more projects as you finish them.
- **Trust & pricing:** check every price, timeline and FAQ answer. Add real testimonials and client logos.
- Check **Terms** and **Privacy** with someone who knows Rwandan law.

## Step 7. Email that really arrives
Railway's cheaper plans **block normal email sending (SMTP)**, so the site sends through an email service over the web. We use **Resend** (Brevo also works).

1. Create an account at resend.com → **Domains** → **Add Domain** → `universetech.rw`.
2. Resend shows some DNS records (SPF, DKIM). Add them where your domain's DNS is managed. Wait until the domain shows **Verified**.
3. **API Keys** → create a key with "Sending access".
4. In Railway Variables set: `EMAIL_PROVIDER=resend`, `RESEND_API_KEY=...`, `DEFAULT_FROM_EMAIL=Universe Tech <info@universetech.rw>`, `NOTIFY_EMAIL=info@universetech.rw`.
5. **Test:** open your site and send a quote request. A notification should arrive at `NOTIFY_EMAIL`. (Also check Spam the first time.)

**Receiving mail at info@universetech.rw:** Resend only *sends*. You also need a mailbox for that address (for example Zoho Mail, Google Workspace, or free forwarding to your Gmail through Cloudflare Email Routing; check each one's current free plan). Add the MX records they give you. When the mailbox works, set `CONTACT_EMAIL=info@universetech.rw` so it shows in the footer.

## Step 8. Your domain `universetech.rw`
1. Buy it from a registrar accredited for `.rw` (the registry is RICTA, see ricta.org.rw).
2. Railway → website service → **Settings** → **Networking** → **Custom Domain** → add `universetech.rw` and `www.universetech.rw`. Railway shows a CNAME record for each.
3. Add those records in your DNS. If your registrar does not allow a CNAME on the bare domain (`universetech.rw`), put the domain's DNS on **Cloudflare** (free) which does.
4. When it works, set `SITE_URL=https://universetech.rw`. HTTPS redirection is automatic.
5. After a few days of everything working, add `HSTS_SECONDS=31536000`.

## Step 9. Daily reminders
Overdue invoices and expiring proposals are reminded by a daily job.
Railway project → **+ New** → **GitHub Repo** (the same repo) → in this new service: **Settings → Cron Schedule** = `0 6 * * *` (08:00 Kigali time) and **Start Command** = `python manage.py send_reminders`. Give it the same variables as the website (use Railway's shared variables or copy them).

## Step 10. Backups
- Railway Postgres: open the database → **Backups** and turn on scheduled backups (check what your plan includes).
- Once a month, also download a copy yourself (needs PostgreSQL tools installed): `pg_dump "PUBLIC_DATABASE_URL" > backup.sql`. Keep it somewhere safe.
- Uploaded files live on the Volume. Back it up from the Volume's **Backups** tab if your plan offers it.

---

## Updating the site later
Change the code, then:
```powershell
git add .
git commit -m "What I changed"
git push
```
Railway rebuilds and restarts automatically, and updates the database structure by itself.

## If something goes wrong
| What you see | Likely cause and fix |
|---|---|
| Deployment fails, logs say `SECRET_KEY is not set` | Add `SECRET_KEY` in Variables. |
| `DisallowedHost` / Bad Request (400) | `SITE_URL` does not match the address you are visiting. |
| Forms say "CSRF verification failed" | Same: `SITE_URL` must start with `https://` and match your address. |
| Uploaded images disappear after a redeploy | The Volume is missing or `MEDIA_ROOT` is not `/data/media`. |
| Emails do not arrive | Domain not **Verified** in Resend, wrong `RESEND_API_KEY`, or check Spam. Logs show the reason. |
| Locked out of the admin (lost phone) | Use one of your recovery codes. |
| Logs say emails "are only printed" | `EMAIL_PROVIDER` is not set. |
