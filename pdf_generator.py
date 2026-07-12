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
  ✓ PDF generated in-memory (BytesIO) — no disk writes, safe on Render

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
from io import BytesIO
import urllib.request
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── COLOURS ──────────────────────────────────────────────────────────────────
BLACK      = colors.black
GRAY_LIGHT = colors.HexColor("#D9D9D9")   # divider bar only
GREEN      = colors.HexColor("#1B5E20")   # Present name
ORANGE     = colors.HexColor("#E65100")   # Late/Partial/Excused name — same
                                           # existing color, reused, not new

# Non-Present attended statuses get a parenthetical tag after the name —
# same mechanism "(Late)" already used, just extended to the two new
# statuses. Sheet layout/colors otherwise stay exactly as before.
STATUS_TAG = {"Late": " (Late)", "Partial": " (Partial)", "Excused": " (Excused)"}

# ── FONTS ────────────────────────────────────────────────────────────────────
TNR      = "Times-Roman"
TNR_BOLD = "Times-Bold"

# ── PAGE GEOMETRY ────────────────────────────────────────────────────────────
PAGE_W   = 8.5 * inch
PAGE_H   = 13  * inch
TOP_M    = 17.5 * mm
LEFT_M   = 25.4 * mm
BOTTOM_M = 6.3  * mm
RIGHT_M  = 25.4 * mm
USABLE   = PAGE_W - LEFT_M - RIGHT_M   # 468 pt

# ── BORDER WEIGHT ─────────────────────────────────────────────────────────────
B = 0.5

# ── COLUMN WIDTHS ─────────────────────────────────────────────────────────────
H_LOGO = USABLE * 0.14
H_REF  = USABLE * 0.29
H_EFF  = USABLE * 0.32
H_REV  = USABLE * 0.25

I_DATE = USABLE * 0.35
I_TIME = USABLE * 0.15
I_ROOM = USABLE * 0.50

R_NAME = USABLE * 0.35
R_SIG  = USABLE * 0.15

SIG_MAX_W = R_SIG - 6
SIG_MAX_H = 12

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

def _no_top(extra=None):
    """Box border without top edge — prevents double lines when stacking tables."""
    cmds = [
        ("LINEBEFORE", (0,  0), (0,  -1), B, BLACK),
        ("LINEAFTER",  (-1, 0), (-1, -1), B, BLACK),
        ("LINEBELOW",  (0,  -1), (-1, -1), B, BLACK),
        ("INNERGRID",  (0,  0), (-1, -1), B, BLACK),
    ]
    if extra:
        cmds.extend(extra)
    return cmds


# ── SIGNATURE IMAGE FETCHER ───────────────────────────────────────────────────

