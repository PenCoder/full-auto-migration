"""Generates docs/presentation/Migration_Wizard_Praktikum_Presentation.pptx.

One-shot content generator, not part of the app itself. Re-run after editing
this file to regenerate the deck. Screenshots in docs/presentation/assets/
are real renders of the actual app/report (see git history for how they
were captured) — keep them in sync if the UI changes meaningfully.

Built on the official school template (Template-L3.pptx, Uni Würzburg /
Lehrstuhl für Kommunikationsnetze) — every slide uses that template's own
slide layouts so the logo, footer, and slide numbers in the master are
inherited automatically. Colors are the template's own theme accents, not
an invented palette.
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION

ASSETS = Path(__file__).resolve().parent.parent / "docs" / "presentation" / "assets"
OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "presentation" / "Migration_Wizard_Praktikum_Presentation.pptx"
TEMPLATE_PATH = Path(r"E:\School Stuff\Seminars\Mobile Computing\Presentation\Template-L3.pptx")

# Official theme accents (ppt/theme/theme1.xml in the school template) — not invented.
NAVY = RGBColor(0x1A, 0x1A, 0x1A)
BLUE = RGBColor(0x06, 0x3D, 0x79)        # accent1
DARK_BLUE = RGBColor(0x06, 0x3D, 0x79)   # accent1
LIGHT_BLUE_BG = RGBColor(0xDC, 0xE6, 0xF0)
GREEN = RGBColor(0x00, 0x84, 0x39)       # accent3
GREEN_BG = RGBColor(0xE2, 0xF1, 0xE8)
AMBER = RGBColor(0xB9, 0x70, 0x00)       # accent4
AMBER_BG = RGBColor(0xF7, 0xEC, 0xDC)
RED = RGBColor(0xB9, 0x27, 0x00)         # accent2
RED_BG = RGBColor(0xF7, 0xE1, 0xDC)
GREY = RGBColor(0x3F, 0x3F, 0x3F)        # accent6
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BG = WHITE
LINE = RGBColor(0xD8, 0xDA, 0xDC)        # accent5

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# Layout indices in Template-L3.pptx's slide master.
LAYOUT_TITLE = 0   # 'Titelfolie' — has CENTER_TITLE (idx 0) + SUBTITLE (idx 1) placeholders
LAYOUT_BLANK = 7   # 'Leer' — blank canvas, inherits the master's logo/footer/slide-number chrome


def new_presentation() -> Presentation:
    from pptx.oxml.ns import qn

    prs = Presentation(str(TEMPLATE_PATH))
    # The template ships with 2 sample slides (empty placeholders) — drop both,
    # including their underlying parts (not just the slide-list reference), so
    # add_slide() below doesn't collide with now-orphaned slide1.xml/slide2.xml
    # part names when re-saving.
    xml_slides = prs.slides._sldIdLst
    for sld in list(xml_slides):
        rId = sld.get(qn("r:id"))
        prs.part.drop_rel(rId)
        xml_slides.remove(sld)

    # The master's footer has a literal "Name" text box (not a real
    # placeholder) meant for the presenter to fill in by hand — set it once
    # here so it applies to every slide instead of showing "Name" literally.
    for shape in prs.slide_masters[0].shapes:
        if shape.has_text_frame and shape.text_frame.text.strip() == "Name":
            # Set the existing run's text directly rather than text_frame.text —
            # the latter clears all runs and re-creates one with default
            # formatting, losing the original (smaller, unbold) 10pt styling.
            shape.text_frame.paragraphs[0].runs[0].text = "Japhet Kofi Appau Arthur"

    return prs


def title_slide(prs, title, subtitle):
    """Uses the template's own 'Titelfolie' layout — real banner, logo, watermark."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE])
    slide.placeholders[0].text = title
    slide.placeholders[1].text = subtitle
    return slide


LAYOUT_SECTION = 2  # 'Abschnittsüberschrift' — section-header layout (unused; kept for reference)

SECTION_ORDER = ["Motivation", "Idea", "Method", "Evidence", "Critique", "Takeaway"]


def section_divider(prs, section_name, description):
    """A section-break slide with a 6-step progress tracker (Motivation → Idea →
    Method → Evidence → Critique → Takeaway) so the audience always knows where
    they are in the talk. Built on the 'Leer' blank layout rather than the
    template's own section-header layout, so it stays visually consistent
    (white background, same accent blue) with every content slide.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_BLANK])
    add_text(slide, Inches(0.9), Inches(2.7), Inches(11.5), Inches(0.45), description, size=15, italic=True, color=GREY)
    add_text(slide, Inches(0.9), Inches(3.1), Inches(11.5), Inches(1.1), section_name.upper(), size=48, bold=True, color=BLUE)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(4.15), Inches(1.3), Pt(4))
    line.fill.solid()
    line.fill.fore_color.rgb = BLUE
    line.line.fill.background()
    line.shadow.inherit = False

    n = len(SECTION_ORDER)
    slot = Inches(11.5) / n
    idx_current = SECTION_ORDER.index(section_name)
    for i, name in enumerate(SECTION_ORDER):
        cx = Inches(0.9) + slot * i + slot / 2
        active = i <= idx_current
        d = Inches(0.22)
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, cx - d / 2, Inches(5.0), d, d)
        dot.fill.solid()
        dot.fill.fore_color.rgb = BLUE if active else WHITE
        dot.line.color.rgb = BLUE if active else LINE
        dot.line.width = Pt(1.25)
        dot.shadow.inherit = False
        add_text(slide, cx - slot / 2, Inches(5.35), slot, Inches(0.35), name,
                  size=11, bold=(name == section_name), color=BLUE if name == section_name else GREY,
                  align=PP_ALIGN.CENTER)
    return slide


def blank_slide(prs, fill=None):
    """A content slide on the template's 'Leer' layout — inherits the master's
    logo + slide-number footer automatically; no custom background needed.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_BLANK])
    return slide


