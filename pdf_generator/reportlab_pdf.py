import os
import html
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Preformatted, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

DEFAULT_FONT_PATH = "fonts/DejaVuSans.ttf"


def register_fonts():
    try:
        if os.path.exists(DEFAULT_FONT_PATH):
            pdfmetrics.registerFont(TTFont("DejaVuSans", DEFAULT_FONT_PATH))
    except Exception:
        pass


def generate_pdf(run_meta: dict, results: list, summary: dict, out_path: str):
    register_fonts()
    styles = getSampleStyleSheet()

    base_font = (
        "DejaVuSans"
        if "DejaVuSans" in pdfmetrics.getRegisteredFontNames()
        else "Helvetica"
    )

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontName=base_font,
        fontSize=18,
        spaceAfter=10,
        textColor="#003566"
    )

    header_style = ParagraphStyle(
        "Header",
        parent=styles["Normal"],
        fontName=base_font,
        fontSize=11,
        leading=14,
    )

    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading3"],
        fontName=base_font,
        fontSize=13,
        spaceBefore=8,
        spaceAfter=4,
        textColor="#03045E"
    )

    normal_style = ParagraphStyle(
        "NormalFixed",
        parent=styles["Normal"],
        fontName=base_font,
        fontSize=10,
        leading=14,
    )

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    flow = []

    flow.append(Paragraph("SQL Validation Report", title_style))
    flow.append(Spacer(1, 6))

    meta_text = f"""
    <b>Name:</b> {html.escape(run_meta.get('name', '-'))}<br/>
    <b>Email:</b> {html.escape(run_meta.get('email', '-'))}<br/>
    <b>Team:</b> {html.escape(run_meta.get('team', '-'))}<br/>
    <b>CR Number:</b> {html.escape(run_meta.get('cr_number', '-'))}<br/>
    <b>Generated At:</b> {html.escape(run_meta.get('generated_at', ''))}
    """
    flow.append(Paragraph(meta_text, header_style))
    flow.append(Spacer(1, 10))

    summary_text = (
        f"<b>Total Queries:</b> {summary.get('total', 0)} &nbsp;&nbsp; "
        f"<b>Passed:</b> <font color='green'>{summary.get('passed', 0)}</font> &nbsp;&nbsp; "
        f"<b>Failed:</b> <font color='red'>{summary.get('failed', 0)}</font>"
    )
    flow.append(Paragraph(summary_text, header_style))
    flow.append(Spacer(1, 14))

    global_validations = summary.get("global_validations", [])
    warnings = summary.get("warnings", [])

    if global_validations:
        flow.append(Paragraph("File-Level Rules", section_title_style))
        for msg in global_validations:
            flow.append(
                Paragraph(
                    f"<font color='{_message_color(msg)}'>{html.escape(msg)}</font>",
                    normal_style
                )
            )
        flow.append(Spacer(1, 10))

    if warnings:
        flow.append(Paragraph("Warnings", section_title_style))
        for item in warnings:
            warning_text = f"Query {item.get('query_index')}: {item.get('message', '')}"
            flow.append(
                Paragraph(
                    f"<font color='{_message_color(item.get('message', ''))}'>{html.escape(warning_text)}</font>",
                    normal_style
                )
            )
        flow.append(Spacer(1, 10))

    flow.append(HRFlowable(width="100%", thickness=1, color="#cccccc"))
    flow.append(Spacer(1, 10))

    for idx, item in enumerate(results, start=1):
        flow.append(Paragraph(f"Query #{idx}", section_title_style))

        sql_text = _insert_soft_breaks(item.get("query", ""), 200)
        flow.append(Preformatted(sql_text, normal_style))
        flow.append(Spacer(1, 4))

        for msg in item.get("validations", []):
            safe_msg = html.escape(msg)
            flow.append(
                Paragraph(
                    f"<font color='{_message_color(msg)}'>{safe_msg}</font>",
                    normal_style
                )
            )

        flow.append(Spacer(1, 10))
        flow.append(HRFlowable(width="100%", thickness=0.8, color="#e0e0e0"))
        flow.append(Spacer(1, 10))

    doc.build(flow)
    return out_path


def _insert_soft_breaks(text, max_len):
    import re

    def repl(match):
        segment = match.group(0)
        if len(segment) <= max_len:
            return segment
        parts = [segment[i:i + max_len] for i in range(0, len(segment), max_len)]
        return "\u200b".join(parts)

    return re.sub(r"\S{" + str(max_len + 1) + r",}", repl, text)


def _message_color(message):
    clean = (message or "").lstrip()
    if clean.startswith("FAIL") or clean.startswith("❌") or clean.startswith("âŒ"):
        return "red"
    if clean.startswith("⚠️") or clean.startswith("âš ï¸"):
        return "#FFA500"
    return "green"