def _fetch_image_bytes(url):
    """Download image from Cloudinary URL. Returns b'' on failure.
    Caches by URL to avoid duplicate downloads within one PDF request."""
    if url in _fetch_image_bytes._cache:
        return _fetch_image_bytes._cache[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
            _fetch_image_bytes._cache[url] = data
            return data
    except Exception as e:
        print(f"[PDF] Could not fetch signature from {url}: {e}")
        _fetch_image_bytes._cache[url] = b""
        return b""

_fetch_image_bytes._cache = {}


def _sig_cell(sig_path, status, norm9c_style):
    """Return a ReportLab flowable for the SIGNATURE column cell."""
    # "SIGNED" marker — render as plain text for attended, blank for absent.
    # Partial/Excused count as attended: the signature represents that the
    # student was physically in class, same as a manual paper sheet would —
    # only a genuinely undetected/Absent student gets a blank cell.
    if sig_path == "SIGNED":
        attended = status in ("Present", "Late", "Partial", "Excused")
        if not attended:
            return Paragraph("", norm9c_style)
        return Paragraph(
            "SIGNED",
            ParagraphStyle("signed_txt", parent=norm9c_style, alignment=TA_CENTER,
                           spaceAfter=0, spaceBefore=0)
        )

    # Legacy: render stored signature image for old records
    if sig_path:
        img_src = None
        if sig_path.startswith("http://") or sig_path.startswith("https://"):
            raw = _fetch_image_bytes(sig_path)
            if raw:
                img_src = BytesIO(raw)
        elif os.path.isfile(sig_path):
            img_src = sig_path

        if img_src is not None:
            try:
                img = RLImage(img_src)
                nat_w, nat_h = img.imageWidth, img.imageHeight
                if nat_w > 0 and nat_h > 0:
                    scale          = min(SIG_MAX_W / nat_w, SIG_MAX_H / nat_h, 1.0)
                    img.drawWidth  = nat_w * scale
                    img.drawHeight = nat_h * scale
                    img.hAlign     = "CENTER"
                    return img
            except Exception as e:
                print(f"[PDF] Image render error: {e}")

    return Paragraph("", norm9c_style)


# ── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

def generate_attendance_pdf(class_id, subject, section, room, date,
                             time_str="", faculty_name="Instructor",
                             records=None, session_time=""):
    if records is None:
        records = []

    filename = f"Log_{_safe(date)}_{_safe(session_time or 'session')}_{_safe(section)}.pdf"
    buf      = BytesIO()

    doc = SimpleDocTemplate(
        buf,
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
    # ══════════════════════════════════════════════════════════════════════════
    LOGO_PATH = "bsu_logo.png"
    if os.path.exists(LOGO_PATH):
        logo_cell = RLImage(LOGO_PATH, width=38, height=38)
    else:
        logo_cell = Paragraph(
            "Batangas State<br/>University",
            ps("lc", fontSize=7, fontName=TNR_BOLD, alignment=TA_CENTER)
        )

    hdr_data = [
        [
            logo_cell,
            Paragraph("Reference No.:  BatStateU-REC-ATT-11",
                      ps("rn", fontSize=9, fontName=TNR, leading=13)),
            Paragraph("Effectivity Date:  May 18, 2022",
                      ps("ed", fontSize=9, fontName=TNR)),
            Paragraph("Revision No.:  01",
                      ps("rv", fontSize=9, fontName=TNR)),
        ],
        [Paragraph("STUDENT CLASS ATTENDANCE", bold12c), "", "", ""],
    ]

    hdr_tbl = Table(hdr_data, colWidths=[H_LOGO, H_REF, H_EFF, H_REV])
    hdr_tbl.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), B, BLACK),
        ("INNERGRID",     (0, 0), (-1,  0), B, BLACK),
        ("LINEBELOW",     (0, 0), (-1,  0), B, BLACK),
        ("SPAN",          (0, 1), (-1,  1)),
        ("ALIGN",         (0, 0), (0,  0), "CENTER"),
        ("ALIGN",         (0, 1), (-1, 1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1,  0), 6),
        ("BOTTOMPADDING", (0, 0), (-1,  0), 6),
        ("LEFTPADDING",   (1, 0), (-1,  0), 6),
        ("RIGHTPADDING",  (0, 0), (-1,  0), 4),
        ("TOPPADDING",    (0, 1), (-1,  1), 7),
        ("BOTTOMPADDING", (0, 1), (-1,  1), 7),
    ]))
    story.append(hdr_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE 2 — INFO BLOCK + GRAY DIVIDER
    # ══════════════════════════════════════════════════════════════════════════
    disp_date = _fmt_date(date)

    info_data = [
        [Paragraph(f"Course Code and Title:  {subject}  ({section})",
                   ps("cc", fontSize=10, fontName=TNR)), "", ""],
        [Paragraph(f"Name of Faculty:  {faculty_name}",
                   ps("af", fontSize=10, fontName=TNR)), "", ""],
        [
            Paragraph(f"Date: {disp_date}",     ps("dt", fontSize=10, fontName=TNR)),
            Paragraph(f"Time: {time_str}",      ps("tm", fontSize=10, fontName=TNR)),
            Paragraph(f"Room/Venue: {room}",    ps("rm", fontSize=10, fontName=TNR)),
        ],
        ["", "", ""],   # gray divider row
    ]

    info_tbl = Table(
        info_data,
        colWidths=[I_DATE, I_TIME, I_ROOM],
        rowHeights=[None, None, None, 8],
    )
    info_tbl.setStyle(TableStyle(_no_top([
        ("SPAN",          (0, 0), (-1,  0)),
        ("SPAN",          (0, 1), (-1,  1)),
        ("SPAN",          (0, 3), (-1,  3)),
        ("BACKGROUND",    (0, 3), (-1,  3), GRAY_LIGHT),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (-1,  2), "LEFT"),
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
    # ══════════════════════════════════════════════════════════════════════════
    # Everyone except a genuinely undetected/Absent student belongs on the
    # official sheet — Present, Late, Partial, and Excused all indicate the
    # student attended the class in one form or another.
    present  = [r for r in records if r.get("status") == "Present"]
    late     = [r for r in records if r.get("status") == "Late"]
    partial  = [r for r in records if r.get("status") == "Partial"]
    excused  = [r for r in records if r.get("status") == "Excused"]
    absent   = [r for r in records if r.get("status") == "Absent"]
    attended = present + late + partial + excused

    ROWS_PER_COL = 30
    slot = {}
    for idx, r in enumerate(attended):
        if idx < ROWS_PER_COL * 2:
            slot[idx] = r

    roster_rows = [[
        Paragraph("NAME",      bold9c),
        Paragraph("SIGNATURE", bold9c),
        Paragraph("NAME",      bold9c),
        Paragraph("SIGNATURE", bold9c),
    ]]

    for i in range(ROWS_PER_COL):
        left_r  = slot.get(i)
        right_r = slot.get(i + ROWS_PER_COL)

        if left_r:
            st      = left_r["status"]
            tag     = STATUS_TAG.get(st, "")
            col     = BLACK if st == "Present" else ORANGE
            l_nm    = Paragraph(f"{i+1}. {left_r['name']}{tag}",
                                ps(f"ln{i}", fontSize=9, fontName=TNR, textColor=col))
            l_sg    = _sig_cell(left_r.get("sig_path", ""), st, norm9c)
        else:
            l_nm = Paragraph(f"{i+1}.", ps(f"le{i}", fontSize=9, fontName=TNR))
            l_sg = Paragraph("", norm9)

        if right_r:
            st      = right_r["status"]
            tag     = STATUS_TAG.get(st, "")
            col     = BLACK if st == "Present" else ORANGE
            r_nm    = Paragraph(f"{i+1+ROWS_PER_COL}. {right_r['name']}{tag}",
                                ps(f"rn{i}", fontSize=9, fontName=TNR, textColor=col))
            r_sg    = _sig_cell(right_r.get("sig_path", ""), st, norm9c)
        else:
            r_nm = Paragraph(f"{i+1+ROWS_PER_COL}.", ps(f"re{i}", fontSize=9, fontName=TNR))
            r_sg = Paragraph("", norm9)

        roster_rows.append([l_nm, l_sg, r_nm, r_sg])

    roster_tbl = Table(
        roster_rows,
        colWidths=[R_NAME, R_SIG, R_NAME, R_SIG],
        repeatRows=1,
        rowHeights=[16] + [14] * ROWS_PER_COL,
    )
    roster_tbl.setStyle(TableStyle(_no_top([
        ("ALIGN",         (0, 0), (-1,  0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
    ])))
    story.append(roster_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # ABSENT SECTION
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
    buf.seek(0)
    print(f"[PDF] Generated in-memory: {filename}")
    return buf, filename