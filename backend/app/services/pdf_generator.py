"""PDF invoice generator using reportlab.

Generates branded A4 invoices with:
- BridgeAI header branding
- Client / billing-from details
- Line items table
- Subtotal / tax / total breakdown
- QR code linking to a Paystack payment URL (if configured)
- Invoice status watermark for paid/overdue invoices
"""
from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Any

# reportlab imports — package is installed in requirements.txt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------
BRAND_DARK = colors.HexColor("#0f172a")   # slate-900
BRAND_MID = colors.HexColor("#1e3a5f")    # bridge-blue
BRAND_ACCENT = colors.HexColor("#3b82f6")  # blue-500
BRAND_LIGHT = colors.HexColor("#e2e8f0")  # slate-200
BRAND_TEXT = colors.HexColor("#334155")   # slate-700
WHITE = colors.white

# Company billing details (override via env)
COMPANY_NAME = os.environ.get("INVOICE_COMPANY_NAME", "BridgeAI (Pty) Ltd")
COMPANY_ADDRESS = os.environ.get("INVOICE_COMPANY_ADDRESS", "South Africa")
COMPANY_EMAIL = os.environ.get("INVOICE_COMPANY_EMAIL", "billing@ai-os.co.za")
COMPANY_VAT = os.environ.get("INVOICE_COMPANY_VAT", "")
PAYSTACK_BASE = os.environ.get("PAYSTACK_PAYMENT_BASE", "https://paystack.com/pay/bridgeai")


def _qr_image(data: str, size: float = 2.5 * cm) -> Image | None:
    """Return a reportlab Image containing a QR code, or None if qrcode not available."""
    try:
        import qrcode
        from PIL import Image as PILImage  # type: ignore

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)
        return Image(buf, width=size, height=size)
    except ImportError:
        return None


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "company_name": ParagraphStyle(
            "company_name",
            fontSize=20,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            spaceAfter=2,
        ),
        "company_sub": ParagraphStyle(
            "company_sub",
            fontSize=8,
            textColor=colors.HexColor("#94a3b8"),
            fontName="Helvetica",
        ),
        "invoice_title": ParagraphStyle(
            "invoice_title",
            fontSize=28,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            alignment=TA_RIGHT,
        ),
        "invoice_meta_label": ParagraphStyle(
            "invoice_meta_label",
            fontSize=8,
            textColor=colors.HexColor("#94a3b8"),
            fontName="Helvetica",
            alignment=TA_RIGHT,
        ),
        "invoice_meta_value": ParagraphStyle(
            "invoice_meta_value",
            fontSize=9,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            alignment=TA_RIGHT,
        ),
        "section_label": ParagraphStyle(
            "section_label",
            fontSize=7,
            textColor=colors.HexColor("#64748b"),
            fontName="Helvetica-Bold",
            spaceAfter=2,
            spaceBefore=8,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=9,
            textColor=BRAND_TEXT,
            fontName="Helvetica",
            leading=13,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            fontSize=9,
            textColor=BRAND_DARK,
            fontName="Helvetica-Bold",
        ),
        "total_label": ParagraphStyle(
            "total_label",
            fontSize=10,
            textColor=BRAND_TEXT,
            fontName="Helvetica",
            alignment=TA_RIGHT,
        ),
        "total_value": ParagraphStyle(
            "total_value",
            fontSize=10,
            textColor=BRAND_DARK,
            fontName="Helvetica-Bold",
            alignment=TA_RIGHT,
        ),
        "grand_total_label": ParagraphStyle(
            "grand_total_label",
            fontSize=14,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            alignment=TA_RIGHT,
        ),
        "grand_total_value": ParagraphStyle(
            "grand_total_value",
            fontSize=14,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            alignment=TA_RIGHT,
        ),
        "note": ParagraphStyle(
            "note",
            fontSize=8,
            textColor=colors.HexColor("#64748b"),
            fontName="Helvetica",
            leading=12,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontSize=7,
            textColor=colors.HexColor("#94a3b8"),
            fontName="Helvetica",
            alignment=TA_CENTER,
        ),
        "watermark": ParagraphStyle(
            "watermark",
            fontSize=60,
            textColor=colors.Color(0, 0.6, 0, alpha=0.12),
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
    }


