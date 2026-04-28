"""
pdf_generator.py — BatStateU-REC-ATT-11 Revision 01
=====================================================
FIXED in this version:
  ✓ Footer removed (no Prepared by / Noted by / timestamp)
  ✓ Page size: 8.5" × 13" (Folio/F4)
  ✓ Margins: top=17.5mm left=25.4mm bottom=6.3mm right=25.4mm
  ✓ All borders: 0.5 pt throughout
  ✓ NAME/SIGNATURE header row: white (NOT gray-shaded)
  ✓ Gray shade on divider bar ONLY (between info block and roster)
  ✓ Seamless flush borders between all stacked tables (no gaps/doubles)

Layout (matches HTML reference exactly):
  HDR ROW 0 : Logo (14%) | Reference No. (29%) | Effectivity Date (32%) | Revision No. (25%)
  HDR ROW 1 : STUDENT CLASS ATTENDANCE  (spans full width)
  INFO ROW 0 : Course Code and Title          (full width)
  INFO ROW 1 : Assigned Faculty               (full width)
  INFO ROW 2 : Date (25%) | Time (30%) | Room/Venue (45%)
  INFO ROW 3 : ████ GRAY DIVIDER ████         (full width, 8 pt tall)
  ROSTER HDR : NAME | SIGNATURE | NAME | SIGNATURE  (white, bold, centered)
  ROWS 1-30  : numbered slots — present/late filled; blanks for manual sign
"""

import os
import re
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── OUTPUT DIR ───────────────────────────────────────────────────────────────
PDF_DIR  = "pdf"
os.makedirs(PDF_DIR, exist_ok=True)

# ── COLOURS ──────────────────────────────────────────────────────────────────
BLACK      = colors.black
GRAY_LIGHT = colors.HexColor("#D9D9D9")   # divider bar only
GREEN      = colors.HexColor("#1B5E20")   # Present name
ORANGE     = colors.HexColor("#E65100")   # Late name

# ── FONTS ────────────────────────────────────────────────────────────────────
TNR      = "Times-Roman"
TNR_BOLD = "Times-Bold"

# ── PAGE GEOMETRY ────────────────────────────────────────────────────────────
# 8.5" × 13" Folio/F4
PAGE_W   = 8.5 * inch    # 612 pt
PAGE_H   = 13  * inch    # 936 pt
TOP_M    = 17.5 * mm     # 49.6 pt
LEFT_M   = 25.4 * mm     # 72 pt  (= 1 inch)
BOTTOM_M = 6.3  * mm     # 17.9 pt
RIGHT_M  = 25.4 * mm     # 72 pt
USABLE   = PAGE_W - LEFT_M - RIGHT_M   # 468 pt

# ── BORDER WEIGHT ─────────────────────────────────────────────────────────────
B = 0.5     # 0.5 pt everywhere — do NOT change per-table

# ── COLUMN WIDTHS (derived from HTML percentages × USABLE) ───────────────────
# Header row
H_LOGO = USABLE * 0.14
H_REF  = USABLE * 0.29
H_EFF  = USABLE * 0.32
H_REV  = USABLE * 0.25

# Info / date-time-room row
I_DATE = USABLE * 0.25
I_TIME = USABLE * 0.30
I_ROOM = USABLE * 0.45

# Roster (35 / 15 / 35 / 15 %)
R_NAME = USABLE * 0.35
R_SIG  = USABLE * 0.15

# ── HELPERS ──────────────────────────────────────────────────────────────────

def _safe(s):
    return re.sub(r'[\\/:*?"<>|,\s]', '_', str(s)).strip('_')

def _fmt_date(d):
    try:
        o = datetime.strptime(d, "%Y-%m-%d")
        return f"{o.month}/{o.day}/{o.year}"
    except Exception:
        return d

def _p(name, styles, **kw):
    return ParagraphStyle(name, parent=styles["Normal"], **kw)

# ── BORDER HELPER: box WITHOUT top border ─────────────────────────────────────
# Used for every table that sits directly below another — prevents double lines.
def _no_top(extra=None):
    cmds = [
        ("LINEBEFORE", (0,  0), (0,  -1), B, BLACK),   # left edge
        ("LINEAFTER",  (-1, 0), (-1, -1), B, BLACK),   # right edge
        ("LINEBELOW",  (0,  -1), (-1, -1), B, BLACK),  # bottom edge
        ("INNERGRID",  (0,  0), (-1, -1), B, BLACK),   # internal grid
    ]
    if extra:
        cmds.extend(extra)
    return cmds


