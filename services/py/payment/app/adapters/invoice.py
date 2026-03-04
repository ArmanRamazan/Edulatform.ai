from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

from app.domain.invoice import InvoiceData


class InvoicePDFGenerator:
    def generate_invoice(self, data: InvoiceData) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        style_right = ParagraphStyle(
            "right", parent=styles["Normal"], alignment=TA_RIGHT,
        )
        style_center = ParagraphStyle(
            "center", parent=styles["Normal"], alignment=TA_CENTER,
        )
        title_style = ParagraphStyle(
            "InvoiceTitle",
            parent=styles["Heading1"],
            fontSize=22,
            spaceAfter=4 * mm,
        )

        elements: list = []

        # Header
        elements.append(Paragraph("EduPlatform", title_style))
        elements.append(
            Paragraph("Invoice", styles["Heading2"])
        )
        elements.append(Spacer(1, 6 * mm))

        # Company info
        company_info = (
            "EduPlatform Inc.<br/>"
            "123 Learning Street, Suite 100<br/>"
            "San Francisco, CA 94105, USA<br/>"
            "support@eduplatform.com"
        )
        elements.append(Paragraph(company_info, styles["Normal"]))
        elements.append(Spacer(1, 6 * mm))

        # Invoice details
        details_data = [
            ["Invoice #:", data.invoice_number],
            ["Date:", data.payment_date.strftime("%Y-%m-%d")],
        ]
        details_table = Table(details_data, colWidths=[30 * mm, 60 * mm])
        details_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 6 * mm))

        # Buyer info
        elements.append(Paragraph("Bill To:", styles["Heading3"]))
        buyer_info = f"{data.buyer_name}<br/>{data.buyer_email}"
        elements.append(Paragraph(buyer_info, styles["Normal"]))
        elements.append(Spacer(1, 8 * mm))

        # Line items table
        line_items = [
            ["Description", "Qty", "Unit Price", "Total"],
            [data.course_title, "1", f"${data.original_price}", f"${data.original_price}"],
        ]
        col_widths = [90 * mm, 20 * mm, 30 * mm, 30 * mm]
        items_table = Table(line_items, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A90D9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 4 * mm))

        # Totals
        totals_data = [
            ["Subtotal:", f"${data.original_price}"],
        ]
        if data.discount_amount > 0:
            discount_label = "Discount"
            if data.coupon_code:
                discount_label += f" ({data.coupon_code})"
            discount_label += ":"
            totals_data.append([discount_label, f"-${data.discount_amount}"])
        totals_data.append(["Total:", f"${data.final_price}"])

        totals_table = Table(totals_data, colWidths=[130 * mm, 40 * mm])
        totals_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 12 * mm))

        # Footer
        elements.append(Paragraph(
            "Thank you for learning with EduPlatform!",
            style_center,
        ))

        doc.build(elements)
        return buf.getvalue()
