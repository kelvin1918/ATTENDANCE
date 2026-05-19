"""
pdf_generator.py — BatStateU-REC-ATT-11 Revision 01
=====================================================
PDF layout mirrors the HTML print viewer exactly:
  - Times New Roman throughout
  - Column widths: Logo 14% | Ref 29% | Eff 32% | Rev 25%
  - Info rows full width, then Date 25% | Time 30% | Room 45%
  - Gray divider bar (D9D9D9) between info and roster
  - Roster: NAME 35% | SIG 15% | NAME 35% | SIG 15%
  - 30 rows per column, minimum 30 blank rows always shown
  - Signature image embedded; fallback = coloured status text
  - Generated in-memory (BytesIO) — no disk writes, safe on Render
"""

import os
import re
import urllib.request
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Image as RLImage, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

# ── COLOURS ──────────────────────────────────────────────────────────────────
BLACK      = colors.black
GRAY_DIV   = colors.HexColor("#D9D9D9")
GREEN_TEXT = colors.HexColor("#1B5E20")
ORANGE_TEXT= colors.HexColor("#E65100")

# ── FONTS ─────────────────────────────────────────────────────────────────────
TNR  = "Times-Roman"
TNRB = "Times-Bold"

# ── PAGE GEOMETRY — 8.5" × 13" Folio/F4 ─────────────────────────────────────
PAGE_W   = 8.5 * inch
PAGE_H   = 13.0 * inch
TOP_M    = 17.5 * mm
LEFT_M   = 25.4 * mm
BOTTOM_M = 6.3  * mm
RIGHT_M  = 25.4 * mm
USABLE   = PAGE_W - LEFT_M - RIGHT_M   # ~468 pt

# ── BORDER ────────────────────────────────────────────────────────────────────
B = 0.5   # 0.5 pt everywhere

# ── COLUMN WIDTHS (match HTML percentages exactly) ───────────────────────────
# Header row
H_LOGO = USABLE * 0.14
H_REF  = USABLE * 0.29
H_EFF  = USABLE * 0.32
H_REV  = USABLE * 0.25

# Info / date-time-room
I_DATE = USABLE * 0.25
I_TIME = USABLE * 0.30
I_ROOM = USABLE * 0.45

# Roster (matches HTML: 35 / 15 / 35 / 15 %)
R_NAME = USABLE * 0.35
R_SIG  = USABLE * 0.15

# Signature cell constraints (px → pt: 20px ≈ 15pt, 90% of R_SIG)
SIG_MAX_H = 15.0
SIG_MAX_W = R_SIG * 0.90

# Roster row height: HTML uses height:25px ≈ 18.75pt → use 19pt
ROW_H     = 19
HDR_ROW_H = 20   # header row slightly taller


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _safe(s):
    return re.sub(r'[\\/:*?"<>|,\s]', '_', str(s)).strip('_')

def _fmt_date(d):
    """'2026-05-19' → '5/19/2026'"""
    try:
        o = datetime.strptime(d, "%Y-%m-%d")
        return f"{o.month}/{o.day}/{o.year}"
    except Exception:
        return d

def _ps(name, ss, **kw):
    return ParagraphStyle(name, parent=ss["Normal"], **kw)

def _box(extra=None):
    """Full box border."""
    cmds = [("BOX", (0, 0), (-1, -1), B, BLACK),
            ("INNERGRID", (0, 0), (-1, -1), B, BLACK)]
    if extra:
        cmds.extend(extra)
    return cmds

def _no_top(extra=None):
    """Box without top — prevents double lines when stacking tables."""
    cmds = [
        ("LINEBEFORE", (0,  0), (0,  -1), B, BLACK),
        ("LINEAFTER",  (-1, 0), (-1, -1), B, BLACK),
        ("LINEBELOW",  (0, -1), (-1, -1), B, BLACK),
        ("INNERGRID",  (0,  0), (-1, -1), B, BLACK),
    ]
    if extra:
        cmds.extend(extra)
    return cmds


# ── SIGNATURE IMAGE CACHE + FETCHER ──────────────────────────────────────────