# ── SIGNATURE CELL HELPER ──────────────────────────────────────────────────────
#
# The SIGNATURE column is ~15% of usable width (R_SIG pts).
# We scale-fit the student's uploaded e-signature image to fill the cell.
# Falls back to coloured "Present"/"Late" text if no image is found on disk.

SIG_MAX_W = R_SIG - 6   # ~57 pt — leave 3 pt padding each side
SIG_MAX_H = 12           # row height is 14 pt; keep 1 pt top/bottom clearance


def _sig_cell(sig_path, status, sig_col, norm9c_style, ps_fn):
    """
    Return a ReportLab flowable for the SIGNATURE column cell.

    Priority:
      1. Valid file on disk  → scale-fit RLImage embedded in the PDF.
      2. No file / error     → coloured text fallback ("Present" / "Late").

    Parameters
    ----------
    sig_path     : str  — relative path stored in students.signature
                          e.g. "uploads/signatures/JohnDoe.png"
    status       : str  — "Present" or "Late"
    sig_col      : str  — hex colour for the text fallback
    norm9c_style : ParagraphStyle — centred 9 pt style
    ps_fn        : callable — ps() factory (unused but kept for symmetry)
    """
    if sig_path and os.path.isfile(sig_path):
        try:
            img = RLImage(sig_path)
            nat_w, nat_h = img.imageWidth, img.imageHeight
            if nat_w > 0 and nat_h > 0:
                scale          = min(SIG_MAX_W / nat_w, SIG_MAX_H / nat_h, 1.0)
                img.drawWidth  = nat_w * scale
                img.drawHeight = nat_h * scale
                img.hAlign     = "CENTER"
                return img
        except Exception:
            pass   # fall through to text fallback

    # Text fallback
    return Paragraph(
        f'<font color="{sig_col}" size="8">{status}</font>',
        norm9c_style
    )



# ── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

