import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_invoice_pdf(invoice, user, customer):
    """Builds a PDF for the given Invoice and returns raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InvoiceTitle", parent=styles["Title"], alignment=0, fontSize=22
    )
    small = styles["Normal"]

    elements = []

    business_name = user.business_name or user.name
    elements.append(Paragraph(business_name, title_style))
    elements.append(Paragraph(f"Invoice #{invoice.invoice_number}", small))
    elements.append(Spacer(1, 10 * mm))

    meta_data = [
        ["Bill To:", "Invoice Date:", "Due Date:"],
        [
            customer.name,
            invoice.issue_date.strftime("%Y-%m-%d") if invoice.issue_date else "-",
            invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "-",
        ],
    ]
    if customer.email:
        meta_data.append([customer.email, "", ""])
    meta_table = Table(meta_data, colWidths=[80 * mm, 50 * mm, 50 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#555555")),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 10 * mm))

    table_data = [["Description", "Qty", "Unit Price", "Tax %", "Line Total"]]
    for item in invoice.items:
        table_data.append(
            [
                item.description,
                f"{item.quantity:g}",
                f"{item.unit_price:,.2f}",
                f"{item.tax_rate:g}%",
                f"{item.line_total:,.2f}",
            ]
        )

    items_table = Table(
        table_data, colWidths=[70 * mm, 20 * mm, 30 * mm, 20 * mm, 30 * mm]
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(items_table)
    elements.append(Spacer(1, 8 * mm))

    totals_data = [
        ["Subtotal", f"{invoice.subtotal:,.2f}"],
        ["Tax", f"{invoice.tax_total:,.2f}"],
        [f"Discount ({invoice.discount_percent:g}%)", f"-{invoice.discount_amount:,.2f}"],
        ["Total", f"{invoice.total:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[140 * mm, 30 * mm])
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 12),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                ("TOPPADDING", (0, -1), (-1, -1), 6),
            ]
        )
    )
    elements.append(totals_table)

    if invoice.notes:
        elements.append(Spacer(1, 10 * mm))
        elements.append(Paragraph(f"<b>Notes:</b> {invoice.notes}", small))

    elements.append(Spacer(1, 10 * mm))
    status_label = invoice.status.upper()
    elements.append(Paragraph(f"<b>Status:</b> {status_label}", small))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
