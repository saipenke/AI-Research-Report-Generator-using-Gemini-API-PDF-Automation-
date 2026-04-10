"""
utils/pdf_generator.py
-----------------------
PDF generation utility using ReportLab.
Produces professional, multi-section reports with cover page,
table of contents, body sections, and a references page.
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

logger = logging.getLogger(__name__)

# ── Colour palette ────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1A3C5E")
ACCENT_BLUE = colors.HexColor("#2E86AB")
LIGHT_GREY  = colors.HexColor("#F5F5F5")
MID_GREY    = colors.HexColor("#CCCCCC")
TEXT_BLACK  = colors.HexColor("#1C1C1C")


def _build_styles() -> dict:
    """Return a dict of named ParagraphStyles."""
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontSize=28, textColor=colors.white,
            alignment=TA_CENTER, spaceAfter=16,
            fontName="Helvetica-Bold", leading=34,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontSize=13, textColor=colors.HexColor("#DDDDDD"),
            alignment=TA_CENTER, spaceAfter=8,
            fontName="Helvetica",
        ),
        "toc_heading": ParagraphStyle(
            "toc_heading",
            fontSize=18, textColor=DARK_BLUE,
            fontName="Helvetica-Bold", spaceAfter=10,
            spaceBefore=20,
        ),
        "toc_entry": ParagraphStyle(
            "toc_entry",
            fontSize=11, textColor=TEXT_BLACK,
            fontName="Helvetica", spaceAfter=5, leftIndent=10,
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            fontSize=16, textColor=DARK_BLUE,
            fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=11, textColor=TEXT_BLACK,
            fontName="Helvetica", leading=17,
            alignment=TA_JUSTIFY, spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontSize=11, textColor=TEXT_BLACK,
            fontName="Helvetica", leading=16,
            leftIndent=20, spaceAfter=4,
            bulletIndent=10,
        ),
        "ref_heading": ParagraphStyle(
            "ref_heading",
            fontSize=14, textColor=DARK_BLUE,
            fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=8,
        ),
        "ref_item": ParagraphStyle(
            "ref_item",
            fontSize=9, textColor=colors.HexColor("#444444"),
            fontName="Helvetica", leading=13, leftIndent=15, spaceAfter=4,
        ),
    }
    return styles


def _sanitize(text: str) -> str:
    """Escape ReportLab XML special characters."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def _cover_page(story: list, topic: str, styles: dict, date_str: str):
    """Build a full-bleed dark-blue cover page."""
    # Coloured table as background block
    cover_table = Table(
        [[Paragraph(_sanitize(topic), styles["cover_title"])],
         [Paragraph("Research Report", styles["cover_sub"])],
         [Spacer(1, 0.4 * cm)],
         [Paragraph(f"Generated on {date_str}", styles["cover_sub"])],
         [Paragraph("Powered by Multi-Agent AI System", styles["cover_sub"])]],
        colWidths=[16 * cm],
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 24),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 24),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(Spacer(1, 3 * cm))
    story.append(cover_table)
    story.append(PageBreak())


def _toc_page(story: list, sections: List[str], styles: dict):
    """Build a simple Table of Contents page."""
    story.append(Paragraph("Table of Contents", styles["toc_heading"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_BLUE))
    story.append(Spacer(1, 0.4 * cm))

    for i, section in enumerate(sections, start=1):
        story.append(Paragraph(f"{i}.  {_sanitize(section)}", styles["toc_entry"]))

    story.append(PageBreak())


def _section(story: list, title: str, content: str, styles: dict):
    """Render one section: heading + body paragraphs / bullets."""
    story.append(Paragraph(_sanitize(title), styles["section_heading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 0.2 * cm))

    for para in content.split("\n"):
        para = para.strip()
        if not para:
            continue
        if para.startswith("- ") or para.startswith("• "):
            bullet_text = para.lstrip("-•").strip()
            story.append(Paragraph(f"• {_sanitize(bullet_text)}", styles["bullet"]))
        else:
            story.append(Paragraph(_sanitize(para), styles["body"]))

    story.append(Spacer(1, 0.4 * cm))


def generate_pdf(research_data: Dict[str, Any], output_dir: str = "generated_reports") -> str:
    """
    Generate a PDF report from structured research data.

    Args:
        research_data: Dict with keys:
            - topic (str)
            - introduction, background, key_concepts,
              insights, applications, conclusion (str each)
            - references (list[str])
        output_dir: Directory to save the PDF.

    Returns:
        Absolute path to the generated PDF file.
    """
    os.makedirs(output_dir, exist_ok=True)

    topic      = research_data.get("topic", "Research Report")
    date_str   = datetime.now().strftime("%B %d, %Y")
    safe_name  = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_")
    filename   = f"{safe_name}_Report.pdf"
    filepath   = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.5 * cm,  bottomMargin=2.5 * cm,
        title=f"{topic} — Research Report",
        author="Multi-Agent AI System",
    )

    styles  = _build_styles()
    story   = []

    # 1. Cover page
    _cover_page(story, topic, styles, date_str)

    # 2. Table of Contents
    section_titles = [
        "Introduction", "Background", "Key Concepts",
        "Important Insights", "Applications", "Conclusion", "References",
    ]
    _toc_page(story, section_titles, styles)

    # 3. Body sections
    body_sections = {
        "Introduction":       research_data.get("introduction", ""),
        "Background":         research_data.get("background", ""),
        "Key Concepts":       research_data.get("key_concepts", ""),
        "Important Insights": research_data.get("insights", ""),
        "Applications":       research_data.get("applications", ""),
        "Conclusion":         research_data.get("conclusion", ""),
    }

    for title, content in body_sections.items():
        if content.strip():
            _section(story, title, content, styles)

    # 4. References
    references: List[str] = research_data.get("references", [])
    if references:
        story.append(Paragraph("References", styles["ref_heading"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
        story.append(Spacer(1, 0.2 * cm))
        for ref in references:
            story.append(Paragraph(f"[•] {_sanitize(ref)}", styles["ref_item"]))

    doc.build(story)
    logger.info(f"[PDFGenerator] Saved → {filepath}")
    return os.path.abspath(filepath)