def _currency_symbol(currency: str) -> str:
    return {"ZAR": "R", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency.upper(), currency + " ")


def generate_invoice_pdf(invoice: dict[str, Any]) -> bytes:
    """Generate a PDF invoice and return raw bytes.

    Args:
        invoice: Invoice dict as stored in MemoryStore / returned by BillingService.

    Returns:
        PDF bytes suitable for streaming as application/pdf response.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=0,        # header drawn manually
        bottomMargin=1.5 * cm,
        title=f"Invoice {invoice.get('invoice_number', '')}",
        author=COMPANY_NAME,
    )

    st = _styles()
    currency = invoice.get("currency", "ZAR")
    sym = _currency_symbol(currency)
    invoice_number = invoice.get("invoice_number", "—")
    status = invoice.get("status", "draft").upper()
    story: list[Any] = []

    # ------------------------------------------------------------------
    # Header banner (dark background)
    # ------------------------------------------------------------------
    page_width = A4[0] - 3 * cm   # usable width

    header_data = [
        [
            Paragraph(COMPANY_NAME, st["company_name"]),
            Paragraph("INVOICE", st["invoice_title"]),
        ],
        [
            Paragraph(f"{COMPANY_ADDRESS}<br/>{COMPANY_EMAIL}", st["company_sub"]),
            Table(
                [
                    [Paragraph("Invoice No.", st["invoice_meta_label"]), Paragraph(invoice_number, st["invoice_meta_value"])],
                    [Paragraph("Issued", st["invoice_meta_label"]), Paragraph(invoice.get("issued_at", "")[:10], st["invoice_meta_value"])],
                    [Paragraph("Due", st["invoice_meta_label"]), Paragraph(invoice.get("due_date", "—"), st["invoice_meta_value"])],
                ],
                colWidths=[2.5 * cm, 4 * cm],
                style=TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]),
            ),
        ],
    ]

    header_table = Table(
        header_data,
        colWidths=[page_width * 0.55, page_width * 0.45],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_MID),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ("LEFTPADDING", (0, 0), (0, -1), 14),
            ("RIGHTPADDING", (-1, 0), (-1, -1), 14),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]),
    )
    story.append(header_table)
    story.append(Spacer(1, 0.5 * cm))

    # ------------------------------------------------------------------
    # Status watermark for PAID / OVERDUE
    # ------------------------------------------------------------------
    if status in ("PAID", "OVERDUE"):
        wm_color = colors.Color(0, 0.55, 0, alpha=0.10) if status == "PAID" else colors.Color(0.8, 0, 0, alpha=0.10)
        wm_style = ParagraphStyle(
            "wm",
            fontSize=72,
            textColor=wm_color,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
        story.append(Paragraph(status, wm_style))
        story.append(Spacer(1, -1 * cm))

    # ------------------------------------------------------------------
    # Bill To / From columns
    # ------------------------------------------------------------------
    from_lines = f"<b>{COMPANY_NAME}</b><br/>{COMPANY_ADDRESS}<br/>{COMPANY_EMAIL}"
    if COMPANY_VAT:
        from_lines += f"<br/>VAT: {COMPANY_VAT}"

    client_name = invoice.get("client_name") or invoice.get("client_company") or invoice.get("client_email", "—")
    to_lines = f"<b>{client_name}</b>"
    if invoice.get("client_company") and invoice.get("client_name"):
        to_lines += f"<br/>{invoice['client_company']}"
    to_lines += f"<br/>{invoice.get('client_email', '')}"

    parties_data = [
        [
            Paragraph("FROM", st["section_label"]),
            Spacer(1, 1),
            Paragraph("BILL TO", st["section_label"]),
        ],
        [
            Paragraph(from_lines, st["body"]),
            Spacer(1, 1),
            Paragraph(to_lines, st["body"]),
        ],
    ]
    parties_table = Table(
        parties_data,
        colWidths=[page_width * 0.42, 0.5 * cm, page_width * 0.52],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]),
    )
    story.append(parties_table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_LIGHT))
    story.append(Spacer(1, 0.3 * cm))

    # ------------------------------------------------------------------
    # Line items table
    # ------------------------------------------------------------------
    col_widths = [page_width * 0.48, page_width * 0.12, page_width * 0.20, page_width * 0.20]
    items = invoice.get("items", [])

    item_rows: list[list[Any]] = [
        [
            Paragraph("<b>Description</b>", st["body_bold"]),
            Paragraph("<b>Qty</b>", st["body_bold"]),
            Paragraph("<b>Unit Price</b>", st["body_bold"]),
            Paragraph("<b>Amount</b>", st["body_bold"]),
        ]
    ]
    for item in items:
        qty = float(item.get("quantity", 1))
        price = float(item.get("unit_price", 0))
        amount = qty * price
        item_rows.append([
            Paragraph(str(item.get("description", "")), st["body"]),
            Paragraph(f"{qty:g}", st["body"]),
            Paragraph(f"{sym}{price:,.2f}", st["body"]),
            Paragraph(f"{sym}{amount:,.2f}", st["body"]),
        ])

    items_table = Table(item_rows, colWidths=col_widths)
    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        # Data rows
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#f8fafc")]),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.25, BRAND_LIGHT),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.4 * cm))

    # ------------------------------------------------------------------
    # Totals block (right-aligned)
    # ------------------------------------------------------------------
    subtotal = invoice.get("subtotal", 0.0)
    tax = invoice.get("tax", 0.0)
    tax_rate = invoice.get("tax_rate", 0.15)
    total = invoice.get("total", 0.0)

    totals_data = [
        [Paragraph("Subtotal", st["total_label"]), Paragraph(f"{sym}{subtotal:,.2f}", st["total_value"])],
        [Paragraph(f"VAT ({tax_rate * 100:.0f}%)", st["total_label"]), Paragraph(f"{sym}{tax:,.2f}", st["total_value"])],
    ]
    totals_table = Table(
        totals_data,
        colWidths=[page_width * 0.82, page_width * 0.18],
        style=TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]),
    )
    story.append(totals_table)
    story.append(Spacer(1, 0.1 * cm))

    # Grand total bar
    grand_data = [[
        Paragraph("TOTAL DUE", st["grand_total_label"]),
        Paragraph(f"{sym}{total:,.2f} {currency}", st["grand_total_value"]),
    ]]
    grand_table = Table(
        grand_data,
        colWidths=[page_width * 0.75, page_width * 0.25],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_MID),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]),
    )
    story.append(grand_table)
    story.append(Spacer(1, 0.5 * cm))

    # ------------------------------------------------------------------
    # QR code + notes row
    # ------------------------------------------------------------------
    payment_url = f"{PAYSTACK_BASE}/{invoice_number.lower().replace('/', '-')}"
    qr_img = _qr_image(payment_url)

    notes_text = invoice.get("notes", "")
    notes_para = Paragraph(
        f"<b>Payment Instructions</b><br/>Scan the QR code or visit:<br/>{payment_url}"
        + (f"<br/><br/><b>Notes:</b> {notes_text}" if notes_text else ""),
        st["note"],
    )

    if qr_img:
        qr_row = Table(
            [[qr_img, notes_para]],
            colWidths=[3 * cm, page_width - 3 * cm],
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (1, 0), (1, 0), 12),
            ]),
        )
        story.append(qr_row)
    else:
        story.append(notes_para)

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_LIGHT))
    story.append(Spacer(1, 0.2 * cm))

    # Footer
    story.append(Paragraph(
        f"{COMPANY_NAME} · {COMPANY_EMAIL} · Generated {datetime.utcnow().strftime('%Y-%m-%d')}",
        st["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
