"""
pdf_generator.py — BatStateU-REC-ATT-11 (Strict University Format)
====================================================================
Matches the exact official layout used by Batangas State University:
  Header : Logo box | Document title | Reference / Effectivity / Revision
  Info   : Course Code & Title, Date, Time, Room/Venue, Assigned Faculty
  Body   : Two-column numbered list (NAME | SIGNATURE) — 30 rows each side
           Present students are filled in; remaining rows are left blank
  Footer : Prepared/Noted by signature lines
"""

import os
import re
from datetime import datetime

from reportlab.lib.pagesizes import LEGAL
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

PDF_DIR = "pdf"
os.makedirs(PDF_DIR, exist_ok=True)

BLACK  = colors.black
WHITE  = colors.white
GRAY   = colors.HexColor("#888888")
GREEN  = colors.HexColor("#1B5E20")


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _safe(s):
    return re.sub(r'[\\/:*?"<>|,\s]', '_', str(s)).strip('_')


def _fmt_time(ts):
    if not ts:
        return ""
    try:
        s = str(ts).split(".")[0]
        if " " in s:
            t = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        else:
            t = datetime.strptime(s[:8], "%H:%M:%S")
        return t.strftime("%I:%M %p")
    except Exception:
        return str(ts)[11:16] if len(str(ts)) > 10 else str(ts)


def _fmt_date(date):
    try:
        return datetime.strptime(date, "%Y-%m-%d").strftime("%-m/%-d/%Y")
    except Exception:
        return date


# ── MAIN GENERATOR ───────────────────────────────────────────────────────────

