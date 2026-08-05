"""
pdf_generator.py — overlays attendance data onto the official
BatStateU-REC-ATT-11 template (assets/attendance_template.pdf) using
PyMuPDF, instead of rebuilding the form from scratch with ReportLab
flowables. The template file IS the page background, so borders,
margins, fonts and spacing are pixel-identical to the university's form
by construction — nothing to fight or drift out of alignment.

Layout coordinates below were measured directly off the template's own
vector borders/text (see get_drawings()/get_text("words") on the PDF),
not eyeballed.
"""

import os
import re
from io import BytesIO
from datetime import datetime

import fitz  # PyMuPDF
import urllib.request

# ── TEMPLATE ─────────────────────────────────────────────────────────────────
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "assets", "attendance_template.pdf")

FONT      = "Times-Roman"
FONT_BOLD = "Times-Bold"
BLACK     = (0, 0, 0)

# ── TEXT BASELINE CALIBRATION ────────────────────────────────────────────────
# PyMuPDF's insert_text(point, ...) does NOT place `point` on the visual
# baseline — empirically (verified with an isolated round-trip test: insert
# at y, read back the rendered bbox via get_text("words")) the actual ink
# lands ~0.281 * fontsize BELOW the given point. Every y-coordinate below is
# the *target* ink-bottom (matched to the template's own printed text), and
# _call_y() converts it to the point insert_text actually needs.
TEXT_Y_RATIO = 0.281


def _call_y(target_y1, fontsize):
    return target_y1 - TEXT_Y_RATIO * fontsize


# ── HEADER / INFO FIELD POSITIONS ────────────────────────────────────────────
# target_y1 = the y where inserted text's ink-bottom should land, matched to
# the template's own label text bottom on the same line.
# max_w is the remaining room to the cell's right border, used for
# shrink-to-fit when a value is too long for the printed line.
CC_TITLE = dict(x=148, target_y1=136.2, size=10, max_w=576.6 - 8 - 148)
FACULTY  = dict(x=123, target_y1=154.6, size=10, max_w=576.6 - 8 - 123)
DATE_F   = dict(x=70,  target_y1=173.2, size=10, max_w=193.4 - 8 - 70)
TIME_F   = dict(x=230, target_y1=173.2, size=10, max_w=294.3 - 8 - 230)
ROOM_F   = dict(x=367, target_y1=173.2, size=10, max_w=576.6 - 8 - 367)

# ── ROSTER GEOMETRY ──────────────────────────────────────────────────────────
# y-boundaries of the 30 roster row bands (row i spans ROW_DIVIDERS[i]..[i+1]).
ROW_DIVIDERS = [
    204.1, 222.7, 241.1, 259.6, 278.1, 296.7, 315.1, 333.7, 352.1, 370.7,
    389.1, 407.7, 426.1, 444.7, 463.1, 481.7, 500.1, 518.7, 537.1, 555.7,
    574.1, 592.7, 611.1, 629.8, 648.2, 666.8, 685.2, 703.8, 722.2, 740.8, 759.2,
]
ROWS_PER_COL  = 30
ROW_FONT_SIZE = 9

NAME1_X, NAME1_RIGHT = 58,    193.65
SIG1_X0,  SIG1_X1    = 193.65, 294.5
NAME2_X, NAME2_RIGHT = 316.5, 576.78
SIG2_X0,  SIG2_X1    = 458.75, 576.78
# (SIG2 column visually starts at 458.75, NAME2 column ends there)
NAME2_RIGHT = 458.75

NAME1_MAXW = NAME1_RIGHT - 4 - NAME1_X
NAME2_MAXW = NAME2_RIGHT - 4 - NAME2_X

SIG_MAX_H = 12  # legacy signature-image cap height, points

# ── HELPERS ──────────────────────────────────────────────────────────────────

def _safe(s):
    return re.sub(r'[\\/:*?"<>|,\s]', '_', str(s)).strip('_')


def _fmt_date(d):
    try:
        o = datetime.strptime(d, "%Y-%m-%d")
        return f"{o.month}/{o.day}/{o.year}"
    except Exception:
        return d


def _fit_size(text, fontname, size, max_w, floor=5.5):
    """Shrink fontsize until text fits max_w, down to floor."""
    s = size
    while s > floor and fitz.get_text_length(text, fontname=fontname, fontsize=s) > max_w:
        s -= 0.5
    return s


def _fit_text(text, fontname, size, max_w):
    """Shrink fontsize to fit max_w; if still too long at floor size,
    truncate with an ellipsis so it never bleeds into the next cell."""
    size = _fit_size(text, fontname, size, max_w)
    if fitz.get_text_length(text, fontname=fontname, fontsize=size) <= max_w:
        return text, size
    while text and fitz.get_text_length(text + "…", fontname=fontname, fontsize=size) > max_w:
        text = text[:-1]
    return text + "…", size