def generate_attendance_pdf(class_id, subject, section, room, date,
                             time_str="", faculty_name="Instructor",
                             records=None, session_time=""):
    if records is None:
        records = []

    filename = f"Log_{_safe(date)}_{_safe(session_time or 'session')}_{_safe(section)}.pdf"
    filepath  = os.path.join(PDF_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=LEFT_M,  rightMargin=RIGHT_M,
        topMargin=TOP_M,    bottomMargin=BOTTOM_M,
    )

    # ── PARAGRAPH STYLES ─────────────────────────────────────────────────────
    ss = getSampleStyleSheet()

    def ps(name, **kw):
        return _p(name, ss, **kw)

    norm9   = ps("n9",   fontSize=9,  fontName=TNR)
    norm9c  = ps("n9c",  fontSize=9,  fontName=TNR,      alignment=TA_CENTER)
    norm10  = ps("n10",  fontSize=10, fontName=TNR)
    bold10c = ps("b10c", fontSize=10, fontName=TNR_BOLD,  alignment=TA_CENTER)
    bold12c = ps("b12c", fontSize=12, fontName=TNR_BOLD,  alignment=TA_CENTER)
    bold9c  = ps("b9c",  fontSize=9,  fontName=TNR_BOLD,  alignment=TA_CENTER)

    story   = []

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE 1 — HEADER
    # Rows: 0 = Logo | Ref No. | Effectivity Date | Revision No.
    #        1 = "STUDENT CLASS ATTENDANCE"  (SPAN all 4)
    # Uses full BOX (all 4 sides) because it is the first table on the page.
    # ══════════════════════════════════════════════════════════════════════════
    LOGO_PATH = "bsu_logo.png"
    if os.path.exists(LOGO_PATH):
        logo_cell = RLImage(LOGO_PATH, width=38, height=38)   # ~1.34 cm square
    else:
        logo_cell = Paragraph(
            "Batangas State<br/>University",
            ps("lc", fontSize=7, fontName=TNR_BOLD, alignment=TA_CENTER)
        )

    hdr_data = [
        [
            logo_cell,
            Paragraph("Reference\nNo.:  <b>BatStateU-REC-ATT-11</b>",
                      ps("rn", fontSize=9, fontName=TNR, leading=13)),
            Paragraph("Effectivity Date:  <b>May 18, 2022</b>",
                      ps("ed", fontSize=9, fontName=TNR)),
            Paragraph("Revision No.:  <b>01</b>",
                      ps("rv", fontSize=9, fontName=TNR)),
        ],
        [Paragraph("STUDENT CLASS ATTENDANCE", bold12c), "", "", ""],
    ]

    hdr_tbl = Table(hdr_data, colWidths=[H_LOGO, H_REF, H_EFF, H_REV])
    hdr_tbl.setStyle(TableStyle([
        # Full outer border (first table — needs top too)
        ("BOX",           (0, 0), (-1, -1), B, BLACK),
        # Inner grid for row 0 only (vertical dividers between logo/ref/eff/rev)
        ("INNERGRID",     (0, 0), (-1,  0), B, BLACK),
        # Horizontal line between row 0 and row 1
        ("LINEBELOW",     (0, 0), (-1,  0), B, BLACK),
        # Span for title row
        ("SPAN",          (0, 1), (-1,  1)),
        # Alignment
        ("ALIGN",         (0, 0), (0,  0), "CENTER"),
        ("ALIGN",         (0, 1), (-1, 1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # Padding row 0
        ("TOPPADDING",    (0, 0), (-1,  0), 6),
        ("BOTTOMPADDING", (0, 0), (-1,  0), 6),
        ("LEFTPADDING",   (1, 0), (-1,  0), 6),
        ("RIGHTPADDING",  (0, 0), (-1,  0), 4),
        # Padding row 1 (title)
        ("TOPPADDING",    (0, 1), (-1,  1), 7),
        ("BOTTOMPADDING", (0, 1), (-1,  1), 7),
    ]))
    story.append(hdr_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE 2 — INFO BLOCK + GRAY DIVIDER (one combined table, 3 columns)
    # Columns: I_DATE (25%) | I_TIME (30%) | I_ROOM (45%)
    # Row 0: Course Code and Title   → SPAN all 3
    # Row 1: Assigned Faculty        → SPAN all 3
    # Row 2: Date | Time | Room/Venue
    # Row 3: Gray divider            → SPAN all 3, 8 pt tall, GRAY_LIGHT bg
    #
    # NO top border (header's bottom serves as the separator — prevents double line).
    # ══════════════════════════════════════════════════════════════════════════
    disp_date = _fmt_date(date)

    info_data = [
        [Paragraph(f"Course Code and Title:  <b>{subject}</b>  ({section})",
                   ps("cc", fontSize=10, fontName=TNR)), "", ""],
        [Paragraph(f"Assigned Faculty:  <b>{faculty_name}</b>",
                   ps("af", fontSize=10, fontName=TNR)), "", ""],
        [
            Paragraph(f"Date: <b>{disp_date}</b>",  ps("dt", fontSize=10, fontName=TNR)),
            Paragraph(f"Time: <b>{time_str}</b>",   ps("tm", fontSize=10, fontName=TNR)),
            Paragraph(f"Room/Venue: <b>{room}</b>", ps("rm", fontSize=10, fontName=TNR)),
        ],
        ["", "", ""],   # gray divider row — blank, styled below
    ]

    info_tbl = Table(
        info_data,
        colWidths=[I_DATE, I_TIME, I_ROOM],
        rowHeights=[None, None, None, 8],   # 8 pt for the gray bar
    )
    info_tbl.setStyle(TableStyle(_no_top([
        # Spans
        ("SPAN",          (0, 0), (-1,  0)),   # Course Code full width
        ("SPAN",          (0, 1), (-1,  1)),   # Faculty full width
        ("SPAN",          (0, 3), (-1,  3)),   # Divider full width
        # Gray divider background
        ("BACKGROUND",    (0, 3), (-1,  3), GRAY_LIGHT),
        # Text alignment
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (-1,  2), "LEFT"),
        # Padding (rows 0-2 only; divider row has 0 padding)
        ("TOPPADDING",    (0, 0), (-1,  2), 5),
        ("BOTTOMPADDING", (0, 0), (-1,  2), 5),
        ("LEFTPADDING",   (0, 0), (-1,  2), 8),
        ("RIGHTPADDING",  (0, 0), (-1,  2), 4),
        ("TOPPADDING",    (0, 3), (-1,  3), 0),
        ("BOTTOMPADDING", (0, 3), (-1,  3), 0),
        ("LEFTPADDING",   (0, 3), (-1,  3), 0),
        ("RIGHTPADDING",  (0, 3), (-1,  3), 0),
    ])))
    story.append(info_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE 3 — ATTENDANCE ROSTER
    # 4 columns: NAME (35%) | SIGNATURE (15%) | NAME (35%) | SIGNATURE (15%)
    # Row 0:    header  — WHITE background, bold, centered
    # Rows 1-30: data   — present/late filled; blanks for manual sign
    #
    # NO top border (info table's bottom = separator).
    # GRAY shade on header is REMOVED — white only (matches HTML reference).
    # ══════════════════════════════════════════════════════════════════════════
    present  = [r for r in records if r.get("status") == "Present"]
    late     = [r for r in records if r.get("status") == "Late"]
    absent   = [r for r in records if r.get("status") == "Absent"]
    attended = present + late

    ROWS_PER_COL = 30
    slot = {}
    for idx, r in enumerate(attended):
        if idx < ROWS_PER_COL * 2:
            slot[idx] = r

    # Header row — white bg, bold, centered (NO GRAY)
    roster_rows = [[
        Paragraph("NAME",      bold9c),
        Paragraph("SIGNATURE", bold9c),
        Paragraph("NAME",      bold9c),
        Paragraph("SIGNATURE", bold9c),
    ]]

    for i in range(ROWS_PER_COL):
        left_r  = slot.get(i)
        right_r = slot.get(i + ROWS_PER_COL)

        # ── left half ────────────────────────────────────────────────────────
        if left_r:
            st      = left_r["status"]
            tag     = " (Late)" if st == "Late" else ""
            col     = BLACK if st == "Present" else ORANGE
            sig_col = "#1B5E20" if st == "Present" else "#E65100"
            l_nm    = Paragraph(f"{i+1}. {left_r['name']}{tag}",
                                ps(f"ln{i}", fontSize=9, fontName=TNR, textColor=col))
            l_sg    = _sig_cell(left_r.get("sig_path", ""), st, sig_col, norm9c, ps)
        else:
            l_nm = Paragraph(f"{i+1}.", ps(f"le{i}", fontSize=9, fontName=TNR))
            l_sg = Paragraph("", norm9)

        # ── right half ───────────────────────────────────────────────────────
        if right_r:
            st      = right_r["status"]
            tag     = " (Late)" if st == "Late" else ""
            col     = BLACK if st == "Present" else ORANGE
            sig_col = "#1B5E20" if st == "Present" else "#E65100"
            r_nm    = Paragraph(f"{i+1+ROWS_PER_COL}. {right_r['name']}{tag}",
                                ps(f"rn{i}", fontSize=9, fontName=TNR, textColor=col))
            r_sg    = _sig_cell(right_r.get("sig_path", ""), st, sig_col, norm9c, ps)
        else:
            r_nm = Paragraph(f"{i+1+ROWS_PER_COL}.", ps(f"re{i}", fontSize=9, fontName=TNR))
            r_sg = Paragraph("", norm9)

        roster_rows.append([l_nm, l_sg, r_nm, r_sg])

    roster_tbl = Table(
        roster_rows,
        colWidths=[R_NAME, R_SIG, R_NAME, R_SIG],
        repeatRows=1,
        rowHeights=[16] + [14] * ROWS_PER_COL,  # compact rows, 14 pt each
    )
    roster_tbl.setStyle(TableStyle(_no_top([
        # Alignment
        ("ALIGN",         (0, 0), (-1,  0), "CENTER"),   # header centred
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
        # No background on header row (white — matches reference)
        # Data rows also white — no alternating shading
    ])))
    story.append(roster_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # ABSENT SECTION — listed below roster only when absences exist
    # (not part of the 60 numbered slots; kept outside the official box)
    # ══════════════════════════════════════════════════════════════════════════
    if absent:
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            "Absent Students:",
            ps("abshdr", fontSize=9, fontName=TNR_BOLD, spaceAfter=2)
        ))
        abs_rows = [[
            Paragraph("#",       bold9c),
            Paragraph("NAME",    bold9c),
            Paragraph("SR CODE", bold9c),
        ]]
        for idx, r in enumerate(absent, 1):
            abs_rows.append([
                Paragraph(str(idx), norm9c),
                Paragraph(r.get("name", ""),    ps(f"an{idx}", fontSize=9, fontName=TNR)),
                Paragraph(r.get("sr_code", ""), norm9c),
            ])
        abs_tbl = Table(
            abs_rows,
            colWidths=[0.45 * inch, USABLE * 0.70, USABLE * 0.20],
            repeatRows=1,
        )
        abs_tbl.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), B, BLACK),
            ("INNERGRID",     (0, 0), (-1, -1), B, BLACK),
            ("BACKGROUND",    (0, 0), (-1,  0), GRAY_LIGHT),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("ALIGN",         (0, 0), (0,  -1), "CENTER"),
            ("ALIGN",         (2, 0), (2,  -1), "CENTER"),
        ]))
        story.append(abs_tbl)

    # ── BUILD ────────────────────────────────────────────────────────────────
    doc.build(story)
    print(f"[PDF] Saved: {filepath}")
    return filepath