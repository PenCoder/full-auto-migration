"""Generates docs/presentation/Migration_Wizard_Praktikum_Presentation.pptx.

One-shot content generator, not part of the app itself. Re-run after editing
this file to regenerate the deck.
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "presentation" / "Migration_Wizard_Praktikum_Presentation.pptx"

# Palette lifted from the app's own Qt theme for visual consistency.
NAVY = RGBColor(0x1B, 0x1E, 0x28)
BLUE = RGBColor(0x3F, 0x6F, 0xE0)
DARK_BLUE = RGBColor(0x1B, 0x3A, 0x86)
LIGHT_BLUE_BG = RGBColor(0xDC, 0xE6, 0xFF)
GREEN = RGBColor(0x1B, 0x5E, 0x20)
GREEN_BG = RGBColor(0xE8, 0xF5, 0xE9)
AMBER = RGBColor(0xE6, 0x51, 0x00)
AMBER_BG = RGBColor(0xFF, 0xF3, 0xE0)
GREY = RGBColor(0x54, 0x6E, 0x7A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BG = RGBColor(0xF7, 0xFB, 0xFE)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def new_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs: Presentation):
    layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(layout)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG
    bg.line.fill.background()
    bg.shadow.inherit = False
    # Send background to back
    spTree = slide.shapes._spTree
    spTree.remove(bg._element)
    spTree.insert(2, bg._element)
    return slide


def add_text(slide, left, top, width, height, text, size=18, bold=False, color=NAVY,
             align=PP_ALIGN.LEFT, font="Segoe UI", anchor=None, italic=False, line_spacing=None):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    if anchor:
        tf.vertical_anchor = anchor
    lines = text.split("\n")
    for i, line in enumerate(lines):
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


def add_bullets(slide, left, top, width, height, items, size=16, color=NAVY, bullet_color=BLUE,
                 space_after=10, bold_first_sentence=False):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        marker = p.add_run()
        marker.text = "›  "
        marker.font.size = Pt(size)
        marker.font.bold = True
        marker.font.color.rgb = bullet_color
        marker.font.name = "Segoe UI"
        run = p.add_run()
        run.text = item
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = "Segoe UI"
    return box


def add_header(slide, kicker, title, kicker_color=BLUE):
    add_text(slide, Inches(0.7), Inches(0.35), Inches(11), Inches(0.4), kicker.upper(),
              size=13, bold=True, color=kicker_color)
    add_text(slide, Inches(0.7), Inches(0.7), Inches(11.9), Inches(0.9), title,
              size=30, bold=True, color=NAVY)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.5), Inches(1.2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = BLUE
    line.line.fill.background()
    line.shadow.inherit = False


def add_card(slide, left, top, width, height, fill=WHITE, line_color=RGBColor(0xC3, 0xD6, 0xE0), radius=True):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    card = slide.shapes.add_shape(shape_type, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = fill
    card.line.color.rgb = line_color
    card.line.width = Pt(1)
    card.shadow.inherit = False
    if radius:
        try:
            card.adjustments[0] = 0.06
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
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
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


def set_table_style(table, header_bg=DARK_BLUE, header_fg=WHITE, body_size=13, header_size=13):
    for r_idx, row in enumerate(table.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.margin_left = Pt(8)
            cell.margin_right = Pt(8)
            cell.margin_top = Pt(4)
            cell.margin_bottom = Pt(4)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            if r_idx == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_bg
            else:
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if r_idx % 2 else RGBColor(0xEE, 0xF7, 0xFB)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(header_size if r_idx == 0 else body_size)
                    run.font.color.rgb = header_fg if r_idx == 0 else NAVY
                    run.font.bold = r_idx == 0
                    run.font.name = "Segoe UI"


def fill_table(slide, left, top, width, height, rows_data):
    rows = len(rows_data)
    cols = len(rows_data[0])
    shape = slide.shapes.add_table(rows, cols, left, top, width, height)
    table = shape.table
    for r, row_vals in enumerate(rows_data):
        for c, val in enumerate(row_vals):
            table.cell(r, c).text = str(val)
    set_table_style(table)
    return table


# ─────────────────────────────────────────────────────────────────────────────

def build() -> Presentation:
    prs = new_presentation()

    # ── 1. Title ─────────────────────────────────────────────────────────────
    s = blank_slide(prs)
    band = slide_band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(7.5))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()
    band.shadow.inherit = False
    spTree = s.shapes._spTree
    spTree.remove(band._element)
    spTree.insert(2, band._element)

    add_pill(s, Inches(0.7), Inches(1.0), Inches(2.6), Inches(0.45), "MOBILE COMPUTING SEMINAR", WHITE, DARK_BLUE, size=12)
    add_text(s, Inches(0.7), Inches(1.7), Inches(11.5), Inches(1.6),
              "Migration Wizard", size=54, bold=True, color=WHITE)
    add_text(s, Inches(0.7), Inches(2.85), Inches(11.5), Inches(1.0),
              "Toward a Fully Automated Migration Framework\nfrom Windows 11 to Linux Mint",
              size=24, bold=False, color=LIGHT_BLUE_BG, line_spacing=1.2)
    add_text(s, Inches(0.7), Inches(6.3), Inches(8), Inches(0.5),
              "Japhet Kofi Appau Arthur  ·  Praktikum Final Presentation", size=16, color=RGBColor(0xAE, 0xC2, 0xE8))

    # ── 2. Problem & Motivation ─────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Motivation", "Switching from Windows to Linux is harder than it should be")
    add_bullets(s, Inches(0.8), Inches(1.9), Inches(7.3), Inches(4.5), [
        "Files, installed apps, and desktop settings all live in different,\nincompatible places between Windows and Linux.",
        "Manually figuring out “what's the Linux equivalent of this app?”\nfor dozens of programs is tedious and error-prone.",
        "Most existing tools handle one piece (file copy, or app install)\n— never the full picture, and rarely for non-technical users.",
        "Goal: one guided tool that handles the whole journey —\nfiles, apps, and settings — with as little manual decision-making\nas the user wants.",
    ], size=17, space_after=18)
    card = add_card(s, Inches(8.5), Inches(1.9), Inches(4.0), Inches(4.5), fill=WHITE)
    add_text(s, Inches(8.7), Inches(2.1), Inches(3.6), Inches(0.4), "WHAT MOVES", size=13, bold=True, color=BLUE)
    add_bullets(s, Inches(8.7), Inches(2.55), Inches(3.6), Inches(3.6), [
        "Personal files (Documents, Pictures, …)",
        "Installed applications → Linux equivalents",
        "Desktop settings (wallpaper, theme, light/dark)",
        "Desktop shortcuts & taskbar launchers",
    ], size=15, space_after=14)

    # ── 3. Goal & Approach ───────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Approach", "A guided, two-phase, privacy-preserving pipeline")
    phases = [
        ("1", "Prepare", "Windows 11", "Scan → app mapping → file & settings\nselection → packed into one bundle", GREEN, GREEN_BG),
        ("2", "Restore", "Linux Mint", "Bundle copied via USB → files restored,\napps installed, settings applied", DARK_BLUE, LIGHT_BLUE_BG),
    ]
    x = Inches(0.8)
    for num, title, sub, desc, color, bg in phases:
        card = add_card(s, x, Inches(2.0), Inches(5.6), Inches(3.6), fill=WHITE)
        add_pill(s, x + Inches(0.3), Inches(2.3), Inches(0.6), Inches(0.6), num, WHITE, color, size=20)
        add_text(s, x + Inches(1.1), Inches(2.3), Inches(4.0), Inches(0.5), title, size=24, bold=True, color=NAVY)
        add_text(s, x + Inches(1.1), Inches(2.75), Inches(4.0), Inches(0.4), sub, size=14, bold=True, color=color)
        add_text(s, x + Inches(0.4), Inches(3.4), Inches(4.8), Inches(2.0), desc, size=16, color=GREY, line_spacing=1.3)
        x += Inches(6.0)
    add_text(s, Inches(0.8), Inches(5.9), Inches(11.5), Inches(0.8),
              "Three guidance levels (Guided / Balanced / Expert) control how many of these\ndecisions the user makes themselves — same destination, different amount of control.",
              size=15, italic=True, color=GREY)

    # ── 4. System Architecture ───────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Architecture", "Clean layer separation, MVC on the Qt side")
    layers = [
        ("src/inventory/", "Hardware, software, settings collectors", GREEN_BG, GREEN),
        ("src/analysis/", "Hardware matrix + software mapping (fuzzy + confidence)", LIGHT_BLUE_BG, DARK_BLUE),
        ("src/services/", "Recommendation, migration, restore, validation, report", AMBER_BG, AMBER),
        ("src/orchestration/", "Error handling + checkpointing", GREEN_BG, GREEN),
        ("src/qt_ui/", "Pages (view) + Controllers + shared state (MVC)", LIGHT_BLUE_BG, DARK_BLUE),
    ]
    y = Inches(1.9)
    for name, desc, bg, fg in layers:
        add_card(s, Inches(0.8), y, Inches(2.6), Inches(0.75), fill=bg, line_color=bg)
        add_text(s, Inches(0.95), y + Inches(0.12), Inches(2.3), Inches(0.5), name, size=15, bold=True, color=fg)
        add_text(s, Inches(3.7), y + Inches(0.12), Inches(8.6), Inches(0.5), desc, size=15, color=NAVY)
        y += Inches(0.92)
    add_text(s, Inches(0.8), Inches(6.6), Inches(11.5), Inches(0.5),
              "Qt window stays thin: AutomationCoordinator, NavigationController, ModeController, and\nOperationsController do the real work — the window just wires pages to them.",
              size=14, italic=True, color=GREY)

    # ── 5. Three-Mode System ─────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "User experience", "One pipeline, three levels of control")
    rows = [
        ["Stage", "Guided", "Balanced", "Expert"],
        ["Inventory scan", "✓", "✓", "✓"],
        ["Compatibility analysis", "—", "✓", "✓"],
        ["App recommendations", "local mapping", "local mapping", "local + Repology online check"],
        ["File recommendations", "—", "all files", "usage-based, AI-assisted"],
        ["Manual overrides", "—", "—", "✓"],
    ]
    fill_table(s, Inches(0.8), Inches(1.9), Inches(11.7), Inches(3.4), rows)
    add_text(s, Inches(0.8), Inches(5.55), Inches(11.5), Inches(1.3),
              "Guided and Balanced never touch the network — only Expert mode triggers a live\nRepology lookup, and only to verify package availability for an already-chosen\nLinux package, never to “discover” the mapping itself.",
              size=15, color=GREY, line_spacing=1.3)

    # ── 6. Recommendation Engine ──────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Core logic", "How a Windows app becomes a Linux package")
    steps = [
        ("1", "CSV mapping table", "238 curated entries (configs/linux_ms_map.csv): Windows app name → Linux package, category, migration strategy, expert confidence."),
        ("2", "Fuzzy matching", "SequenceMatcher finds the best CSV row even with version numbers or naming variations (e.g. “7-Zip 24.09 (x64)”)."),
        ("3", "Confidence floors", "Expert-assigned CSV confidence (high/medium/low) sets a minimum score — a curated match is never silently downgraded."),
        ("4", "Online verification (Expert mode only)", "Repology API confirms the chosen package actually exists in Mint/Ubuntu repos before recommending it."),
    ]
    y = Inches(1.85)
    for num, title, desc in steps:
        add_pill(s, Inches(0.8), y, Inches(0.5), Inches(0.5), num, WHITE, BLUE, size=16)
        add_text(s, Inches(1.5), y - Inches(0.05), Inches(4.0), Inches(0.5), title, size=17, bold=True, color=NAVY)
        add_text(s, Inches(1.5), y + Inches(0.42), Inches(10.6), Inches(0.7), desc, size=14, color=GREY, line_spacing=1.2)
        y += Inches(1.18)

    # ── 7. Windows-side workflow ──────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Workflow — Windows side", "7 guided steps from scan to bundle")
    win_steps = ["Welcome", "Choose Mode", "System Scan\n+ App Matching", "Settings", "Select Files", "Review &\nConfirm", "Create Bundle"]
    x = Inches(0.6)
    w = Inches(1.65)
    for i, label in enumerate(win_steps):
        card = add_card(s, x, Inches(2.6), w, Inches(1.5), fill=WHITE)
        add_pill(s, x + Inches(0.55), Inches(2.8), Inches(0.55), Inches(0.55), str(i + 1), WHITE, BLUE, size=16)
        add_text(s, x + Inches(0.08), Inches(3.45), w - Inches(0.16), Inches(0.6), label, size=12, bold=True,
                  color=NAVY, align=PP_ALIGN.CENTER)
        if i < len(win_steps) - 1:
            arrow = add_text(s, x + w - Inches(0.05), Inches(3.05), Inches(0.3), Inches(0.4), "→", size=20, bold=True, color=BLUE)
        x += w + Inches(0.05)
    add_bullets(s, Inches(0.8), Inches(4.6), Inches(11.5), Inches(2.3), [
        "Output: migration_bundle.zip — manifest + SHA-256 checksums, app install list, settings, shortcuts, and (optionally) a pre-built Linux restore binary, all self-contained.",
        "Carried to the Linux machine via USB, network share, or cloud storage.",
    ], size=15, space_after=14)

    # ── 8. Linux-side workflow ─────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Workflow — Linux side", "One click: restore → verify → report")
    lin_steps = [
        ("Extract & Restore", "Unzip bundle, copy files preserving folder structure, install apps, recreate shortcuts, apply wallpaper/theme."),
        ("Verify", "Re-hash every restored file (SHA-256) against the manifest — confirms nothing got corrupted."),
        ("Report", "Sovereignty Score + JSON/Markdown/HTML report: what succeeded, what needs manual setup, what failed and why."),
    ]
    x = Inches(0.8)
    for i, (title, desc) in enumerate(lin_steps):
        card = add_card(s, x, Inches(1.95), Inches(3.6), Inches(3.6), fill=WHITE)
        add_pill(s, x + Inches(0.3), Inches(2.2), Inches(0.55), Inches(0.55), str(i + 1), WHITE, GREEN, size=16)
        add_text(s, x + Inches(0.3), Inches(2.95), Inches(3.0), Inches(0.6), title, size=17, bold=True, color=NAVY)
        add_text(s, x + Inches(0.3), Inches(3.55), Inches(3.0), Inches(1.8), desc, size=13.5, color=GREY, line_spacing=1.25)
        x += Inches(3.85)
    add_bullets(s, Inches(0.8), Inches(5.9), Inches(11.5), Inches(1.0), [
        "If a step fails partway: “Restart” (full reset) or “Review & Complete Anyway” — nothing fails silently.",
        "Reset can also undo a previous restore entirely: files, shortcuts, settings files, and (opt-in) installed apps.",
    ], size=14.5, space_after=10)

    # ── 9. Privacy ─────────────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Design principle", "Privacy by default, every layer")
    rows = [
        ["Component", "Privacy measure"],
        ["File inventory", "Files never leave the local machine; paths redacted in logs"],
        ["Repology lookup", "Only name / version / publisher sent — no file content, ever"],
        ["AI-assisted ranking", "Expert mode only; opt-in, never sends file paths externally"],
        ["Research metrics", "Machine ID anonymised; no personal identifiers recorded"],
        ["Backup bundle", "Stored locally; user chooses and controls the destination"],
    ]
    fill_table(s, Inches(0.8), Inches(1.9), Inches(11.7), Inches(3.6), rows)

    # ── 10. Validation & Reporting ───────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Evidence the migration worked", "Sovereignty Score & multi-format reports")
    add_bullets(s, Inches(0.8), Inches(1.95), Inches(6.7), Inches(4.5), [
        "Every restored file is hash-verified (SHA-256) against the original manifest.",
        "Sovereignty Score (0–100%) summarises integrity across the whole restore.",
        "Final report ships in three formats: JSON (machine-readable), Markdown,\nand a styled standalone HTML page — openable straight from the app,\neven in a brand-new session (no bundle required to re-open it).",
        "Report surfaces what actually happened: files restored, apps installed\nvs. failed, settings applied vs. needing manual setup, and any warnings\n— not just a pass/fail flag.",
    ], size=16, space_after=16)
    card = add_card(s, Inches(8.0), Inches(1.95), Inches(4.5), Inches(4.4), fill=WHITE)
    add_text(s, Inches(8.2), Inches(2.15), Inches(4.0), Inches(0.4), "REPORT SECTIONS", size=13, bold=True, color=BLUE)
    add_bullets(s, Inches(8.2), Inches(2.6), Inches(4.0), Inches(3.6), [
        "Key Metrics", "Warnings", "Timing", "Settings & Configuration",
        "App Matches", "Shortcuts & Launchers", "Restore Details", "Activity Log",
    ], size=14, space_after=10)

    # ── 11. Testing ───────────────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Quality", "190+ automated tests across four levels")
    rows = [
        ["Level", "Coverage"],
        ["Unit", "Mapping accuracy, scoring, graceful failure handling"],
        ["Integration", "Mode gating, timing, category/confidence propagation, CLI parity"],
        ["End-to-end", "Full mode-selection → scan → recommendation flow"],
        ["Performance", "Throughput benchmarks"],
    ]
    fill_table(s, Inches(0.8), Inches(1.9), Inches(7.0), Inches(3.0), rows)
    card = add_card(s, Inches(8.1), Inches(1.9), Inches(4.4), Inches(3.0), fill=WHITE)
    add_text(s, Inches(8.3), Inches(2.1), Inches(4.0), Inches(0.4), "WHY IT MATTERS HERE", size=13, bold=True, color=BLUE)
    add_bullets(s, Inches(8.3), Inches(2.55), Inches(4.0), Inches(2.3), [
        "CI tests pass ≠ the real app works",
        "Several real bugs this session were\nfound only by running the app on\na live Windows + Linux Mint VM pair",
    ], size=14, space_after=12)
    add_text(s, Inches(0.8), Inches(5.2), Inches(11.5), Inches(0.5),
              "→ next slide: what running it for real actually surfaced.", size=15, italic=True, color=GREY)

    # ── 12. Hardening this session ────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Found via live testing", "Real bugs only a live VM run exposed")
    bugs = [
        ("Atomic install failure", "One invalid package name failed the ENTIRE apt-get batch — nothing installed, not just the bad one.",
         "Batch attempt first, falls back to one-package-at-a-time on failure."),
        ("Shortcuts matched the wrong list", "Desktop shortcuts were matched against requested apps, not apps that actually installed.",
         "Shortcuts now matched only against genuinely-installed apps."),
        ("Silent multi-minute gaps", "Extraction, file restore, and verification produced zero log output for minutes at a time.",
         "Periodic progress logging added to every long-running phase."),
        ("No timeout on elevation calls", "An unanswered pkexec prompt could hang Reset/Install forever.",
         "120s timeout per attempt; treated as a normal failure, not a hang."),
    ]
    y = Inches(1.85)
    for title, problem, fix in bugs:
        add_text(s, Inches(0.8), y, Inches(11.5), Inches(0.4), title, size=16, bold=True, color=NAVY)
        add_text(s, Inches(1.0), y + Inches(0.38), Inches(11.0), Inches(0.4), "Problem: " + problem, size=12.5, color=AMBER)
        add_text(s, Inches(1.0), y + Inches(0.72), Inches(11.0), Inches(0.4), "Fix: " + fix, size=12.5, color=GREEN)
        y += Inches(1.18)

    # ── 13. Reset / Undo feature ─────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "New capability", "Reset now undoes a restore completely")
    add_bullets(s, Inches(0.8), Inches(1.95), Inches(11.5), Inches(4.0), [
        "Previously: Reset only deleted the restored files.",
        "Now: files, desktop shortcuts/launchers, the wallpaper file written during\nrestore — and optionally, the apps that were installed.",
        "App removal is opt-in and off by default: removing a shared dependency\ncould affect other software — the checkbox makes that risk explicit.",
        "Works from a brand-new app session too — reads entirely from the\nalready-written restore report, no original bundle required.",
        "Live progress reported the same way restore does — visible in the\nActivity Log, not just the log file.",
    ], size=16, space_after=16)

    # ── 14. Packaging ──────────────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Distribution", "Double-click standalone apps, both platforms")
    x = Inches(0.8)
    cards = [
        ("Windows", "MigrationWizard.exe", "PyInstaller --onefile build of the full Qt app.\nOptionally bakes the Linux binary in directly,\nfor a true single-file standalone."),
        ("Linux Mint", "MigrationWizard (ELF binary)", "Built on the target distro itself — PyInstaller\ncan't cross-compile. Embedded automatically into\nevery bundle the Windows app creates."),
    ]
    for title, name, desc in cards:
        add_card(s, x, Inches(1.95), Inches(5.6), Inches(3.4), fill=WHITE)
        add_text(s, x + Inches(0.3), Inches(2.15), Inches(5.0), Inches(0.4), title, size=18, bold=True, color=DARK_BLUE)
        add_text(s, x + Inches(0.3), Inches(2.65), Inches(5.0), Inches(0.4), name, size=14, bold=True, color=BLUE)
        add_text(s, x + Inches(0.3), Inches(3.15), Inches(5.0), Inches(2.0), desc, size=13.5, color=GREY, line_spacing=1.3)
        x += Inches(5.9)
    add_text(s, Inches(0.8), Inches(5.7), Inches(11.5), Inches(0.8),
              "Bundle stays self-contained: unzip, run the embedded binary, click Browse → Restore.\nNo Python install required on either machine.",
              size=15, italic=True, color=GREY)

    # ── 15. Results / Evaluation ──────────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Evaluation", "What the project actually delivers")
    metrics = [
        ("238", "curated Windows→Linux\napp mappings"),
        ("190+", "automated tests\nacross 4 levels"),
        ("3", "guidance modes,\none consistent pipeline"),
        ("2", "platforms packaged as\ndouble-click standalone apps"),
    ]
    x = Inches(0.8)
    for num, label in metrics:
        add_card(s, x, Inches(2.0), Inches(2.7), Inches(2.0), fill=WHITE)
        add_text(s, x, Inches(2.25), Inches(2.7), Inches(0.9), num, size=40, bold=True, color=BLUE, align=PP_ALIGN.CENTER)
        add_text(s, x + Inches(0.15), Inches(3.15), Inches(2.4), Inches(0.7), label, size=13, color=NAVY, align=PP_ALIGN.CENTER)
        x += Inches(2.85)
    add_bullets(s, Inches(0.8), Inches(4.5), Inches(11.5), Inches(2.3), [
        "Functionality: inventory → mapping → file recs → backup → restore → validation →\nreport all operate end-to-end, verified by running the real two-machine flow.",
        "Automation: Guided mode requires zero post-setup decisions; Balanced and\nExpert progressively add control without changing the underlying pipeline.",
    ], size=15.5, space_after=14)

    # ── 16. Conclusion & Future Work ─────────────────────────────────────────
    s = blank_slide(prs)
    add_header(s, "Wrap-up", "Conclusion & future work")
    left = add_card(s, Inches(0.8), Inches(1.9), Inches(5.7), Inches(4.6), fill=WHITE)
    add_text(s, Inches(1.0), Inches(2.1), Inches(5.3), Inches(0.4), "KEY CONTRIBUTIONS", size=13, bold=True, color=GREEN)
    add_bullets(s, Inches(1.0), Inches(2.55), Inches(5.3), Inches(3.8), [
        "Dynamic recommendation engine: fuzzy matching +\nconfidence floors + category propagation + Repology",
        "One mode policy enforced consistently across\nboth the Qt wizard and the CLI",
        "Per-stage execution timing for every pipeline run",
        "Comprehensive, multi-level automated test coverage",
        "This session: real-VM-tested reliability fixes +\nfull undo/reset + cross-platform packaging",
    ], size=14, space_after=12, bullet_color=GREEN)
    right = add_card(s, Inches(6.85), Inches(1.9), Inches(5.65), Inches(4.6), fill=WHITE)
    add_text(s, Inches(7.05), Inches(2.1), Inches(5.3), Inches(0.4), "FUTURE WORK", size=13, bold=True, color=AMBER)
    add_bullets(s, Inches(7.05), Inches(2.55), Inches(5.3), Inches(3.8), [
        "Real end-to-end test on a physical (non-VM) machine pair",
        "Live USB write automation (currently a CLI stub)",
        "Resume/checkpoint support for very large restores,\nso a retry doesn't re-extract and re-hash everything",
        "Broader Linux distro support beyond Mint/Ubuntu",
    ], size=14, space_after=12, bullet_color=AMBER)

    # ── 17. Thank you ─────────────────────────────────────────────────────────
    s = blank_slide(prs)
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Inches(7.5))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()
    band.shadow.inherit = False
    spTree = s.shapes._spTree
    spTree.remove(band._element)
    spTree.insert(2, band._element)
    add_text(s, Inches(0.8), Inches(2.9), Inches(11.5), Inches(1.2), "Thank you", size=48, bold=True, color=WHITE)
    add_text(s, Inches(0.8), Inches(3.9), Inches(11.5), Inches(0.6), "Questions & live demo", size=22, color=LIGHT_BLUE_BG)

    return prs


if __name__ == "__main__":
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs = build()
    prs.save(OUT_PATH)
    print(f"Saved {len(prs.slides)} slides to {OUT_PATH}")
