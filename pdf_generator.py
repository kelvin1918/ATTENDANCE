"""
pdf_generator.py — BSU Attendance Sheet Format
================================================
Matches BatStateU-REC-ATT-11 layout:
  Header:  University name, Reference No., Document Title
  Info:    Course Code & Title, Faculty, Date, Time, Venue
  Body:    Two-column numbered student list with Status + Signature
  Footer:  Summary counts + Faculty signature line
"""
import os, re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

PDF_DIR = "pdf"
os.makedirs(PDF_DIR, exist_ok=True)

ACCENT = colors.HexColor("#D32F2F")
LIGHT  = colors.HexColor("#FFEBEE")
WHITE  = colors.white
BLACK  = colors.black
GRAY   = colors.HexColor("#757575")
LGRAY  = colors.HexColor("#F5F5F5")


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


def generate_attendance_pdf(class_id, subject, section, room, date,
                             time_str="", faculty_name="Instructor",
                             records=None, session_time=""):
    if records is None:
        records = []

    filename = f"Log_{_safe(date)}_{_safe(session_time or 'session')}_{_safe(section)}.pdf"
    filepath  = os.path.join(PDF_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.2*cm,   bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    hdr_cell = S("hc", fontSize=7.5, fontName="Helvetica-Bold",
                 textColor=WHITE, alignment=TA_CENTER)
    body_cell = S("bc", fontSize=8,  fontName="Helvetica", textColor=BLACK)
    label_s   = S("lb", fontSize=8,  fontName="Helvetica-Bold", textColor=BLACK)
    value_s   = S("vl", fontSize=9,  fontName="Helvetica",      textColor=BLACK)
    foot_s    = S("ft", fontSize=7,  fontName="Helvetica",      textColor=GRAY, alignment=TA_CENTER)

    story = []

    # ── DOCUMENT HEADER ───────────────────────────────────────────────────────
    uni_s = S("uni", fontSize=9, fontName="Helvetica-Bold", alignment=TA_CENTER)
    doc_s = S("ds",  fontSize=10, fontName="Helvetica-Bold", textColor=ACCENT, alignment=TA_CENTER)
    ref_s = S("rs",  fontSize=7,  fontName="Helvetica", textColor=GRAY)

    ref_tbl = Table([
        [Paragraph("Reference No.:", ref_s),  Paragraph("BatStateU-REC-ATT-11", ref_s)],
        [Paragraph("Effectivity:",    ref_s),  Paragraph("January 3, 2017",       ref_s)],
        [Paragraph("Revision No.:",   ref_s),  Paragraph("00",                    ref_s)],
    ], colWidths=[2.4*cm, 2.8*cm])

    hdr_tbl = Table([[
        Paragraph("Batangas State University\nARASof-Nasugbu Campus", uni_s),
        Paragraph("ATTENDANCE SHEET\nStudent Class Attendance", doc_s),
        ref_tbl,
    ]], colWidths=[4*cm, 8.5*cm, 5.5*cm])
    hdr_tbl.setStyle(TableStyle([
        ("BOX",    (0,0),(-1,-1), 1,   BLACK),
        ("INNERGRID",(0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1), 6), ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 0.3*cm))

    # ── INFO BLOCK ────────────────────────────────────────────────────────────
    try:
        disp_date = datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        disp_date = date

    info = Table([
        [Paragraph("Course Code and Title:", label_s), Paragraph(subject, value_s),
         Paragraph("Section:", label_s), Paragraph(section, value_s)],
        [Paragraph("Assigned Faculty:", label_s), Paragraph(faculty_name.upper(), value_s),
         Paragraph("Date:", label_s), Paragraph(disp_date, value_s)],
        [Paragraph("Venue / Room:", label_s), Paragraph(room, value_s),
         Paragraph("Time:", label_s), Paragraph(time_str, value_s)],
    ], colWidths=[3.5*cm, 6*cm, 2.5*cm, 6*cm])
    info.setStyle(TableStyle([
        ("BOX",    (0,0),(-1,-1), 1,   BLACK),
        ("INNERGRID",(0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(info)
    story.append(Spacer(1, 0.3*cm))

    # ── SPLIT RECORDS ─────────────────────────────────────────────────────────
    present  = [r for r in records if r["status"] == "Present"]
    late     = [r for r in records if r["status"] == "Late"]
    absent   = [r for r in records if r["status"] == "Absent"]
    attended = present + late

    # ── TWO-COLUMN ATTENDANCE TABLE ───────────────────────────────────────────
    col_size  = max(30, (len(attended) + 1) // 2)
    left_rows = attended[:col_size]
    right_rows= attended[col_size:]
    while len(right_rows) < len(left_rows):
        right_rows.append(None)

    # Status colors
    def sc(s):
        return colors.HexColor("#388E3C") if s == "Present" else colors.HexColor("#E65100")

    att_data   = [[
        Paragraph("#",         hdr_cell), Paragraph("NAME",      hdr_cell),
        Paragraph("TIME IN",   hdr_cell), Paragraph("STATUS",    hdr_cell),
        Paragraph("SIGNATURE", hdr_cell),
        Paragraph("#",         hdr_cell), Paragraph("NAME",      hdr_cell),
        Paragraph("TIME IN",   hdr_cell), Paragraph("STATUS",    hdr_cell),
        Paragraph("SIGNATURE", hdr_cell),
    ]]
    row_styles = [
        ("BACKGROUND",    (0,0),(-1,0),  ACCENT),
        ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
        ("FONTSIZE",      (0,0),(-1,-1), 7.5),
        ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ("LINEAFTER",     (4,0),(4,-1),  1.5, BLACK),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 4), ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("ALIGN",         (0,0),(0,-1),  "CENTER"),
        ("ALIGN",         (5,0),(5,-1),  "CENTER"),
    ]

    for i, (lr, rr) in enumerate(zip(left_rows, right_rows), start=1):
        ri = len(att_data)
        row = []
        if lr:
            row += [str(i), lr["name"], _fmt_time(lr.get("timestamp","")), lr["status"], ""]
            row_styles += [("TEXTCOLOR",(3,ri),(3,ri), sc(lr["status"])),
                           ("FONTNAME", (3,ri),(3,ri), "Helvetica-Bold")]
        else:
            row += ["","","","",""]
        rn = i + col_size
        if rr:
            row += [str(rn), rr["name"], _fmt_time(rr.get("timestamp","")), rr["status"], ""]
            row_styles += [("TEXTCOLOR",(8,ri),(8,ri), sc(rr["status"])),
                           ("FONTNAME", (8,ri),(8,ri), "Helvetica-Bold")]
        else:
            row += ["","","","",""]
        att_data.append(row)

    if len(att_data) == 1:
        att_data.append(["","No students attended.","","","","","","","",""])

    att_tbl = Table(att_data,
                    colWidths=[0.7*cm,4.5*cm,1.8*cm,1.8*cm,2.5*cm,
                               0.7*cm,4.5*cm,1.8*cm,1.8*cm,2.5*cm],
                    repeatRows=1)
    att_tbl.setStyle(TableStyle(row_styles))
    story.append(Paragraph("Attendance Log",
        S("al", fontSize=9, fontName="Helvetica-Bold", textColor=ACCENT, spaceAfter=4)))
    story.append(att_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── ABSENT TABLE ──────────────────────────────────────────────────────────
    if absent:
        abs_data = [[Paragraph("#", hdr_cell), Paragraph("NAME", hdr_cell),
                     Paragraph("SR CODE", hdr_cell), Paragraph("REMARKS", hdr_cell)]]
        for i, r in enumerate(absent, 1):
            abs_data.append([str(i), r["name"], r.get("sr_code","") or "", "ABSENT"])
        abs_tbl = Table(abs_data, colWidths=[1*cm,7*cm,4*cm,6*cm], repeatRows=1)
        abs_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),  GRAY),
            ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
            ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
            ("FONTNAME",      (0,1),(-1,-1), "Helvetica"),
            ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ("ROWBACKGROUND", (0,1),(-1,-1), [WHITE, LGRAY]),
            ("TOPPADDING",    (0,0),(-1,-1), 4), ("BOTTOMPADDING",(0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ]))
        story.append(Paragraph("Absent Students",
            S("ab", fontSize=9, fontName="Helvetica-Bold", textColor=GRAY, spaceAfter=4)))
        story.append(abs_tbl)
        story.append(Spacer(1, 0.4*cm))

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    summary = Table([[
        Paragraph(f"Total: <b>{len(records)}</b>",   S("s1", fontSize=9, fontName="Helvetica")),
        Paragraph(f"Present: <b>{len(present)}</b>", S("s2", fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#388E3C"))),
        Paragraph(f"Late: <b>{len(late)}</b>",       S("s3", fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#E65100"))),
        Paragraph(f"Absent: <b>{len(absent)}</b>",   S("s4", fontSize=9, fontName="Helvetica", textColor=ACCENT)),
    ]], colWidths=[4*cm,4*cm,4*cm,6*cm])
    summary.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT),
        ("BOX",           (0,0),(-1,-1), 1,   ACCENT),
        ("INNERGRID",     (0,0),(-1,-1), 0.5, ACCENT),
        ("TOPPADDING",    (0,0),(-1,-1), 8), ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10), ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(summary)
    story.append(Spacer(1, 0.8*cm))

    # ── SIGNATURE ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Prepared by:", S("pb", fontSize=8, fontName="Helvetica", textColor=GRAY)))
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="40%", thickness=0.5, color=BLACK))
    story.append(Paragraph(f"<b>{faculty_name.upper()}</b>",
                            S("fn", fontSize=9, fontName="Helvetica-Bold")))
    story.append(Paragraph("Faculty / Instructor",
                            S("ft2", fontSize=7, fontName="Helvetica", textColor=GRAY)))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}  |  "
        f"Attendance Monitoring System  |  BatStateU-REC-ATT-11",
        foot_s))

    doc.build(story)
    print(f"[PDF] Saved: {filepath}")
    return filepath