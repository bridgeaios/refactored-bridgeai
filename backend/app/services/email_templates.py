"""Outreach email templates — industry-specific HTML emails.

Templates are keyed by template_type (set by OSINT analysis):
  tech, marketing, finance, consulting, ecommerce, real_estate, legal, general
"""
from __future__ import annotations

import html as _html

FROM_NAME = "BridgeAI"
BRAND_URL = "https://go.ai-os.co.za"
UNSUBSCRIBE_URL = "https://go.ai-os.co.za/unsubscribe"

_BASE_STYLE = """
body{margin:0;padding:0;background:#f1f5f9;font-family:Inter,system-ui,Arial,sans-serif}
.wrap{max-width:580px;margin:32px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}
.header{background:#0f172a;padding:28px 32px;text-align:center}
.header-brand{color:#63ffda;font-size:22px;font-weight:700;letter-spacing:2px}
.body{padding:32px}
.greeting{font-size:17px;font-weight:600;color:#0f172a;margin-bottom:12px}
p{font-size:14px;color:#475569;line-height:1.7;margin:0 0 14px}
.highlight{background:#f0fdf4;border-left:3px solid #22c55e;padding:12px 16px;border-radius:4px;margin:18px 0}
.highlight p{color:#166534;margin:0}
.cta-wrap{text-align:center;margin:24px 0}
.cta{display:inline-block;background:#0f172a;color:#63ffda!important;text-decoration:none;padding:13px 32px;border-radius:7px;font-weight:600;font-size:14px;letter-spacing:.5px}
.features{margin:18px 0;padding:0;list-style:none}
.features li{font-size:13px;color:#475569;padding:5px 0;padding-left:20px;position:relative}
.features li::before{content:"✓";position:absolute;left:0;color:#22c55e;font-weight:700}
.footer{background:#f8fafc;padding:18px 32px;text-align:center;border-top:1px solid #e2e8f0}
.footer p{font-size:11px;color:#94a3b8;margin:0}
.footer a{color:#64748b}
""".strip()


def _wrap(header_accent: str, body_html: str, company: str) -> str:
    safe_company = _html.escape(company or "there")
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>{_BASE_STYLE}</style></head>
<body>
<div class="wrap">
  <div class="header" style="border-bottom:3px solid {header_accent}">
    <div class="header-brand">BRIDGE AI</div>
  </div>
  <div class="body">
    {body_html}
  </div>
  <div class="footer">
    <p>© 2026 BridgeAI · <a href="{BRAND_URL}">{BRAND_URL}</a> · <a href="{UNSUBSCRIBE_URL}">Unsubscribe</a></p>
  </div>
</div>
</body></html>"""


def _plain(body: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Industry templates
# ---------------------------------------------------------------------------

def _template_tech(company: str, email: str) -> tuple[str, str, str]:
    subject = f"AI automation for {company or 'your dev team'}"
    body = f"""
<p class="greeting">Hi {_html.escape(company or 'there')},</p>
<p>We noticed your team is building something interesting. BridgeAI helps tech companies automate the business side — invoicing, CRM, and outreach — so engineers can focus on the product.</p>
<div class="highlight"><p><strong>What we automate for tech companies:</strong></p></div>
<ul class="features">
  <li>Automated client invoicing with Paystack / Stripe</li>
  <li>Lead generation &amp; outreach campaigns</li>
  <li>AI-powered CRM pipeline management</li>
  <li>MRR / ARR reporting dashboards</li>
</ul>
<p>Most clients cut admin time by 70%+ in the first month. Want a 15-minute walkthrough?</p>
<div class="cta-wrap"><a class="cta" href="{BRAND_URL}/login.html">See it live →</a></div>
"""
    return subject, _wrap("#3b82f6", body, company), _plain(body)


def _template_marketing(company: str, email: str) -> tuple[str, str, str]:
    subject = f"More leads, less manual work — {company or 'your agency'}"
    body = f"""
<p class="greeting">Hey {_html.escape(company or 'team')},</p>
<p>Running a marketing agency means juggling dozens of client accounts, proposals, and invoices. BridgeAI handles the repetitive parts so you close more, bill faster, and keep clients happier.</p>
<div class="highlight"><p>Our AI agents run 24/7 lead generation campaigns while your team sleeps.</p></div>
<ul class="features">
  <li>Automated lead scraping &amp; email outreach</li>
  <li>Smart proposal-to-invoice pipeline</li>
  <li>Client CRM with deal tracking</li>
  <li>Campaign ROI reporting</li>
