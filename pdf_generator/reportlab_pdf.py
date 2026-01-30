import os
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
            pdfmetrics.registerFont(TTFont('DejaVuSans', DEFAULT_FONT_PATH))
    except Exception:
        pass


def generate_pdf(run_meta: dict, results: list, summary: dict, out_path: str):

    register_fonts()
    styles = getSampleStyleSheet()

    # Use DejaVu if installed
    base_font = (
        'DejaVuSans'
        if 'DejaVuSans' in pdfmetrics.getRegisteredFontNames()
        else 'Helvetica'
    )

    title_style = ParagraphStyle(
        "Title",
        parent=styles['Heading1'],
        fontName=base_font,
        fontSize=18,
        spaceAfter=10,
        textColor="#003566"
    )

    header_style = ParagraphStyle(
        "Header",
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=11,
        leading=14,
    )

    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles['Heading3'],
        fontName=base_font,
        fontSize=13,
        spaceBefore=8,
        spaceAfter=4,
        textColor="#03045E"
    )

    normal_style = ParagraphStyle(
        "NormalFixed",
        parent=styles['Normal'],
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

    # -------------------------
    # TITLE
    # -------------------------
    flow.append(Paragraph("SQL Validation Report", title_style))
    flow.append(Spacer(1, 6))

    # -------------------------
    # META BLOCK
    # -------------------------
    meta_text = f"""
    <b>Name:</b> {run_meta.get('name', '-')}<br/>
    <b>Email:</b> {run_meta.get('email', '-')}<br/>
    <b>Team:</b> {run_meta.get('team', '-')}<br/>
    <b>CR Number:</b> {run_meta.get('cr_number', '-')}<br/>
    <b>Generated At:</b> {run_meta.get('generated_at', '')}
    """
    flow.append(Paragraph(meta_text, header_style))
    flow.append(Spacer(1, 10))

    # -------------------------
    # AI SECTION
    # -------------------------
    if summary.get('ai_summary'):
        flow.append(Paragraph("AI Executive Summary", section_title_style))
        flow.append(Paragraph(summary['ai_summary'], normal_style))
        flow.append(Spacer(1, 12))

    if summary.get('ai_insights'):
        flow.append(Paragraph("AI Logic & Performance Analysis", section_title_style))
        for insight in summary['ai_insights']:
            # Color code based on severity
            sev = insight.get('severity', 'Low')
            color = "#333333"
            if sev == 'High': color = "#b91c1c" # red
            elif sev == 'Medium': color = "#b45309" # amber

            p_text = f"<b>[{insight.get('type')}]</b> <font color='{color}'>{insight.get('message')}</font>"
            flow.append(Paragraph(p_text, normal_style))
        
        flow.append(Spacer(1, 12))
        flow.append(HRFlowable(width="100%", thickness=1, color="#cccccc"))
        flow.append(Spacer(1, 10))

    # -------------------------
    # SUMMARY
    # -------------------------
    summary_text = (
        f"<b>Total Queries:</b> {summary.get('total',0)} &nbsp;&nbsp; "
        f"<b>Passed:</b> <font color='green'>{summary.get('passed',0)}</font> &nbsp;&nbsp; "
        f"<b>Failed:</b> <font color='red'>{summary.get('failed',0)}</font>"
    )
    flow.append(Paragraph(summary_text, header_style))
    flow.append(Spacer(1, 14))

    flow.append(HRFlowable(width="100%", thickness=1, color="#cccccc"))
    flow.append(Spacer(1, 10))

    # -------------------------
    # EACH QUERY
    # -------------------------
    for idx, item in enumerate(results, start=1):

        flow.append(Paragraph(f"Query #{idx}", section_title_style))

        # SQL block
        sql_text = item.get("query", "")
        sql_text = _insert_soft_breaks(sql_text, 200)

        flow.append(Preformatted(sql_text, normal_style))
        flow.append(Spacer(1, 4))

        # Validation messages
        for msg in item.get("validations", []):
            clean = msg.lstrip()   # <-- THIS FIXES IT

            if clean.startswith("❌"):
                color = "red"
            elif clean.startswith("⚠️"):
                color = "#FFA500"  # orange / yellow
            else:
                color = "green"

            flow.append(
                Paragraph(f"<font color='{color}'>{msg}</font>", normal_style)
            )


        flow.append(Spacer(1, 10))
        flow.append(HRFlowable(width="100%", thickness=0.8, color="#e0e0e0"))
        flow.append(Spacer(1, 10))

    doc.build(flow)
    return out_path


def _insert_soft_breaks(text, max_len):
    """Prevents long lines from breaking the entire PDF layout."""
    import re

    def repl(m):
        s = m.group(0)
        if len(s) > max_len:
            parts = [s[i:i + max_len] for i in range(0, len(s), max_len)]
            return "\u200b".join(parts)
        return s

    return re.sub(r'\S{' + str(max_len + 1) + r',}', repl, text)