def _send_to_back(slide, shape):
    spTree = slide.shapes._spTree
    spTree.remove(shape._element)
    spTree.insert(2, shape._element)


def add_text(slide, left, top, width, height, text, size=18, bold=False, color=NAVY,
             align=PP_ALIGN.LEFT, font="Segoe UI", anchor=None, italic=False, line_spacing=None):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    if anchor:
        tf.vertical_anchor = anchor
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line_spacing:
            p.line_spacing = line_spacing
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
        run.font.name = font
    return box


def add_card(slide, left, top, width, height, fill=WHITE, line_color=LINE, radius=True, shadow=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    card = slide.shapes.add_shape(shape_type, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = fill
    card.line.color.rgb = line_color
    card.line.width = Pt(1)
    card.shadow.inherit = shadow
    if radius:
        try:
            card.adjustments[0] = 0.07
        except Exception:
            pass
    return card


def add_pill(slide, left, top, width, height, text, fg, bg, size=12):
    pill = add_card(slide, left, top, width, height, fill=bg, line_color=bg)
    try:
        pill.adjustments[0] = 0.5
    except Exception:
        pass
    tf = pill.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = fg
    run.font.name = "Segoe UI"
    return pill


def add_icon_circle(slide, cx, cy, diameter, glyph, fg=WHITE, bg=BLUE, size=28):
    left = cx - diameter / 2
    top = cy - diameter / 2
    circ = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top, diameter, diameter)
    circ.fill.solid()
    circ.fill.fore_color.rgb = bg
    circ.line.fill.background()
    circ.shadow.inherit = False
    tf = circ.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = glyph
    run.font.size = Pt(size)
    run.font.color.rgb = fg
    run.font.bold = True
    return circ


def add_arrow(slide, x1, y1, x2, y2, color=BLUE, weight=2.25):
    """A simple horizontal right-pointing arrow autoshape between two points.

    A connector + manually-injected <a:tailEnd> XML looked right in
    python-pptx (non-validating) but produced OOXML PowerPoint itself
    refused to open — child-element ordering in <a:ln> is schema-strict.
    A plain autoshape avoids hand-written XML entirely.
    """
    width = abs(x2 - x1)
    height = Pt(14)
    top = min(y1, y2) - height / 2
    left = min(x1, x2)
    arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, left, top, width, height)
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = color
    arrow.line.fill.background()
    arrow.shadow.inherit = False
    return arrow


def add_down_arrow(slide, cx, y1, y2, color=BLUE, width=Pt(14)):
    """A vertical downward arrow autoshape, centered on cx, from y1 to y2."""
    height = abs(y2 - y1)
    left = cx - width / 2
    arrow = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, left, min(y1, y2), width, height)
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = color
    arrow.line.fill.background()
    arrow.shadow.inherit = False
    return arrow


def add_header(slide, kicker, title, kicker_color=BLUE):
    add_text(slide, Inches(0.6), Inches(0.3), Inches(11), Inches(0.35), kicker.upper(),
              size=12, bold=True, color=kicker_color)
    add_text(slide, Inches(0.6), Inches(0.62), Inches(12.0), Inches(0.75), title,
              size=27, bold=True, color=NAVY)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.32), Inches(1.1), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = BLUE
    line.line.fill.background()
    line.shadow.inherit = False


def add_picture_framed(slide, img_path, left, top, max_w, max_h, caption=None, border=True):
    from PIL import Image
    with Image.open(img_path) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w, h = int(iw * scale), int(ih * scale)
    frame_pad = Pt(4)
    if border:
        frame = add_card(slide, left - Pt(6), top - Pt(6), w + Pt(12), h + Pt(12), fill=WHITE, line_color=LINE, radius=True, shadow=True)
    pic = slide.shapes.add_picture(str(img_path), left, top, width=w, height=h)
    if caption:
        add_text(slide, left, top + h + Pt(8), max_w, Inches(0.4), caption, size=12.5, italic=True, color=GREY,
                  align=PP_ALIGN.CENTER)
    return pic, w, h


