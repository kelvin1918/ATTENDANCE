"""
pdf_generator.py
=================
Generates a downloadable PDF attendance report using ReportLab.

PDF layout:
    Header:  School name, Section, Subject, Room, Date, Time
    Body:    Table of Present and Late students with signature column
    Footer:  Total counts (Present / Late / Absent)

Called by app.py when teacher clicks the download button.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


PDF_DIR = "pdf"
os.makedirs(PDF_DIR, exist_ok=True)

# Brand color matching your #D32F2F theme
ACCENT = colors.HexColor("#D32F2F")
LIGHT  = colors.HexColor("#FFEBEE")
WHITE  = colors.white
BLACK  = colors.black
GRAY   = colors.HexColor("#757575")


def generate_attendance_pdf(
    class_id: int,
    subject:  str,
    section:  str,
    room:     str,
    date:     str,
    records:  list      # list of sqlite3.Row from get_attendance_session()
) -> str:
    """
    Generates the PDF and saves it to pdf/ folder.
    Returns the file path so Flask can serve it as a download.

    records = rows from attendance table, already sorted:
        Present → Late → Absent
    """

    filename = f"{section.replace('-','').replace(' ','')}_{date}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles  = getSampleStyleSheet()
    story   = []

    # ── Header styles ─────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "title",
        parent=styles["Normal"],
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=ACCENT,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "sub",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica",
        textColor=GRAY,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    label_style = ParagraphStyle(
        "label",
        parent=styles["Normal"],
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=BLACK,
        alignment=TA_LEFT,
    )

    # ── Title ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("Attendance Report", title_style))
    story.append(Paragraph("Attendance Monitoring System", sub_style))
    story.append(Spacer(1, 0.4 * cm))

    # ── Info block ────────────────────────────────────────────────────────────
    time_str = datetime.now().strftime("%I:%M %p")
    info_data = [
        ["Section:",  section,  "Date:",    date],
        ["Subject:",  subject,  "Time:",    time_str],
        ["Room:",     room,     "",         ""],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 7*cm, 2.5*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), ACCENT),
        ("TEXTCOLOR", (2, 0), (2, -1), ACCENT),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── Split records ─────────────────────────────────────────────────────────
    present = [r for r in records if r["status"] == "Present"]
    late    = [r for r in records if r["status"] == "Late"]
    absent  = [r for r in records if r["status"] == "Absent"]

    # ── Attendance table (Present + Late only — they sign) ────────────────────
    story.append(Paragraph("Attendance List", label_style))
    story.append(Spacer(1, 0.2 * cm))

    table_data = [["#", "Student ID", "Name", "Status", "Time In", "Signature"]]

    row_num = 1
    for r in present + late:
        table_data.append([
            str(row_num),
            r["student_id"] or "",
            r["name"],
            r["status"],
            r["timestamp"] or "",
            "",            # signature column — blank for handwriting
        ])
        row_num += 1

    if len(table_data) == 1:
        table_data.append(["", "", "No present or late students.", "", "", ""])

    col_widths = [1*cm, 3*cm, 5.5*cm, 2.5*cm, 2.5*cm, 4*cm]
    att_table  = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Row colors: header=accent, present=white, late=light yellow
    row_styles = [
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        # All rows
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("ROWBACKGROUND",(0, 1), (-1, -1), [WHITE, colors.HexColor("#F9F9F9")]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
    ]

    # Highlight Late rows in light amber
    for i, r in enumerate(present + late, start=1):
        if r["status"] == "Late":
            row_styles.append(
                ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FFF8E1"))
            )

    att_table.setStyle(TableStyle(row_styles))
    story.append(att_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── Absent list ───────────────────────────────────────────────────────────
    if absent:
        story.append(Paragraph("Absent Students", label_style))
        story.append(Spacer(1, 0.2 * cm))

        abs_data = [["#", "Student ID", "Name"]]
        for i, r in enumerate(absent, start=1):
            abs_data.append([str(i), r["student_id"] or "", r["name"]])

        abs_table = Table(abs_data, colWidths=[1*cm, 3*cm, 10*cm])
        abs_table.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#757575")),
            ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
            ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ROWBACKGROUND",(0, 1), (-1, -1), [WHITE, colors.HexColor("#F9F9F9")]),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(abs_table)
        story.append(Spacer(1, 0.6 * cm))

    # ── Summary footer ────────────────────────────────────────────────────────
    summary_data = [[
        f"Total: {len(records)}",
        f"Present: {len(present)}",
        f"Late: {len(late)}",
        f"Absent: {len(absent)}",
    ]]
    summary_table = Table(summary_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT),
        ("TEXTCOLOR",    (0, 0), (-1, -1), ACCENT),
        ("FONTNAME",     (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 11),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("BOX",          (0, 0), (-1, -1), 1, ACCENT),
        ("INNERGRID",    (0, 0), (-1, -1), 0.5, ACCENT),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 1 * cm))

    # ── Generated timestamp ───────────────────────────────────────────────────
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        ParagraphStyle("footer", parent=styles["Normal"],
                       fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    print(f"[PDF] Generated: {filepath}")
    return filepath