</ul>
<div class="cta-wrap"><a class="cta" href="{BRAND_URL}/login.html">Try it free →</a></div>
"""
    return subject, _wrap("#8b5cf6", body, company), _plain(body)


def _template_finance(company: str, email: str) -> tuple[str, str, str]:
    subject = f"Streamline billing &amp; client ops — {company or 'your firm'}"
    body = f"""
<p class="greeting">Dear {_html.escape(company or 'team')},</p>
<p>Financial services firms trust BridgeAI to handle compliance-friendly invoicing, automated client follow-ups, and pipeline management — without the overhead of a full ops team.</p>
<div class="highlight"><p>SOC-2 aligned. All data processed in-region. No third-party data sharing.</p></div>
<ul class="features">
  <li>Tax-compliant invoice generation (VAT, GST)</li>
  <li>Automated payment reconciliation</li>
  <li>Client lifecycle CRM</li>
  <li>Treasury reporting &amp; cash-flow dashboards</li>
</ul>
<div class="cta-wrap"><a class="cta" href="{BRAND_URL}/login.html">Schedule a demo →</a></div>
"""
    return subject, _wrap("#f59e0b", body, company), _plain(body)


def _template_consulting(company: str, email: str) -> tuple[str, str, str]:
    subject = f"Bill more hours, less admin — {company or 'your practice'}"
    body = f"""
<p class="greeting">Hi {_html.escape(company or 'there')},</p>
<p>Consultants spend an average of 12 hours per week on admin — proposals, invoicing, follow-ups. BridgeAI cuts that to under 2 hours with AI agents that handle the busywork.</p>
<div class="highlight"><p>Clients report recovering 10+ billable hours per week after onboarding.</p></div>
<ul class="features">
  <li>One-click invoice generation from project scope</li>
  <li>Automated payment reminders</li>
  <li>Proposal pipeline tracking</li>
  <li>Referral &amp; lead capture automation</li>
</ul>
<div class="cta-wrap"><a class="cta" href="{BRAND_URL}/login.html">Get started free →</a></div>
"""
    return subject, _wrap("#10b981", body, company), _plain(body)


def _template_ecommerce(company: str, email: str) -> tuple[str, str, str]:
    subject = f"Automate your B2B ops — {company or 'your store'}"
    body = f"""
<p class="greeting">Hi {_html.escape(company or 'there')},</p>
<p>E-commerce brands using BridgeAI automate wholesale invoicing, B2B outreach to retail buyers, and supplier payment reconciliation — all from one dashboard.</p>
<div class="highlight"><p>Average time to first B2B invoice: under 5 minutes.</p></div>
<ul class="features">
  <li>Bulk B2B invoice generation</li>
  <li>Automated wholesale buyer outreach</li>
  <li>Payment reconciliation with Paystack/Stripe</li>
  <li>Inventory-aware CRM</li>
</ul>
<div class="cta-wrap"><a class="cta" href="{BRAND_URL}/login.html">Try it free →</a></div>
"""
    return subject, _wrap("#f97316", body, company), _plain(body)


def _template_general(company: str, email: str) -> tuple[str, str, str]:
    subject = f"AI agents that run your business ops — {company or 'see how'}"
    body = f"""
<p class="greeting">Hi {_html.escape(company or 'there')},</p>
<p>BridgeAI deploys AI agents that handle lead generation, invoicing, outreach, and CRM — automatically. No coding required, no ops team needed.</p>
<div class="highlight"><p>One platform. Invoicing → CRM → Outreach → Treasury. Fully autonomous.</p></div>
<ul class="features">
  <li>AI-powered lead generation campaigns</li>
  <li>Automated invoicing &amp; payment reconciliation</li>
  <li>Smart CRM pipeline management</li>
  <li>Outreach email sequences</li>
</ul>
<div class="cta-wrap"><a class="cta" href="{BRAND_URL}/login.html">See a live demo →</a></div>
"""
    return subject, _wrap("#0ea5e9", body, company), _plain(body)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_TEMPLATES = {
    "tech": _template_tech,
    "marketing": _template_marketing,
    "finance": _template_finance,
    "consulting": _template_consulting,
    "ecommerce": _template_ecommerce,
    "real_estate": _template_consulting,   # reuse consulting variant
    "legal": _template_consulting,
}


def render_template(
    template_type: str,
    company: str,
    email: str,
) -> tuple[str, str, str]:
    """Return (subject, html, text) for the given template type."""
    fn = _TEMPLATES.get(template_type, _template_general)
    return fn(company, email)
