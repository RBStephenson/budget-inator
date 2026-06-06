"""Render the budget report data to PDF bytes using ReportLab."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.monthly import MonthlySummaryResponse
from app.schemas.schedule import AssignedBillOut, PayPeriodOut
from app.services.report_service import ReportData

# Canonical category display order, shared with the dashboard grouping.
_CATEGORY_ORDER = [
    "housing",
    "utilities",
    "subscriptions",
    "insurance",
    "debt",
    "savings",
    "other",
]

_CATEGORY_LABELS = {
    "housing": "Housing",
    "utilities": "Utilities",
    "subscriptions": "Subscriptions",
    "insurance": "Insurance",
    "debt": "Debt",
    "savings": "Savings",
    "other": "Other",
}

_STATUS_LABELS = {
    "on_time": "On time",
    "late_flagged": "Late",
    "paid": "Paid",
    "skipped": "Skipped",
}

# Palette
_HEADER_BG = colors.HexColor("#1f2937")
_CATEGORY_BG = colors.HexColor("#f3f4f6")
_LATE_BG = colors.HexColor("#fee2e2")
_SUBTOTAL_BG = colors.HexColor("#fafafa")
_GRID = colors.HexColor("#e5e7eb")
_MUTED = colors.HexColor("#6b7280")


def _money(value: Decimal | str | float) -> str:
    d = Decimal(str(value))
    sign = "-" if d < 0 else ""
    return f"{sign}${abs(d):,.2f}"


def _fmt_date(d) -> str:
    return f"{d:%b} {d.day}, {d.year}"


def _fmt_day(d) -> str:
    return f"{d:%b} {d.day}"


def _fmt_month(month_str: str) -> str:
    year, month = month_str.split("-")
    names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    return f"{names[int(month) - 1]} {year}"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontSize=20,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontSize=9,
            textColor=_MUTED,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "section": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontSize=14,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "period": ParagraphStyle(
            "PeriodHeading",
            parent=base["Heading3"],
            fontSize=11,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "cell": ParagraphStyle("Cell", parent=base["Normal"], fontSize=8),
        "cell_right": ParagraphStyle(
            "CellRight", parent=base["Normal"], fontSize=8, alignment=TA_RIGHT
        ),
        "empty": ParagraphStyle(
            "Empty", parent=base["Normal"], fontSize=9, textColor=_MUTED
        ),
    }


def _bills_by_category(
    bills: list[AssignedBillOut],
) -> list[tuple[str, list[AssignedBillOut]]]:
    grouped: list[tuple[str, list[AssignedBillOut]]] = []
    for cat in _CATEGORY_ORDER:
        in_cat = [b for b in bills if b.category == cat]
        if in_cat:
            grouped.append((cat, in_cat))
    return grouped


def _assigned_amount(bill: AssignedBillOut) -> Decimal:
    if bill.actual_amount is not None:
        return Decimal(str(bill.actual_amount))
    return Decimal(str(bill.amount))


def _period_flowables(period: PayPeriodOut, styles) -> list:
    """One pay-period block: heading, grouped bill table, balance summary."""
    flow: list = []
    heading = (
        f"{_fmt_date(period.period_start)} &ndash; {_fmt_date(period.period_end)}"
        f" &nbsp;·&nbsp; Pay on {_fmt_day(period.pay_date)}"
    )
    flow.append(Paragraph(heading, styles["period"]))

    header = ["Bill", "Due on", "Pay on", "Amount", "Status"]
    data: list[list] = [header]
    style_cmds: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, _GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    if not period.assigned_bills:
        data.append(
            [Paragraph("No bills this period.", styles["empty"]), "", "", "", ""]
        )
        style_cmds.append(("SPAN", (0, 1), (-1, 1)))
    else:
        for cat, bills in _bills_by_category(period.assigned_bills):
            row_idx = len(data)
            data.append([_CATEGORY_LABELS.get(cat, cat), "", "", "", ""])
            style_cmds.append(("SPAN", (0, row_idx), (-1, row_idx)))
            style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), _CATEGORY_BG))
            style_cmds.append(
                ("FONTNAME", (0, row_idx), (0, row_idx), "Helvetica-Bold")
            )

            subtotal = Decimal("0")
            for bill in bills:
                amt = _assigned_amount(bill)
                if bill.status != "skipped":
                    subtotal += amt
                amount_str = ("~" if bill.is_variable else "") + _money(amt)
                bill_row = len(data)
                data.append(
                    [
                        bill.name,
                        _fmt_day(bill.due_date),
                        _fmt_day(period.pay_date),
                        amount_str,
                        _STATUS_LABELS.get(bill.status, bill.status),
                    ]
                )
                if bill.status == "late_flagged":
                    style_cmds.append(
                        ("BACKGROUND", (0, bill_row), (-1, bill_row), _LATE_BG)
                    )
                    style_cmds.append(
                        ("FONTNAME", (0, bill_row), (-1, bill_row), "Helvetica-Bold")
                    )

            sub_row = len(data)
            data.append(["", "", "Subtotal", _money(subtotal), ""])
            style_cmds.append(("BACKGROUND", (0, sub_row), (-1, sub_row), _SUBTOTAL_BG))
            style_cmds.append(
                ("FONTNAME", (2, sub_row), (3, sub_row), "Helvetica-Bold")
            )
            style_cmds.append(("ALIGN", (2, sub_row), (2, sub_row), "RIGHT"))

    col_widths = [2.3 * inch, 0.9 * inch, 0.9 * inch, 1.1 * inch, 0.9 * inch]
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(TableStyle(style_cmds))
    flow.append(table)

    # Running-balance summary
    available_label = (
        "Available to spend" if period.remaining_balance >= 0 else "Overspent"
    )
    bal_data = [
        ["Opening balance", _money(period.opening_balance)],
        ["Bills total", "-" + _money(period.total_bills)],
        [available_label, _money(period.remaining_balance)],
    ]
    bal = Table(bal_data, colWidths=[2.3 * inch, 1.1 * inch], hAlign="LEFT")
    bal_style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEABOVE", (0, 2), (-1, 2), 0.5, _GRID),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
    ]
    if period.remaining_balance < 0:
        bal_style.append(("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#991b1b")))
    bal.setStyle(TableStyle(bal_style))
    flow.append(Spacer(1, 4))
    flow.append(bal)
    return flow


def _monthly_flowables(monthly: MonthlySummaryResponse, styles) -> list:
    flow: list = [Paragraph("Monthly Summary", styles["section"])]
    if not monthly.months:
        flow.append(Paragraph("No months in range.", styles["empty"]))
        return flow

    header = ["Month", "Income", "Bills", "Net remaining"]
    data: list[list] = [header]
    for m in monthly.months:
        data.append(
            [
                _fmt_month(m.month),
                _money(m.total_income),
                _money(m.total_bills),
                _money(m.available),
            ]
        )

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, _GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Red text for any overspent (negative net) month.
    for i, m in enumerate(monthly.months, start=1):
        if m.available < 0:
            style_cmds.append(("TEXTCOLOR", (3, i), (3, i), colors.HexColor("#991b1b")))

    col_widths = [1.8 * inch, 1.3 * inch, 1.3 * inch, 1.5 * inch]
    table = Table(data, colWidths=col_widths, hAlign="LEFT")
    table.setStyle(TableStyle(style_cmds))
    flow.append(table)
    return flow


def _make_footer(generated_on, margin: float):
    """Build an onPage callback that draws the generated date and page number."""
    generated_label = f"Generated on {_fmt_date(generated_on)}"

    def _draw_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(_MUTED)
        y = 0.35 * inch
        canvas.drawString(margin, y, generated_label)
        canvas.drawRightString(letter[0] - margin, y, f"Page {doc.page}")
        canvas.restoreState()

    return _draw_footer


def render_budget_pdf(report: ReportData) -> bytes:
    """Render the assembled report data to PDF bytes."""
    buffer = BytesIO()
    margin = 0.6 * inch
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title="Budget Report",
    )
    styles = _styles()
    flow: list = []

    flow.append(Paragraph("Budget Report", styles["title"]))
    range_label = (
        f"{_fmt_date(report.schedule.summary.from_date)} &ndash; "
        f"{_fmt_date(report.schedule.summary.to_date)}"
    )
    flow.append(Paragraph(range_label, styles["subtitle"]))

    # Section 1 — Pay Period Schedule
    flow.append(Paragraph("Pay Period Schedule", styles["section"]))
    if not report.schedule.periods:
        flow.append(Paragraph("No pay periods in range.", styles["empty"]))
    else:
        for period in report.schedule.periods:
            flow.extend(_period_flowables(period, styles))

    # Section 2 — Monthly Summary
    flow.extend(_monthly_flowables(report.monthly, styles))

    footer = _make_footer(report.generated_on, margin)
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