def icon_label_row(slide, items, top, total_width=Inches(11.5), left=Inches(0.9), circle_d=Inches(0.85),
                    icon_size=30, label_size=14, sub_size=11.5, fg=WHITE, bg=BLUE):
    n = len(items)
    slot = total_width / n
    for i, (glyph, label, sub) in enumerate(items):
        cx = left + slot * i + slot / 2
        add_icon_circle(slide, cx, top + circle_d / 2, circle_d, glyph, fg=fg, bg=bg, size=icon_size)
        add_text(slide, cx - slot / 2 + Inches(0.1), top + circle_d + Pt(8), slot - Inches(0.2), Inches(0.4),
                  label, size=label_size, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        if sub:
            add_text(slide, cx - slot / 2 + Inches(0.1), top + circle_d + Pt(8) + Inches(0.42), slot - Inches(0.2), Inches(0.7),
                      sub, size=sub_size, color=GREY, align=PP_ALIGN.CENTER, line_spacing=1.15)


def set_table_style(table, header_bg=DARK_BLUE, header_fg=WHITE, body_size=13, header_size=13):
    for r_idx, row in enumerate(table.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.margin_left = Pt(8)
            cell.margin_right = Pt(8)
            cell.margin_top = Pt(4)
            cell.margin_bottom = Pt(4)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_bg if r_idx == 0 else (WHITE if r_idx % 2 else RGBColor(0xEE, 0xF7, 0xFB))
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.CENTER if (r_idx == 0 or c_idx > 0) else PP_ALIGN.LEFT
                for run in p.runs:
                    run.font.size = Pt(header_size if r_idx == 0 else body_size)
                    run.font.color.rgb = header_fg if r_idx == 0 else NAVY
                    run.font.bold = r_idx == 0
                    run.font.name = "Segoe UI"


def fill_table(slide, left, top, width, height, rows_data):
    rows, cols = len(rows_data), len(rows_data[0])
    table = slide.shapes.add_table(rows, cols, left, top, width, height).table
    for r, row_vals in enumerate(rows_data):
        for c, val in enumerate(row_vals):
            table.cell(r, c).text = str(val)
    set_table_style(table)
    return table


def add_bar_chart(slide, left, top, width, height, categories, series_name, values,
                   bar_color=BLUE, title=None, horizontal=False):
    """A real native PowerPoint chart (editable in PowerPoint), not a picture."""
    chart_data = CategoryChartData()
    chart_data.categories = categories
    chart_data.add_series(series_name, values)
    chart_type = XL_CHART_TYPE.BAR_CLUSTERED if horizontal else XL_CHART_TYPE.COLUMN_CLUSTERED
    graphic_frame = slide.shapes.add_chart(chart_type, left, top, width, height, chart_data)
    chart = graphic_frame.chart
    chart.has_legend = False
    plot = chart.plots[0]
    plot.has_data_labels = True
    plot.data_labels.font.size = Pt(13)
    plot.data_labels.font.bold = True
    plot.data_labels.font.color.rgb = NAVY
    if not horizontal:
        plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    series = plot.series[0]
    series.format.fill.solid()
    series.format.fill.fore_color.rgb = bar_color
    series.format.line.fill.background()
    chart.category_axis.format.line.color.rgb = LINE
    chart.category_axis.tick_labels.font.size = Pt(13)
    chart.category_axis.tick_labels.font.color.rgb = NAVY
    chart.value_axis.visible = False
    chart.value_axis.has_major_gridlines = False
    if title:
        chart.has_title = True
        chart.chart_title.text_frame.text = title
        chart.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
        chart.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
    else:
        chart.has_title = False
    return chart


# ─────────────────────────────────────────────────────────────────────────────

def build() -> Presentation:
    prs = new_presentation()

    # ── 1. Title ─────────────────────────────────────────────────────────────
    title_slide(
        prs,
        "Migration Wizard — Windows 11 → Linux Mint, automated",
        "Japhet Kofi Appau Arthur  ·  Mobile Computing Seminar · Praktikum",
    )

    # ── SECTION: Motivation ──────────────────────────────────────────────────────
    section_divider(prs, "Motivation", "Why a migration tool is a digital sovereignty question, not just a convenience one")

    # ── The premise, stated big (one idea, oversized pull-quote) ───────────────
    s = blank_slide(prs)
    add_text(s, Inches(0.6), Inches(0.3), Inches(11), Inches(0.35), "MOTIVATION", size=12, bold=True, color=BLUE)
    add_text(s, Inches(0.9), Inches(1.6), Inches(11.5), Inches(1.8),
              "“Meaningful control over digital infrastructure, data flows, and computational processes.”",
              size=32, italic=True, color=GREY, line_spacing=1.15)
    add_text(s, Inches(0.9), Inches(3.45), Inches(11.5), Inches(0.4), "— Floridi (2020); Pohle & Thiel (2020)", size=14, color=GREY)
    add_text(s, Inches(0.9), Inches(4.6), Inches(11.5), Inches(1.4),
              "Windows 11 cannot be fully audited or constrained — this project asks whether a migration tool can close that gap.",
              size=26, bold=True, color=DARK_BLUE, line_spacing=1.15)

    # ── Sovereignty: measured, not claimed ──────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Motivation", "Sovereignty, measured — not claimed")
    add_text(s, Inches(0.8), Inches(1.55), Inches(11.7), Inches(0.4),
              "“Meaningful control over digital infrastructure, data flows, and computational processes” — Floridi (2020); Pohle & Thiel (2020)",
              size=13, italic=True, color=GREY)
    add_bar_chart(
        s, Inches(0.6), Inches(2.05), Inches(6.0), Inches(3.9),
        categories=["Rate open-source\ncritical", "Cite reducing\nUS-vendor dep.", "Still run\nWindows (EU)"],
        series_name="%", values=[63.2, 47.4, 67.75], bar_color=DARK_BLUE,
        title="The preference-behaviour gap (Wire/StatCounter 2025)",
    )
    add_bar_chart(
        s, Inches(6.8), Inches(2.05), Inches(6.0), Inches(3.9),
        categories=["Repology\n(opt-in)", "Telemetry", "Ads/\ntracking", "Remote\nanalytics"],
        series_name="Outbound calls", values=[2, 0, 0, 0], bar_color=GREEN,
        title="This codebase's network calls — counted, not claimed",
    )
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.2), Inches(0.05), Inches(0.6))
    rule.fill.solid(); rule.fill.fore_color.rgb = GREEN; rule.line.fill.background(); rule.shadow.inherit = False
    add_text(s, Inches(1.05), Inches(6.3), Inches(11.4), Inches(0.55),
              "sovereignty_score = integrity_score + openness_bonus  —  every restore reports one", size=15, bold=True, color=GREEN)

    # ── SECTION: Idea ─────────────────────────────────────────────────────────────
    section_divider(prs, "Idea", "Extend an existing semi-automated tool into one with measured automation, not just more of it")

    # ── Building on prior work ──────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Idea", "Extending a term paper into a working tool")
    add_card(s, Inches(0.8), Inches(1.85), Inches(11.7), Inches(1.5), fill=WHITE)
    add_text(s, Inches(1.1), Inches(2.0), Inches(11.1), Inches(0.5), "TERM PAPER", size=12.5, bold=True, color=BLUE)
    add_text(s, Inches(1.1), Inches(2.35), Inches(11.1), Inches(0.55),
              "“Digital Sovereignty Through Semi-Automated Migration from Windows to Linux”", size=18, bold=True, color=NAVY)
    add_text(s, Inches(1.1), Inches(2.92), Inches(11.1), Inches(0.4),
              "Japhet Arthur — Julius-Maximilians-Universität Würzburg, Lehrstuhl für Kommunikationsnetze", size=13.5, italic=True, color=GREY)
    add_text(s, Inches(0.8), Inches(3.65), Inches(11.7), Inches(0.6), "RESEARCH QUESTION IT ASKED", size=13, bold=True, color=DARK_BLUE)
    add_text(s, Inches(0.8), Inches(4.0), Inches(11.7), Inches(0.85),
              "How can semi-automated migration frameworks reduce technical barriers to OS-level\nsovereignty restoration while maintaining user control, data integrity, and workflow continuity?",
              size=16, color=NAVY, line_spacing=1.25)
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(5.1), Inches(0.05), Inches(1.65))
    rule.fill.solid(); rule.fill.fore_color.rgb = AMBER; rule.line.fill.background(); rule.shadow.inherit = False
    add_text(s, Inches(1.1), Inches(5.1), Inches(11.3), Inches(0.4), "WHAT IT BUILT — AND STATED AS LIMITATIONS", size=13, bold=True, color=AMBER)
    add_text(s, Inches(1.1), Inches(5.45), Inches(11.3), Inches(0.4),
              "A working 5-phase pipeline (Assess → Review → Prepare → Migrate → Verify).",
              size=14, color=GREY)
    add_text(s, Inches(1.1), Inches(5.9), Inches(11.3), Inches(0.8),
              "“…heuristic matching… not guaranteeing feature parity.”",
              size=21, italic=True, bold=True, color=NAVY, line_spacing=1.1)

    # ── The proof of concept, inspected directly ────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Idea", "The proof of concept this project actually started from")
    add_text(s, Inches(0.8), Inches(1.8), Inches(11.7), Inches(0.4),
              "github.com/PenCoder/semi-auto-migration — cloned and inspected directly, not paraphrased from the term paper",
              size=13, italic=True, color=GREY)
    items = [
        ("\U0001F5A5", "Tkinter GUI", "no Qt, no CLI parity\nclaim made"),
        ("\U0001F4CB", "25 mappings", "substring match\nonly, 1 stage"),
        ("\U0001F9EA", "0 tests", "no automated\nregression coverage"),
        ("\U0001F427", "Linux-only", "packaging; one\n22.5MB binary"),
    ]
    icon_label_row(s, items, top=Inches(2.4), circle_d=Inches(1.0), icon_size=26, label_size=15, sub_size=12.5, bg=AMBER)
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(4.75), Inches(0.05), Inches(1.3))
    rule.fill.solid(); rule.fill.fore_color.rgb = AMBER; rule.line.fill.background(); rule.shadow.inherit = False
    add_text(s, Inches(1.05), Inches(4.75), Inches(11.4), Inches(0.4), "INHERITED DEFECT, FOUND AND FIXED THIS SESSION", size=12.5, bold=True, color=AMBER)
    add_text(s, Inches(1.05), Inches(5.1), Inches(11.4), Inches(0.8),
              "The proof of concept's apt-get install is one atomic batch call — no per-package fallback, no timeout,\nfailures silently logged and ignored. Same defect existed here until this session's fix.",
              size=13.5, color=NAVY, line_spacing=1.2)

    # ── Three modes (funnel: decreasing automation, increasing control) ────────
    s = blank_slide(prs)
    add_header(s, "Idea", "Same pipeline, three levels of control")
    bands = [
        ("Guided", GREEN, "Zero decisions after mode pick", 6.5),
        ("Balanced", DARK_BLUE, "+ file type selection", 4.7),
        ("Expert", AMBER, "+ overrides + online verification", 2.9),
    ]
    cx = Inches(4.3)
    y = Inches(2.0)
    band_h = Inches(1.15)
    gap = Inches(0.12)
    for label, color, sub, w_in in bands:
        w = Inches(w_in)
        shp = s.shapes.add_shape(MSO_SHAPE.TRAPEZOID, cx - w / 2, y, w, band_h)
        shp.fill.solid(); shp.fill.fore_color.rgb = color; shp.line.fill.background(); shp.shadow.inherit = False
        tf = shp.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = label
        run.font.size = Pt(17)
        run.font.bold = True
        run.font.color.rgb = WHITE
        add_text(s, Inches(7.3), y + Inches(0.32), Inches(5.3), Inches(0.55), sub, size=13.5, color=NAVY)
        y += band_h + gap
    add_text(s, Inches(0.9), Inches(5.85), Inches(11.5), Inches(0.4),
              "Decreasing automation, increasing manual control, top to bottom.", size=13, italic=True, color=GREY)
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(6.35), Inches(0.05), Inches(0.4))
    rule.fill.solid(); rule.fill.fore_color.rgb = AMBER; rule.line.fill.background(); rule.shadow.inherit = False
    add_text(s, Inches(1.15), Inches(6.35), Inches(11.2), Inches(0.4),
              "Only Expert mode touches the network — only to verify a package already chosen, never to find it.",
              size=13, color=NAVY)

    # ── SECTION: Method ───────────────────────────────────────────────────────────
    section_divider(prs, "Method", "How automation was built, measured, and managed as a project")

    # ── 4. Approach + Architecture ──────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Method", "Two machines, four clean layers")
    rule1 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.9), Inches(0.05), Inches(1.0))
    rule1.fill.solid(); rule1.fill.fore_color.rgb = GREEN; rule1.line.fill.background(); rule1.shadow.inherit = False
    add_text(s, Inches(0.85), Inches(1.9), Inches(5.1), Inches(0.4), "1 — Prepare (Windows)", size=15, bold=True, color=NAVY)
    add_text(s, Inches(0.85), Inches(2.35), Inches(5.1), Inches(0.55), "Scan → map apps → pack a bundle", size=13.5, color=GREY)
    rule2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.6), Inches(1.9), Inches(0.05), Inches(1.0))
    rule2.fill.solid(); rule2.fill.fore_color.rgb = DARK_BLUE; rule2.line.fill.background(); rule2.shadow.inherit = False
    add_text(s, Inches(6.85), Inches(1.9), Inches(5.5), Inches(0.4), "2 — Restore (Linux Mint)", size=15, bold=True, color=NAVY)
    add_text(s, Inches(6.85), Inches(2.35), Inches(5.5), Inches(0.55), "Unzip → restore → verify → report", size=13.5, color=GREY)
    layers = [("inventory/", GREEN_BG, GREEN), ("analysis/", LIGHT_BLUE_BG, DARK_BLUE),
              ("services/", AMBER_BG, AMBER), ("qt_ui/ + cli", LIGHT_BLUE_BG, DARK_BLUE)]
    x = Inches(0.7)
    w = Inches(2.85)
    for i, (name, bg, fg) in enumerate(layers):
        add_card(s, x, Inches(3.7), w, Inches(1.1), fill=bg, line_color=bg)
        add_text(s, x, Inches(4.05), w, Inches(0.4), name, size=15, bold=True, color=fg, align=PP_ALIGN.CENTER)
        if i < len(layers) - 1:
            add_arrow(s, x + w, Inches(4.25), x + w + Inches(0.25), Inches(4.25), color=BLUE)
        x += w + Inches(0.25)
    add_card(s, Inches(1.4), Inches(5.15), Inches(10.5), Inches(1.6), fill=WHITE)
    add_text(s, Inches(1.7), Inches(5.35), Inches(9.9), Inches(0.4), "17,467 LOC (src) · 3,595 LOC (tests) · 89 files · MIT licensed", size=14, bold=True, color=DARK_BLUE)
    add_text(s, Inches(1.7), Inches(5.78), Inches(9.9), Inches(0.85),
              "Pages ↔ Controllers ↔ Services — Qt window only wires up controllers; CLI calls the\nsame services directly. Iterative work packages (WP1–WP7) plus a 6-day risk buffer before this presentation.",
              size=13, color=GREY, line_spacing=1.2)

    # ── Mode policy: one shared decision, two call paths ───────────────────────
    s = blank_slide(prs)
    add_header(s, "Method", "One shared decision module, two call paths")
    col_w = Inches(5.65)
    col_gap = Inches(0.3)
    left_x = Inches(0.6)
    right_x = left_x + col_w + col_gap
    add_card(s, left_x, Inches(1.6), col_w, Inches(0.5), fill=LIGHT_BLUE_BG, line_color=LIGHT_BLUE_BG)
    add_text(s, left_x, Inches(1.72), col_w, Inches(0.3), "Qt Wizard", size=14, bold=True, color=DARK_BLUE, align=PP_ALIGN.CENTER)
    add_card(s, right_x, Inches(1.6), col_w, Inches(0.5), fill=LIGHT_BLUE_BG, line_color=LIGHT_BLUE_BG)
    add_text(s, right_x, Inches(1.72), col_w, Inches(0.3), "CLI — python -m src.cli scan", size=14, bold=True, color=DARK_BLUE, align=PP_ALIGN.CENTER)
    add_card(s, left_x, Inches(2.25), col_w, Inches(0.5), fill=WHITE, line_color=LINE)
    add_text(s, left_x, Inches(2.37), col_w, Inches(0.3), "OperationsController / AutomationCoordinator", size=12, color=NAVY, align=PP_ALIGN.CENTER)
    add_card(s, right_x, Inches(2.25), col_w, Inches(0.5), fill=WHITE, line_color=LINE)
    add_text(s, right_x, Inches(2.37), col_w, Inches(0.3), "scan_command()", size=12, color=NAVY, align=PP_ALIGN.CENTER)
    add_down_arrow(s, left_x + col_w / 2, Inches(2.78), Inches(3.18))
    add_down_arrow(s, right_x + col_w / 2, Inches(2.78), Inches(3.18))
    add_card(s, left_x, Inches(3.22), col_w * 2 + col_gap, Inches(1.45), fill=AMBER_BG, line_color=AMBER_BG)
    add_text(s, left_x + Inches(0.3), Inches(3.32), col_w * 2, Inches(0.35), "src/orchestration/mode_policy.py", size=14, bold=True, color=AMBER)
    fns = [
        "should_run_analysis(mode)",
        "should_run_file_recommendations(mode)",
        "resolve_app_recommendation_strategy(mode)",
    ]
    for i, fn in enumerate(fns):
        add_text(s, left_x + Inches(0.5), Inches(3.7) + Inches(0.32) * i, col_w * 2, Inches(0.32), "•  " + fn, size=12.5, color=NAVY)
    add_down_arrow(s, Inches(6.7), Inches(4.7), Inches(5.1))
    add_card(s, left_x, Inches(5.15), col_w * 2 + col_gap, Inches(0.55), fill=GREEN_BG, line_color=GREEN_BG)
    add_text(s, left_x, Inches(5.27), col_w * 2 + col_gap, Inches(0.32),
              "Services Layer — MigrationService · RecommendationService · FileRecommendationService · RestoreService",
              size=12, color=NAVY, align=PP_ALIGN.CENTER)
    add_text(s, Inches(0.6), Inches(5.95), Inches(12.1), Inches(0.55),
              "Verified by identity, not output: Qt.resolve_app_recommendation_strategy is CLI.resolve_app_recommendation_strategy — both call paths hold the same function object, so a policy change can't silently apply to only one interface.",
              size=13, italic=True, color=GREY, line_spacing=1.2)

    # ── 6. Recommendation engine + the fix it delivers ─────────────────────────
    s = blank_slide(prs)
    add_header(s, "Method", "Windows app → Linux package — and a named gap, closed")
    steps = [
        ("\U0001F4CB", "CSV mapping (238)", ""),
        ("\U0001F50D", "Fuzzy match", ""),
        ("\U0001F6E1", "Confidence floor", ""),
        ("\U0001F310", "Repology check", ""),
    ]
    icon_label_row(s, steps, top=Inches(1.8), circle_d=Inches(0.9), icon_size=26, label_size=14.5, sub_size=12, bg=DARK_BLUE)
    for i in range(len(steps) - 1):
        slot = Inches(11.5) / len(steps)
        cx = Inches(0.9) + slot * i + slot
        add_arrow(s, cx - Inches(0.3), Inches(2.32), cx + Inches(0.05), Inches(2.32), color=BLUE, weight=2)
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(3.6), Inches(0.05), Inches(0.7))
    rule.fill.solid(); rule.fill.fore_color.rgb = AMBER; rule.line.fill.background(); rule.shadow.inherit = False
    add_text(s, Inches(0.95), Inches(3.65), Inches(11.4), Inches(0.65),
              "Term paper: “Compatibility mapping relies on heuristic matching... not guaranteeing feature parity.”",
              size=14, italic=True, color=NAVY)
    add_text(s, Inches(0.7), Inches(4.55), Inches(6.0), Inches(0.4), "WHAT THIS PROJECT FIXED", size=13, bold=True, color=BLUE)
    deliv = ["Fuzzy matching (SequenceMatcher) replaces exact-string-only lookup",
             "Confidence floors stop the algorithm silently downgrading curated matches",
             "Live Repology verification — package existence checked, not assumed"]
    y = Inches(5.0)
    for i, d in enumerate(deliv):
        add_text(s, Inches(0.7), y, Inches(0.5), Inches(0.5), f"{i+1}", size=18, bold=True, color=GREEN)
        add_text(s, Inches(1.2), y + Inches(0.03), Inches(11.0), Inches(0.45), d, size=14, color=NAVY)
        y += Inches(0.55)

    # ── Objectives (PM) ──────────────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Method", "Measurable objectives, defined at project start")
    rows = [
        ["Objective", "Target", "Result"],
        ["O1 — Manual steps", "≤ 3 in guided mode", "3"],
        ["O2 — App coverage", "≥ 80% of top-50", "238 entries"],
        ["O3 — File integrity", "≥ 95% pass SHA-256", "100%"],
        ["O4 — Sovereignty Score", "≥ 85%", "Scored every run"],
        ["O5 — Qt/CLI parity", "Identical policy, both interfaces", "One shared module"],
        ["O6 — Cycle time", "< 20 min for ≤ 5GB", "Timed every run — see Critique"],
    ]
    table = fill_table(s, Inches(0.6), Inches(2.0), Inches(12.1), Inches(4.0), rows)
    table.columns[0].width = Inches(3.4)
    table.columns[1].width = Inches(4.4)
    table.columns[2].width = Inches(4.3)
    set_table_style(table, body_size=14, header_size=14)

    # ── Work breakdown & risk (PM) ───────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Method", "Work breakdown & risk")
    add_text(s, Inches(0.7), Inches(1.75), Inches(6.0), Inches(0.4), "7 WORK PACKAGES + 6-DAY RISK BUFFER", size=14, bold=True, color=BLUE)
    add_text(s, Inches(6.4), Inches(1.77), Inches(5.7), Inches(0.36),
              "Open risk: no physical-hardware E2E test — VM pair only", size=12, italic=True, color=AMBER, align=PP_ALIGN.RIGHT)
    add_picture_framed(s, ASSETS / "gantt_chart.png", Inches(0.6), Inches(2.35), Inches(12.1), Inches(3.6), border=False)

    # ── SECTION: Evidence ─────────────────────────────────────────────────────────
    section_divider(prs, "Evidence", "What actually ran, what actually broke, and what the numbers say")

    # ── Quantified improvement over the proof of concept ────────────────────────
    s = blank_slide(prs)
    add_header(s, "Evidence", "Quantified improvement over the proof of concept")
    rows = [
        ["Aspect", "Proof of concept", "This project", "Change"],
        ["App mappings", "25", "238", "9.5×"],
        ["Source LOC", "4,031", "17,467", "4.3×"],
        ["Automated tests", "0", "192", "0 → 192"],
        ["GUI framework", "Tkinter", "Qt (PySide6)", "rewritten"],
        ["App-matching stages", "1 (substring)", "3 (fuzzy + confidence + online)", "1 → 3"],
        ["Platforms packaged", "1 (Linux)", "2 (Win + Linux, auto-embed)", "1 → 2"],
    ]
    table = fill_table(s, Inches(0.6), Inches(1.8), Inches(12.1), Inches(3.3), rows)
    table.columns[0].width = Inches(2.6)
    table.columns[1].width = Inches(2.8)
    table.columns[2].width = Inches(4.4)
    table.columns[3].width = Inches(2.3)
    add_text(s, Inches(0.6), Inches(5.35), Inches(12.1), Inches(0.45),
              "New capabilities with no proof-of-concept equivalent: settings/wallpaper migration, desktop shortcuts, full reset/undo, completeness scoring.",
              size=13.5, color=NAVY)
    add_text(s, Inches(0.6), Inches(5.85), Inches(12.1), Inches(0.5),
              "github.com/PenCoder/semi-auto-migration — cloned and inspected directly for this comparison.",
              size=12.5, italic=True, color=GREY)

    # ── 7. Workflow — Windows + Linux ───────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Evidence", "7 guided steps, then 1 click")
    win_steps = ["Welcome", "Mode", "Scan +\nMatch", "Data", "Review", "Backup", "Bundle\nReport"]
    x = Inches(0.5)
    w = Inches(1.62)
    for i, label in enumerate(win_steps):
        add_icon_circle(s, x + w / 2, Inches(2.05), Inches(0.6), str(i + 1), fg=WHITE, bg=BLUE, size=15)
        add_text(s, x, Inches(2.42), w, Inches(0.55), label, size=11.5, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        if i < len(win_steps) - 1:
            add_arrow(s, x + w - Inches(0.05), Inches(2.05), x + w + Inches(0.12), Inches(2.05), color=BLUE)
        x += w + Inches(0.12)
    add_text(s, Inches(0.5), Inches(3.05), Inches(11.5), Inches(0.4), "→ migration_bundle.zip (manifest + SHA-256, apps, settings, optional Linux binary)",
              size=13, italic=True, color=GREY)
    add_icon_circle(s, Inches(0.95), Inches(3.95), Inches(0.7), "1", fg=WHITE, bg=GREEN, size=20)
    add_text(s, Inches(1.45), Inches(3.7), Inches(4.5), Inches(0.4), "Restore & Report", size=15, bold=True, color=NAVY)
    add_text(s, Inches(1.45), Inches(4.1), Inches(4.5), Inches(0.55),
              "Restore, verify (SHA-256), and report\nall happen within that one click.", size=12, color=GREY, line_spacing=1.15)
    add_text(s, Inches(0.5), Inches(4.85), Inches(5.6), Inches(0.8),
              "Failed step? Restart or Review & Complete Anyway. Reset undoes files, shortcuts, the wallpaper file, and (opt-in) apps.",
              size=13, color=GREY, line_spacing=1.2)
    pic, w2, h2 = add_picture_framed(s, ASSETS / "final_report.png", Inches(6.6), Inches(3.5), Inches(6.0), Inches(2.85),
                                       caption="Real report — actual VM restore, 3,344 files")

    # ── 8. Quality: tests + the bugs only live testing found ───────────────────
    s = blank_slide(prs)
    add_header(s, "Evidence", "192 tests — and 4 bugs only a live VM run exposed")
    add_bar_chart(
        s, Inches(0.6), Inches(1.85), Inches(6.0), Inches(3.5),
        categories=["Unit", "Integ.", "Perf.", "E2E", "UI"],
        series_name="Test functions", values=[80, 68, 18, 15, 11], bar_color=DARK_BLUE,
    )
    bugs = [
        ("Bad package name failed ALL installs", "per-package fallback"),
        ("Shortcuts matched requested, not installed", "matched to actual installs"),
        ("Silent multi-minute log gaps", "periodic progress logging"),
        ("Unanswered prompt could hang forever", "120s timeout per attempt"),
    ]
    y = Inches(1.95)
    for problem, fix in bugs:
        add_icon_circle(s, Inches(7.1), y + Inches(0.18), Inches(0.4), "!", fg=WHITE, bg=AMBER, size=15)
        add_text(s, Inches(7.45), y, Inches(5.15), Inches(0.4), problem, size=13, color=NAVY)
        add_icon_circle(s, Inches(7.1), y + Inches(0.62), Inches(0.4), "✓", fg=WHITE, bg=GREEN, size=14)
        add_text(s, Inches(7.45), y + Inches(0.45), Inches(5.15), Inches(0.4), fix, size=12.5, color=GREEN, bold=True)
        y += Inches(0.92)
    add_text(s, Inches(0.6), Inches(5.55), Inches(6.0), Inches(0.6), "CI passing ≠ the real app works.", size=14, italic=True, color=GREY)

    # ── 9. This session shipped ─────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Evidence", "Undo, and double-click distribution")
    items = [("\U0001F4C1", "Files"), ("\U0001F517", "Shortcuts"), ("\U0001F5BC", "Wallpaper"), ("\U0001F4E6", "Apps (opt-in)")]
    x = Inches(1.0)
    for glyph, label in items:
        add_icon_circle(s, x, Inches(2.3), Inches(0.95), glyph, fg=WHITE, bg=GREEN, size=24)
        add_text(s, x - Inches(0.9), Inches(2.85), Inches(1.8), Inches(0.4), label, size=13, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        x += Inches(2.55)
    add_text(s, Inches(0.6), Inches(3.5), Inches(11.5), Inches(0.45), "Reset now undoes all of the above — opt-in for apps, live progress in the Activity Log.", size=13.5, color=GREY)
    add_card(s, Inches(0.9), Inches(4.2), Inches(5.4), Inches(2.2), fill=WHITE)
    add_icon_circle(s, Inches(3.6), Inches(4.85), Inches(0.8), "\U0001FA9F", fg=WHITE, bg=DARK_BLUE, size=22)
    add_text(s, Inches(1.1), Inches(5.35), Inches(5.0), Inches(0.9), "migrate.exe\nPyInstaller; can bake the Linux\nbinary in for a single-file standalone.",
              size=12.5, color=GREY, align=PP_ALIGN.CENTER, line_spacing=1.2)
    add_card(s, Inches(6.9), Inches(4.2), Inches(5.4), Inches(2.2), fill=WHITE)
    add_icon_circle(s, Inches(9.6), Inches(4.85), Inches(0.8), "\U0001F427", fg=WHITE, bg=GREEN, size=22)
    add_text(s, Inches(7.1), Inches(5.35), Inches(5.0), Inches(0.9), "restore (ELF binary)\nBuilt on the target distro; embedded\nautomatically into every bundle.",
              size=12.5, color=GREY, align=PP_ALIGN.CENTER, line_spacing=1.2)

    # ── Evaluation ───────────────────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Evidence", "What the project delivers")
    metrics = [("238", "app mappings"), ("192", "automated tests"), ("3", "guidance modes"), ("2", "platforms packaged")]
    x = Inches(0.8)
    for num, label in metrics:
        add_card(s, x, Inches(1.8), Inches(2.75), Inches(1.5), fill=WHITE)
        add_text(s, x, Inches(1.95), Inches(2.75), Inches(0.75), num, size=32, bold=True, color=BLUE, align=PP_ALIGN.CENTER)
        add_text(s, x + Inches(0.15), Inches(2.6), Inches(2.45), Inches(0.5), label, size=12.5, color=NAVY, align=PP_ALIGN.CENTER)
        x += Inches(2.88)
    add_bar_chart(
        s, Inches(0.8), Inches(3.55), Inches(5.5), Inches(3.5),
        categories=["Before", "Now"], series_name="App mappings",
        values=[149, 238], bar_color=GREEN, title="App mapping table growth",
    )
    pic, w, h = add_picture_framed(s, ASSETS / "final_report.png", Inches(6.7), Inches(3.5), Inches(5.9), Inches(2.8),
                                     caption="100% sovereignty score — real restore, 3,344 files")

    # ── SECTION: Critique ──────────────────────────────────────────────────────────
    section_divider(prs, "Critique", "Where the project's own claims didn't hold up when checked against the system")

    # ── Honest limitations ────────────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Critique", "Four review gaps, plus two found checking our own claims")
    rows = [
        ["#", "Gap raised", "Fix", "Status"],
        ["1", "Vague objectives (\"more dynamic strategies\")", "O1–O6 measurable targets, each with a result", "Done"],
        ["2", "Qt/CLI consistency too coarse", "src/orchestration/mode_policy.py — one shared function per decision", "Done"],
        ["3", "Tight timeline, no buffer", "6-day risk buffer added to the Gantt", "Stale dates"],
        ["4", "Evaluation lacks metrics", "Automation count, Sovereignty Score, timing real; precision/recall = target only", "Partial"],
    ]
    table = fill_table(s, Inches(0.6), Inches(1.7), Inches(12.1), Inches(2.75), rows)
    table.columns[0].width = Inches(0.5)
    table.columns[1].width = Inches(3.3)
    table.columns[2].width = Inches(6.5)
    table.columns[3].width = Inches(1.8)
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(4.65), Inches(0.05), Inches(1.7))
    rule.fill.solid(); rule.fill.fore_color.rgb = AMBER; rule.line.fill.background(); rule.shadow.inherit = False
    add_text(s, Inches(0.85), Inches(4.65), Inches(11.8), Inches(0.4), "FOUND WHEN RE-CHECKING THE PROJECT'S OWN CLAIMS", size=12.5, bold=True, color=AMBER)
    add_text(s, Inches(0.85), Inches(5.05), Inches(11.8), Inches(0.6),
              "O6 (cycle time) does not hold up: target was <20 min for ≤5GB; the real logged run took ~30–35 minutes for extract+restore+verify alone.",
              size=13.5, color=NAVY, line_spacing=1.2)
    add_text(s, Inches(0.85), Inches(5.6), Inches(11.8), Inches(0.6),
              "Recommendation-quality precision/recall: 0% measured. Methodology is defined; no ground-truth evaluation script has been built or run.",
              size=13.5, color=NAVY, line_spacing=1.2)

    # ── SECTION: Takeaway ────────────────────────────────────────────────────────
    section_divider(prs, "Takeaway", "What was delivered, what's still open, and what to do about it")

    # ── 12. Conclusion & future work ────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Takeaway", "Conclusion & future work")
    rule1 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.95), Inches(0.05), Inches(4.4))
    rule1.fill.solid(); rule1.fill.fore_color.rgb = GREEN; rule1.line.fill.background(); rule1.shadow.inherit = False
    add_text(s, Inches(1.0), Inches(1.9), Inches(5.0), Inches(0.4), "DELIVERED", size=16, bold=True, color=GREEN)
    deliv = ["Dynamic recommendation engine", "Unified mode policy (Qt + CLI)", "Per-stage execution timing",
             "192 test regression coverage", "Real-VM-tested reliability fixes", "Full undo/reset + packaging"]
    y = Inches(2.55)
    for d in deliv:
        add_icon_circle(s, Inches(1.2), y + Inches(0.19), Inches(0.38), "✓", fg=WHITE, bg=GREEN, size=13)
        add_text(s, Inches(1.55), y + Inches(0.04), Inches(4.9), Inches(0.45), d, size=14, color=NAVY)
        y += Inches(0.62)
    rule2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.7), Inches(1.95), Inches(0.05), Inches(4.4))
    rule2.fill.solid(); rule2.fill.fore_color.rgb = AMBER; rule2.line.fill.background(); rule2.shadow.inherit = False
    add_text(s, Inches(7.0), Inches(1.9), Inches(5.0), Inches(0.4), "NEXT", size=16, bold=True, color=AMBER)
    nxt = ["Real precision/recall evaluation script", "Real E2E test, physical machines", "Live USB write automation", "Resume/checkpoint for large restores"]
    y = Inches(2.55)
    for n in nxt:
        add_icon_circle(s, Inches(7.2), y + Inches(0.19), Inches(0.38), "→", fg=WHITE, bg=AMBER, size=13)
        add_text(s, Inches(7.55), y + Inches(0.0), Inches(4.9), Inches(0.6), n, size=14, color=NAVY)
        y += Inches(0.7)

    # ── 13. References ──────────────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Takeaway", "References — sovereignty framing cited from the term paper")
    refs = [
        "Floridi, L. (2020). The fight for digital sovereignty. Philosophy & Technology, 33(3), 369–378.",
        "Pohle, J., & Thiel, T. (2020). Digital sovereignty. Internet Policy Review, 9(4).",
        "Roberts, H., et al. (2021). Safeguarding European values with digital sovereignty. Internet Policy Review, 10(3).",
        "Wehnes, H. (2024). Preventing digital colony and lock-in. INFORMATIK 2024, Gesellschaft für Informatik.",
        "Wire (2025); StatCounter Global Stats (2025). Digital sovereignty survey & OS market share, Europe.",
    ]
    y = Inches(2.1)
    for r in refs:
        add_text(s, Inches(0.9), y, Inches(11.5), Inches(0.45), "•  " + r, size=14.5, color=NAVY)
        y += Inches(0.65)
    add_text(s, Inches(0.9), y + Inches(0.2), Inches(11.5), Inches(0.5),
              "Full bibliography: Arthur, J. — Digital Sovereignty Through Semi-Automated OS Migration (term paper).",
              size=13, italic=True, color=GREY)

    # ── 14. Thank you ────────────────────────────────────────────────────────────
    title_slide(prs, "Thank you", "Questions & live demo")

    return prs


if __name__ == "__main__":
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs = build()
    prs.save(OUT_PATH)
    print(f"Saved {len(prs.slides)} slides to {OUT_PATH}")