def _fetch_image_bytes(url):
    """Fetch Cloudinary URL → bytes. Cached per-request. Returns b'' on error."""
    cache = _fetch_image_bytes._cache
    if url in cache:
        return cache[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = r.read()
        cache[url] = data
        return data
    except Exception as e:
        print(f"[PDF] Signature fetch failed ({url}): {e}")
        cache[url] = b""
        return b""

_fetch_image_bytes._cache = {}


def _sig_cell(sig_path, status, style):
    """
    Return a ReportLab flowable for a SIGNATURE cell.
    Mirrors the HTML viewer: image → coloured status text fallback.
    """
    col_hex = "#1B5E20" if status == "Present" else "#E65100"

    if sig_path:
        img_data = None
        if sig_path.startswith("http://") or sig_path.startswith("https://"):
            raw = _fetch_image_bytes(sig_path)
            if raw:
                img_data = BytesIO(raw)
        elif os.path.isfile(sig_path):
            img_data = sig_path

        if img_data is not None:
            try:
                img = RLImage(img_data)
                w, h = img.imageWidth, img.imageHeight
                if w > 0 and h > 0:
                    scale = min(SIG_MAX_W / w, SIG_MAX_H / h, 1.0)
                    img.drawWidth  = w * scale
                    img.drawHeight = h * scale
                    img.hAlign = "CENTER"
                    return img
            except Exception as e:
                print(f"[PDF] Sig render error: {e}")

    # Fallback: coloured status text (bold, centered, 10pt — matches HTML span)
    return Paragraph(
        f'<font color="{col_hex}" size="10"><b>{status}</b></font>',
        style
    )


# ── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

def generate_attendance_pdf(class_id, subject, section, room, date,
                             time_str="", faculty_name="Instructor",
                             records=None, session_time=""):
    if records is None:
        records = []

    filename = f"Log_{_safe(date)}_{_safe(session_time or 'session')}_{_safe(section)}.pdf"
    buf = BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=LEFT_M, rightMargin=RIGHT_M,
        topMargin=TOP_M,   bottomMargin=BOTTOM_M,
    )

    ss = getSampleStyleSheet()

    def ps(name, **kw):
        return _ps(name, ss, **kw)

    # Shared styles
    norm10    = ps("n10",  fontSize=10, fontName=TNR)
    norm10c   = ps("n10c", fontSize=10, fontName=TNR,  alignment=TA_CENTER)
    norm11    = ps("n11",  fontSize=11, fontName=TNR)
    bold11c   = ps("b11c", fontSize=11, fontName=TNRB, alignment=TA_CENTER)
    bold14c   = ps("b14c", fontSize=14, fontName=TNRB, alignment=TA_CENTER)
    bold11    = ps("b11",  fontSize=11, fontName=TNRB)
    sig_style = ps("sig",  fontSize=10, fontName=TNRB, alignment=TA_CENTER)

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE 1 — HEADER (Logo | Ref No. | Effectivity | Revision)
    #            + "STUDENT CLASS ATTENDANCE" title row
    # Uses full BOX (first table on page).
    # Font size 10px in HTML → 10pt in PDF.
    # ══════════════════════════════════════════════════════════════════════════
    LOGO_PATH = "bsu_logo.png"
    if os.path.exists(LOGO_PATH):
        # HTML uses height:48px — convert to pt (1px ≈ 0.75pt → 36pt)
        logo_cell = RLImage(LOGO_PATH, width=36, height=36)
    else:
        logo_cell = Paragraph("Batangas State<br/>University",
                              ps("lc", fontSize=7, fontName=TNRB, alignment=TA_CENTER))

    hdr_data = [
        [
            logo_cell,
            Paragraph("Reference No.:<br/><b>BatStateU-REC-ATT-11</b>",
                      ps("hn1", fontSize=10, fontName=TNR, leading=14)),
            Paragraph("Effectivity Date: <b>May 18, 2022</b>",
                      ps("hn2", fontSize=10, fontName=TNR)),
            Paragraph("Revision No.: <b>01</b>",
                      ps("hn3", fontSize=10, fontName=TNR)),
        ],
        # Title row spans all 4 columns — 14pt bold uppercase, matches HTML
        [Paragraph("STUDENT CLASS ATTENDANCE", bold14c), "", "", ""],
    ]

    hdr_tbl = Table(hdr_data, colWidths=[H_LOGO, H_REF, H_EFF, H_REV])
    hdr_tbl.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), B, BLACK),
        ("INNERGRID",     (0, 0), (-1,  0), B, BLACK),
        ("LINEBELOW",     (0, 0), (-1,  0), B, BLACK),
        ("SPAN",          (0, 1), (-1,  1)),
        ("ALIGN",         (0, 0), (0,   0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1,  0), 6),
        ("BOTTOMPADDING", (0, 0), (-1,  0), 6),
        ("LEFTPADDING",   (1, 0), (-1,  0), 8),
        ("RIGHTPADDING",  (0, 0), (-1,  0), 4),
        ("TOPPADDING",    (0, 1), (-1,  1), 8),
        ("BOTTOMPADDING", (0, 1), (-1,  1), 8),
        ("LEFTPADDING",   (0, 1), (-1,  1), 4),
    ]))
    story.append(hdr_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE 2 — INFO BLOCK
    # Row 0: Course Code and Title (full width)
    # Row 1: Assigned Faculty      (full width)
    # Row 2: Date (25%) | Time (30%) | Room/Venue (45%)
    # Row 3: Gray divider bar (D9D9D9, 10px ≈ 7.5pt → use 8pt)
    # No top border (avoids double line with header).
    # Font size 11px in HTML → 11pt here.
    # ══════════════════════════════════════════════════════════════════════════
    disp_date = _fmt_date(date)

    info_data = [
        [Paragraph(f"Course Code and Title:&nbsp;&nbsp;<b>{subject}</b>&nbsp;({section})",
                   ps("cc", fontSize=11, fontName=TNR)), "", ""],
        [Paragraph(f"Assigned Faculty:&nbsp;&nbsp;<b>{faculty_name}</b>",
                   ps("af", fontSize=11, fontName=TNR)), "", ""],
        [
            Paragraph(f"Date:&nbsp;<b>{disp_date}</b>",
                      ps("dt", fontSize=11, fontName=TNR)),
            Paragraph(f"Time:&nbsp;<b>{time_str}</b>",
                      ps("tm", fontSize=11, fontName=TNR)),
            Paragraph(f"Room/Venue:&nbsp;<b>{room}</b>",
                      ps("rm", fontSize=11, fontName=TNR)),
        ],
        ["", "", ""],  # gray divider
    ]

    info_tbl = Table(
        info_data,
        colWidths=[I_DATE, I_TIME, I_ROOM],
        rowHeights=[None, None, None, 8],
    )
    info_tbl.setStyle(TableStyle(_no_top([
        ("SPAN",          (0, 0), (-1, 0)),
        ("SPAN",          (0, 1), (-1, 1)),
        ("SPAN",          (0, 3), (-1, 3)),
        ("BACKGROUND",    (0, 3), (-1, 3), GRAY_DIV),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (0, 0), (-1,  2), "LEFT"),
        ("TOPPADDING",    (0, 0), (-1,  2), 6),
        ("BOTTOMPADDING", (0, 0), (-1,  2), 6),
        ("LEFTPADDING",   (0, 0), (-1,  2), 10),
        ("RIGHTPADDING",  (0, 0), (-1,  2), 4),
        ("TOPPADDING",    (0, 3), (-1,  3), 0),
        ("BOTTOMPADDING", (0, 3), (-1,  3), 0),
        ("LEFTPADDING",   (0, 3), (-1,  3), 0),
        ("RIGHTPADDING",  (0, 3), (-1,  3), 0),
    ])))
    story.append(info_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE 3 — ATTENDANCE ROSTER
    # Mirrors HTML exactly:
    #   - Only Present + Late in roster (Absent excluded)
    #   - Left col: slots 0–29, Right col: slots 30–59
    #   - Minimum 30 blank rows always rendered
    #   - Row height: 25px in HTML → 19pt
    #   - Sig cell: image if available, else bold coloured status text
    # ══════════════════════════════════════════════════════════════════════════
    attended     = [r for r in records if r.get("status") in ("Present", "Late")]
    absent_list  = [r for r in records if r.get("status") == "Absent"]
    ROWS_PER_COL = 30

    # Header row
    roster_rows = [[
        Paragraph("<b>NAME</b>",      bold11c),
        Paragraph("<b>SIGNATURE</b>", bold11c),
        Paragraph("<b>NAME</b>",      bold11c),
        Paragraph("<b>SIGNATURE</b>", bold11c),
    ]]
    row_heights = [HDR_ROW_H]

    for i in range(ROWS_PER_COL):
        sL = attended[i]               if i < len(attended) else None
        sR = attended[i + ROWS_PER_COL] if i + ROWS_PER_COL < len(attended) else None

        numL = i + 1
        numR = i + ROWS_PER_COL + 1

        if sL:
            col_l = GREEN_TEXT if sL["status"] == "Present" else ORANGE_TEXT
            tag_l = " (Late)" if sL["status"] == "Late" else ""
            nm_l  = Paragraph(f"{numL}. {sL['name']}{tag_l}",
                               ps(f"nl{i}", fontSize=11, fontName=TNR, textColor=col_l))
            sg_l  = _sig_cell(sL.get("sig_path", ""), sL["status"], sig_style)
        else:
            nm_l = Paragraph(f"{numL}.", ps(f"el{i}", fontSize=11, fontName=TNR))
            sg_l = Paragraph("", norm11)

        if sR:
            col_r = GREEN_TEXT if sR["status"] == "Present" else ORANGE_TEXT
            tag_r = " (Late)" if sR["status"] == "Late" else ""
            nm_r  = Paragraph(f"{numR}. {sR['name']}{tag_r}",
                               ps(f"nr{i}", fontSize=11, fontName=TNR, textColor=col_r))
            sg_r  = _sig_cell(sR.get("sig_path", ""), sR["status"], sig_style)
        else:
            nm_r = Paragraph(f"{numR}.", ps(f"er{i}", fontSize=11, fontName=TNR))
            sg_r = Paragraph("", norm11)

        roster_rows.append([nm_l, sg_l, nm_r, sg_r])
        row_heights.append(ROW_H)

    roster_tbl = Table(
        roster_rows,
        colWidths=[R_NAME, R_SIG, R_NAME, R_SIG],
        repeatRows=1,
        rowHeights=row_heights,
    )
    roster_tbl.setStyle(TableStyle(_no_top([
        ("ALIGN",         (0, 0), (-1,  0), "CENTER"),
        ("ALIGN",         (1, 1), (1,  -1), "CENTER"),
        ("ALIGN",         (3, 1), (3,  -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (1, 0), (1,  -1), 3),
        ("LEFTPADDING",   (3, 0), (3,  -1), 3),
    ])))
    story.append(roster_tbl)

    # ══════════════════════════════════════════════════════════════════════════
    # ABSENT SECTION — listed below roster
    # ══════════════════════════════════════════════════════════════════════════
    if absent_list:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Absent Students:",
                                ps("abshdr", fontSize=10, fontName=TNRB, spaceAfter=3)))

        GRAY_LIGHT = colors.HexColor("#D9D9D9")
        abs_col_w  = [0.40 * inch, USABLE * 0.68, USABLE * 0.22]

        abs_rows = [[
            Paragraph("<b>#</b>",       norm10c),
            Paragraph("<b>NAME</b>",    bold11c),
            Paragraph("<b>SR CODE</b>", bold11c),
        ]]
        for idx, r in enumerate(absent_list, 1):
            abs_rows.append([
                Paragraph(str(idx), norm10c),
                Paragraph(r.get("name", ""),    ps(f"an{idx}", fontSize=11, fontName=TNR)),
                Paragraph(r.get("sr_code", ""), norm10c),
            ])

        abs_tbl = Table(abs_rows, colWidths=abs_col_w, repeatRows=1)
        abs_tbl.setStyle(TableStyle([
            ("BOX",           (0, 0), (-1, -1), B, BLACK),
            ("INNERGRID",     (0, 0), (-1, -1), B, BLACK),
            ("BACKGROUND",    (0, 0), (-1,  0), GRAY_LIGHT),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("ALIGN",         (0, 0), (0,  -1), "CENTER"),
            ("ALIGN",         (2, 0), (2,  -1), "CENTER"),
        ]))
        story.append(abs_tbl)

    # ── BUILD ─────────────────────────────────────────────────────────────────
    doc.build(story)
    buf.seek(0)
    print(f"[PDF] Generated in-memory: {filename}")
    return buf, filename