def generate_attendance_pdf(class_id, subject, section, room, date,
                             time_str="", faculty_name="Instructor",
                             records=None, session_time=""):
    if records is None:
        records = []

    filename = f"Log_{_safe(date)}_{_safe(session_time or 'session')}_{_safe(section)}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=LEGAL,
        rightMargin=1.8*cm, leftMargin=1.8*cm,
        topMargin=1.5*cm,   bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    # Common styles
    bold8c  = S("b8c",  fontSize=8,  fontName="Helvetica-Bold",  alignment=TA_CENTER)
    bold8   = S("b8",   fontSize=8,  fontName="Helvetica-Bold")
    norm8   = S("n8",   fontSize=8,  fontName="Helvetica")
    norm8c  = S("n8c",  fontSize=8,  fontName="Helvetica",        alignment=TA_CENTER)
    bold9c  = S("b9c",  fontSize=9,  fontName="Helvetica-Bold",  alignment=TA_CENTER)
    bold10c = S("b10c", fontSize=10, fontName="Helvetica-Bold",  alignment=TA_CENTER)
    norm7   = S("n7",   fontSize=7,  fontName="Helvetica",        textColor=GRAY, alignment=TA_CENTER)
    norm7l  = S("n7l",  fontSize=7,  fontName="Helvetica",        textColor=GRAY)

    story = []

    # ── HEADER TABLE ─────────────────────────────────────────────────────────
    # Col 1: University logo placeholder + name
    # Col 2: Document title (center)
    # Col 3: Reference / Effectivity / Revision (right side box)

    uni_block = Table([
        [Paragraph("Batangas State University\nARASof-Nasugbu Campus", bold8c)]
    ], colWidths=[4.2*cm])
    uni_block.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
    ]))

    title_block = Paragraph("STUDENT CLASS ATTENDANCE", bold10c)

    ref_data = [
        [Paragraph("Reference No.:", norm7l), Paragraph("BatStateU-REC-ATT-11", norm7l)],
        [Paragraph("Effectivity Date:", norm7l), Paragraph("May 18, 2022",         norm7l)],
        [Paragraph("Revision No.:",     norm7l), Paragraph("01",                   norm7l)],
    ]
    ref_block = Table(ref_data, colWidths=[2.5*cm, 3.0*cm])
    ref_block.setStyle(TableStyle([
        ("FONTSIZE",      (0,0),(-1,-1), 7),
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
    ]))

    hdr_tbl = Table(
        [[uni_block, title_block, ref_block]],
        colWidths=[4.2*cm, 8.0*cm, 5.5*cm]
    )
    hdr_tbl.setStyle(TableStyle([
        ("BOX",           (0,0),(-1,-1), 0.8, BLACK),
        ("INNERGRID",     (0,0),(-1,-1), 0.5, BLACK),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",         (1,0),(1,0),   "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
    ]))
    story.append(hdr_tbl)

    # ── INFO BLOCK ───────────────────────────────────────────────────────────
    # Row 1: Course Code and Title | (value spans) | Date | (value)
    # Row 2: Assigned Faculty      | (value spans) | Time | (value)
    # Row 3: Room/Venue            | (value spans) | (blank)

    disp_date = _fmt_date(date)

    info_data = [
        [
            Paragraph("Course Code and Title:", bold8),
            Paragraph(f"  {subject} ({section})", norm8),
            Paragraph("Date:", bold8),
            Paragraph(f"  {disp_date}", norm8),
        ],
        [
            Paragraph("Assigned Faculty:", bold8),
            Paragraph(f"  {faculty_name}", norm8),
            Paragraph("Time:", bold8),
            Paragraph(f"  {time_str}", norm8),
        ],
        [
            Paragraph("Room/Venue:", bold8),
            Paragraph(f"  {room}", norm8),
            Paragraph("", norm8),
            Paragraph("", norm8),
        ],
    ]
    info_tbl = Table(info_data, colWidths=[3.8*cm, 6.4*cm, 2.0*cm, 5.5*cm])
    info_tbl.setStyle(TableStyle([
        ("BOX",           (0,0),(-1,-1), 0.8, BLACK),
        ("INNERGRID",     (0,0),(-1,-1), 0.5, BLACK),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
    ]))
    story.append(info_tbl)

    # ── ATTENDANCE BODY ───────────────────────────────────────────────────────
    # University format: two columns of (No. | NAME | SIGNATURE)
    # 30 rows per column = 60 total slots
    # Present/Late students fill in their slot; rest are blank for manual sign

    present  = [r for r in records if r["status"] == "Present"]
    late     = [r for r in records if r["status"] == "Late"]
    absent   = [r for r in records if r["status"] == "Absent"]
    attended = present + late   # only attended students get a name slot

    ROWS_PER_COL = 30           # always 30 rows per column = 60 slots total

    # Build name lookup: slot index → student name + status
    slot_names = {}
    for idx, r in enumerate(attended):
        if idx < ROWS_PER_COL * 2:
            slot_names[idx] = r

    # Header row
    hdr_row = [
        Paragraph("NAME", bold8c),
        Paragraph("SIGNATURE", bold8c),
        Paragraph("NAME", bold8c),
        Paragraph("SIGNATURE", bold8c),
    ]

    body_rows = [hdr_row]
    row_styles = [
        ("BOX",           (0,0),(-1,-1), 0.8, BLACK),
        ("INNERGRID",     (0,0),(-1,-1), 0.5, BLACK),
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#D9D9D9")),
        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("LINEAFTER",     (1,0),(1,-1),  1.2, BLACK),   # thick divider between columns
    ]

    for i in range(ROWS_PER_COL):
        left_num  = i + 1
        right_num = i + 1 + ROWS_PER_COL

        left_r  = slot_names.get(i)
        right_r = slot_names.get(i + ROWS_PER_COL)

        # Left cell content
        if left_r:
            status_tag = " (Late)" if left_r["status"] == "Late" else ""
            left_name = Paragraph(
                f"{left_num}. {left_r['name']}{status_tag}",
                S(f"ln{i}", fontSize=8, fontName="Helvetica",
                  textColor=GREEN if left_r["status"] == "Present" else colors.HexColor("#E65100"))
            )
            left_sig = Paragraph(
                f"<font color='#1B5E20' size='7'>{'Present' if left_r['status']=='Present' else 'Late'}</font>",
                norm8c
            )
        else:
            left_name = Paragraph(f"{left_num}.", norm8)
            left_sig  = Paragraph("", norm8)

        # Right cell content
        if right_r:
            status_tag = " (Late)" if right_r["status"] == "Late" else ""
            right_name = Paragraph(
                f"{right_num}. {right_r['name']}{status_tag}",
                S(f"rn{i}", fontSize=8, fontName="Helvetica",
                  textColor=GREEN if right_r["status"] == "Present" else colors.HexColor("#E65100"))
            )
            right_sig = Paragraph(
                f"<font color='#1B5E20' size='7'>{'Present' if right_r['status']=='Present' else 'Late'}</font>",
                norm8c
            )
        else:
            right_name = Paragraph(f"{right_num}.", norm8)
            right_sig  = Paragraph("", norm8)

        body_rows.append([left_name, left_sig, right_name, right_sig])

    # Column widths: NAME wide, SIGNATURE narrower, repeated twice
    # Total usable width ≈ 17.7 cm (A4 minus margins)
    NAME_W = 5.8*cm
    SIG_W  = 3.15*cm
    att_tbl = Table(
        body_rows,
        colWidths=[NAME_W, SIG_W, NAME_W, SIG_W],
        repeatRows=1
    )
    att_tbl.setStyle(TableStyle(row_styles))

    story.append(Spacer(1, 0.15*cm))
    story.append(att_tbl)

    # ── ABSENT SECTION (below the main table) ────────────────────────────────
    if absent:
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(
            "Absent Students:",
            S("abshdr", fontSize=8, fontName="Helvetica-Bold", spaceAfter=3)
        ))
        abs_hdr = [
            Paragraph("#",    bold8c),
            Paragraph("NAME", bold8c),
        ]
        abs_rows = [abs_hdr]
        for idx, r in enumerate(absent, 1):
            abs_rows.append([
                Paragraph(str(idx), norm8c),
                Paragraph(r["name"], norm8),
            ])
        abs_tbl = Table(abs_rows, colWidths=[1.2*cm, 16.5*cm], repeatRows=1)
        abs_tbl.setStyle(TableStyle([
            ("BOX",           (0,0),(-1,-1), 0.8, BLACK),
            ("INNERGRID",     (0,0),(-1,-1), 0.5, BLACK),
            ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#D9D9D9")),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 3),
            ("BOTTOMPADDING", (0,0),(-1,-1), 3),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("ALIGN",         (0,0),(0,-1),  "CENTER"),
        ]))
        story.append(abs_tbl)

    # ── SIGNATURE / FOOTER ───────────────────────────────────────────────────
    story.append(Spacer(1, 0.6*cm))

    sig_data = [[
        Paragraph("Prepared by:", S("pb", fontSize=8, fontName="Helvetica")),
        Paragraph("Noted by:", S("nb", fontSize=8, fontName="Helvetica")),
    ]]
    sig_tbl = Table(sig_data, colWidths=[8.85*cm, 8.85*cm])
    sig_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0),(-1,-1), "TOP"),
        ("TOPPADDING", (0,0),(-1,-1), 0),
    ]))
    story.append(sig_tbl)

    story.append(Spacer(1, 1.2*cm))

    # Signature lines
    sig_line_data = [[
        Paragraph(
            f"<u>{'&nbsp;'*35}</u><br/>"
            f"<b>{faculty_name.upper()}</b><br/>"
            f"<font size='7' color='#888888'>Faculty / Instructor</font>",
            S("sl", fontSize=8, fontName="Helvetica", alignment=TA_CENTER)
        ),
        Paragraph(
            f"<u>{'&nbsp;'*35}</u><br/>"
            f"<b>&nbsp;</b><br/>"
            f"<font size='7' color='#888888'>Department Head / Dean</font>",
            S("sl2", fontSize=8, fontName="Helvetica", alignment=TA_CENTER)
        ),
    ]]
    sig_line_tbl = Table(sig_line_data, colWidths=[8.85*cm, 8.85*cm])
    sig_line_tbl.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "BOTTOM"),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
    ]))
    story.append(sig_line_tbl)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}  |  "
        f"Attendance Monitoring System  |  BatStateU-REC-ATT-11",
        norm7
    ))

    doc.build(story)
    print(f"[PDF] Saved: {filepath}")
    return filepath