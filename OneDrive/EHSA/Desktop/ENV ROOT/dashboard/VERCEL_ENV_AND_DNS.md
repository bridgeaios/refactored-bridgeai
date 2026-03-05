# Vercel — Environment Variables & DNS (app.supaco.ai)

Reference for the app hosted at **https://app.supaco.ai** (Vercel). Set env vars in **Vercel Dashboard → Project → Settings → Environment Variables**. Do not commit secrets to the repo.

---

## Required (blocking login + payments)

| Variable         | Value / notes |
|------------------|---------------|
| `NEXTAUTH_SECRET` | Set in Vercel. Use a long random string (e.g. `openssl rand -hex 32`). Required for NextAuth. |
| `NEXTAUTH_URL`   | `https://app.supaco.ai` |
| `NODE_ENV`       | `production` |

---

## Payment keys

Get from the dashboards and paste into Vercel (never commit).

| Variable                 | Where to get it |
|--------------------------|------------------|
| `PAYSTACK_SECRET_KEY`    | dashboard.paystack.com → Settings → API Keys |
| `PAYSTACK_PUBLIC_KEY`   | same |
| `PAYSTACK_WEBHOOK_SECRET` | dashboard.paystack.com → Settings → Webhooks |
| `PAYPAL_CLIENT_ID`      | developer.paypal.com → My Apps |
| `PAYPAL_CLIENT_SECRET`  | same |

---

## Email

| Variable        | Value / notes |
|-----------------|----------------|
| `RESEND_API_KEY` | resend.com → API Keys (set in Vercel only) |
| `EMAIL_FROM`    | `support@bridge-ai-os.com` |

---

## App URLs

| Variable                   | Value |
|----------------------------|--------|
| `DASHBOARD_URL`            | `https://app.supaco.ai` |
| `FUNDS_DASHBOARD_PUBLIC`   | `true` |

---

## DNS (Cloudflare Dashboard)

**app.supaco.ai** (zone: **supaco.ai**):

| Field  | Value |
|--------|--------|
| Type   | CNAME |
| Name   | `app` |
| Target | `cname.vercel-dns.com` (or your Vercel deployment hostname) |
| Proxy  | **DNS only (grey cloud)** — Vercel needs direct TLS |

**bridge-ai-os.tech** (zone: **bridge-ai-os.tech**):

| Field  | Value |
|--------|--------|
| Type   | CNAME |
| Name   | `@` |
| Target | `bridge-ai-os.com` |
| Proxy  | **Proxied (orange cloud)** for redirect |
