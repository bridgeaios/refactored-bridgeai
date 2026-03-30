"""
OSINT Profile Engine - Analyze company data and create intelligence profiles
"""
import re
from typing import Dict, Any

def analyze_company(url: str, title: str, emails: list) -> Dict[str, Any]:
    """
    Analyze company data and extract intelligence profile
    Returns: {
        "company_name": str,
        "industry": str,
        "size_estimate": "startup|small|medium|large|enterprise",
        "email_domain": str,
        "decision_makers": list,
        "pain_points": list,
        "template_type": str
    }
    """

    # Extract company name
    company_name = extract_company_name(title, url)

    # Detect industry
    industry = detect_industry(title, url, emails)

    # Estimate company size
    size = estimate_company_size(url, emails, industry)

    # Extract email domain
    email_domain = extract_email_domain(emails[0] if emails else "")

    # Identify decision makers
    decision_makers = identify_decision_makers(emails)

    # Extract pain points based on industry
    pain_points = extract_pain_points(industry, size)

    # Select template type based on profile
    template_type = select_template(industry, size, decision_makers)

    return {
        "company_name": company_name,
        "industry": industry,
        "size_estimate": size,
        "email_domain": email_domain,
        "decision_makers": decision_makers,
        "pain_points": pain_points,
        "template_type": template_type,
        "profile_confidence": calculate_confidence(title, emails, industry)
    }


def extract_company_name(title: str, url: str) -> str:
    """Extract company name from title or URL"""
    # Clean title first
    name = title.split("|")[0].strip() if "|" in title else title
    name = name.split("-")[0].strip() if "-" in name else name

    # Remove common suffixes
    suffixes = [" Inc", " LLC", " Ltd", " Corp", " Group", " Agency", " Co", " Agency"]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    return name.strip()


def detect_industry(title: str, url: str, emails: list) -> str:
    """Detect industry from available signals"""

    combined_text = f"{title} {url} {' '.join(emails)}".lower()

    industries = {
        "technology": ["software", "tech", "cloud", "ai", "digital", "saas", "app", "developer"],
        "marketing": ["marketing", "advertising", "agency", "digital marketing", "seo", "social"],
        "finance": ["bank", "finance", "investment", "trading", "insurance", "crypto"],
        "real_estate": ["real estate", "property", "realtor", "realty", "developer"],
        "consulting": ["consulting", "consultant", "strategy", "management", "advisory"],
        "ecommerce": ["ecommerce", "shop", "store", "retail", "amazon", "shopify"],
        "legal": ["law", "attorney", "lawyer", "legal", "firm"],
        "healthcare": ["health", "medical", "hospital", "clinic", "dental", "pharmacy"],
        "construction": ["construction", "builder", "contractor", "engineer"],
        "manufacturing": ["manufacturing", "factory", "production", "industrial"]
    }

    for industry, keywords in industries.items():
        for keyword in keywords:
            if keyword in combined_text:
                return industry

    return "general"


def estimate_company_size(url: str, emails: list, industry: str) -> str:
    """Estimate company size based on email count and domain signals"""

    num_emails = len(set([e.split("@")[1] for e in emails]))  # Unique domains

    # More diverse emails = larger organization
    if num_emails >= 5:
        return "enterprise"
    elif num_emails >= 3:
        return "large"
    elif num_emails >= 2:
        return "medium"
    elif num_emails == 1:
        return "small"
    else:
        return "startup"


def extract_email_domain(email: str) -> str:
    """Extract domain from email"""
    if not email or "@" not in email:
        return ""
    return email.split("@")[1]


def identify_decision_makers(emails: list) -> list:
    """Identify potential decision makers from email patterns"""

    decision_indicators = ["ceo", "founder", "director", "manager", "head", "chief", "executive", "owner"]

    makers = []
    for email in emails:
        email_lower = email.lower()
        for indicator in decision_indicators:
            if indicator in email_lower or indicator in email.split("@")[0]:
                makers.append(email)
                break

    return makers[:3]  # Top 3


def extract_pain_points(industry: str, size: str) -> list:
    """Extract industry-specific pain points"""

    pain_map = {
        "technology": [
            "Scaling infrastructure",
            "Managing technical debt",
            "Recruiting engineering talent",
            "Cloud cost optimization"
        ],
        "marketing": [
            "Lead generation at scale",
            "Attribution & ROI tracking",
            "Content production efficiency",
            "Team collaboration"
        ],
        "finance": [
            "Regulatory compliance",
            "Risk management",
            "Data security",
            "Transaction processing speed"
        ],
        "consulting": [
            "Resource allocation",
            "Project delivery efficiency",
            "Knowledge management",
            "Client billing accuracy"
        ],
        "real_estate": [
            "Lead qualification",
            "Property management",
            "Market analysis",
            "Transaction velocity"
        ]
    }

    return pain_map.get(industry, [
        "Operational efficiency",
        "Customer acquisition",
        "Data management",
        "Team coordination"
    ])


def select_template(industry: str, size: str, decision_makers: list) -> str:
    """Select email template type based on profile"""

    # Premium templates for large companies with decision makers
    if size in ["enterprise", "large"] and decision_makers:
        return "executive"

    # Industry-specific templates
    if industry == "technology":
        return "tech_founder"
    elif industry == "marketing":
        return "marketing_pro"
    elif industry == "finance":
        return "finance"
    elif industry == "consulting":
        return "consultant"

    # Default based on size
    if size == "startup":
        return "founder"
    elif size in ["small", "medium"]:
        return "standard"
    else:
        return "general"


def calculate_confidence(title: str, emails: list, industry: str) -> float:
    """Calculate confidence score of profile (0-1)"""

    score = 0.5  # Base score

    if title and len(title) > 20:
        score += 0.2

    if emails and len(emails) >= 2:
        score += 0.2

    if industry != "general":
        score += 0.1

    return min(score, 1.0)