def _draw_field(page, spec, text, fontname=FONT):
    text = str(text or "").strip()
    if not text:
        return
    text, size = _fit_text(text, fontname, spec["size"], spec["max_w"])
    y = _call_y(spec["target_y1"], size)
    page.insert_text((spec["x"], y), text, fontname=fontname, fontsize=size, color=BLACK)


def _draw_name(page, x, target_y1, name, max_w):
    name = str(name or "").strip()
    if not name:
        return
    name, size = _fit_text(name, FONT, ROW_FONT_SIZE, max_w)
    y = _call_y(target_y1, size)
    page.insert_text((x, y), name, fontname=FONT, fontsize=size, color=BLACK)


def _insert_centered(page, cx, target_y1, text, fontname, size):
    w = fitz.get_text_length(text, fontname=fontname, fontsize=size)
    y = _call_y(target_y1, size)
    page.insert_text((cx - w / 2, y), text, fontname=fontname, fontsize=size, color=BLACK)


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


def _insert_sig_image(page, raw, x0, x1, row_top, row_bottom):
    try:
        from PIL import Image
        img = Image.open(BytesIO(raw))
        nat_w, nat_h = img.size
    except Exception as e:
        print(f"[PDF] Image render error: {e}")
        return
    if nat_w <= 0 or nat_h <= 0:
        return
    avail_w = (x1 - x0) - 6
    scale   = min(avail_w / nat_w, SIG_MAX_H / nat_h, 1.0)
    w, h    = nat_w * scale, nat_h * scale
    cx      = (x0 + x1) / 2
    cy      = (row_top + row_bottom) / 2
    rect    = fitz.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    try:
        page.insert_image(rect, stream=raw, keep_proportion=True)
    except Exception as e:
        print(f"[PDF] Image render error: {e}")


def _draw_sig(page, x0, x1, row_top, row_bottom, rec):
    """SIGNED counts as attended (Present/Late/Excused) — the mark represents
    physical attendance, same as a manual paper sheet. Legacy records that
    still carry a stored signature image are rendered as an image instead."""
    status    = rec.get("status")
    sig_path  = rec.get("sig_path", "")
    target_y1 = row_bottom - 3.5

    if sig_path == "SIGNED":
        if status in ("Present", "Late", "Excused"):
            _insert_centered(page, (x0 + x1) / 2, target_y1, "SIGNED", FONT, ROW_FONT_SIZE)
        return

    if sig_path:
        raw = None
        if sig_path.startswith("http://") or sig_path.startswith("https://"):
            raw = _fetch_image_bytes(sig_path)
        elif os.path.isfile(sig_path):
            with open(sig_path, "rb") as f:
                raw = f.read()
        if raw:
            _insert_sig_image(page, raw, x0, x1, row_top, row_bottom)


# ── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

def generate_attendance_pdf(class_id, subject, section, room, date,
                             time_str="", faculty_name="Instructor",
                             records=None, session_time=""):
    if records is None:
        records = []

    filename = f"Log_{_safe(date)}_{_safe(session_time or 'session')}_{_safe(section)}.pdf"

    doc  = fitz.open(TEMPLATE_PATH)
    page = doc[0]

    _draw_field(page, CC_TITLE, f"{subject}  ({section})")
    _draw_field(page, FACULTY,  faculty_name)
    _draw_field(page, DATE_F,   _fmt_date(date))
    _draw_field(page, TIME_F,   time_str)
    _draw_field(page, ROOM_F,   room)

    # Present, Late, and Excused all indicate the student attended the class
    # in some form and belong on the official sheet. Partial is treated the
    # same as Absent here — falling below the attendance-duration threshold
    # means they didn't attend enough to count, so neither appears anywhere
    # on the sheet, matching the on-screen preview/print reference.
    present  = [r for r in records if r.get("status") == "Present"]
    late     = [r for r in records if r.get("status") == "Late"]
    excused  = [r for r in records if r.get("status") == "Excused"]
    attended = present + late + excused

    for i in range(ROWS_PER_COL):
        row_top    = ROW_DIVIDERS[i]
        row_bottom = ROW_DIVIDERS[i + 1]
        target_y1  = row_bottom - 3.5

        left_r  = attended[i]                if i < len(attended) else None
        right_r = attended[i + ROWS_PER_COL] if i + ROWS_PER_COL < len(attended) else None

        if left_r:
            _draw_name(page, NAME1_X, target_y1, left_r["name"], NAME1_MAXW)
            _draw_sig(page, SIG1_X0, SIG1_X1, row_top, row_bottom, left_r)
        if right_r:
            _draw_name(page, NAME2_X, target_y1, right_r["name"], NAME2_MAXW)
            _draw_sig(page, SIG2_X0, SIG2_X1, row_top, row_bottom, right_r)

    # No appendix section — the official BatStateU-REC-ATT-11 sheet (and the
    # on-screen preview/print it must match) lists attended students only,
    # capped at the form's 60 printed slots. Absent/Partial students don't
    # appear anywhere on the form.

    buf = BytesIO()
    doc.save(buf)
    doc.close()
    buf.seek(0)
    print(f"[PDF] Generated in-memory: {filename}")
    return buf, filename
