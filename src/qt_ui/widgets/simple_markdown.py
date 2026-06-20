"""Tiny Markdown → HTML renderer for the bundled user manual.

Not a general CommonMark implementation — just enough to render
docs/USER_MANUAL.md (headers, bold/italic/code, blockquotes, tables,
lists, code fences, hr, bare links) into a nicely branded standalone
HTML page, without adding a markdown dependency or fighting Qt's
QTextEdit.toHtml() inline-style output.
"""

from __future__ import annotations

import base64
import html
import mimetypes
import re
from pathlib import Path

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
_CODE = re.compile(r"`([^`]+?)`")
_BARE_LINK = re.compile(r"(?<![\"'(>])(https?://[^\s)*]+)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_IMAGE_LINE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")


def _image_src(src: str, base_dir: Path | None) -> str:
    """Resolve a Markdown image path to a usable <img src>.

    Embeds local files as base64 data URIs so the rendered HTML stays
    self-contained no matter where it ends up written to (a temp dir,
    not next to the source Markdown) — bare http(s) URLs pass through
    unchanged.
    """
    if src.startswith(("http://", "https://", "data:")):
        return src
    if base_dir is None:
        return src

    candidate = (base_dir / src).resolve()
    if not candidate.is_file():
        return src

    mime, _ = mimetypes.guess_type(candidate.name)
    mime = mime or "image/png"
    data = base64.b64encode(candidate.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _inline(text: str) -> str:
    """Apply inline formatting (bold/italic/code/links) to already-escaped-safe text."""
    text = html.escape(text)
    text = _MD_LINK.sub(r'<a href="\2">\1</a>', text)
    text = _BARE_LINK.sub(r'<a href="\1">\1</a>', text)
    text = _CODE.sub(r"<code>\1</code>", text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    return text


def _render_table(rows: list[str]) -> str:
    header_cells = [c.strip() for c in rows[0].strip("|").split("|")]
    body_rows = rows[2:]  # rows[1] is the |---|---| separator
    out = ["<table>", "<thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in header_cells]
    out.append("</tr></thead><tbody>")
    for row in body_rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def markdown_to_html_body(md_text: str, base_dir: Path | None = None) -> str:
    """Convert Markdown text to an HTML fragment (no <html>/<head> wrapper).

    *base_dir* anchors relative image paths (e.g. `![...](assets/x.png)`),
    resolved relative to the directory the source Markdown file lives in.
    """
    lines = md_text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Code fence
        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
            continue

        # Horizontal rule
        if stripped == "---":
            out.append("<hr>")
            i += 1
            continue

        # Headers
        m = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # Blockquote (group consecutive "> " lines)
        if stripped.startswith(">"):
            quote_lines = []
            while i < n and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote>" + _inline(" ".join(quote_lines)) + "</blockquote>")
            continue

        # Table (header row + separator row)
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|?[\s:|-]+\|?$", lines[i + 1].strip()):
            table_rows = [lines[i].strip(), lines[i + 1].strip()]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                table_rows.append(lines[i].strip())
                i += 1
            out.append(_render_table(table_rows))
            continue

        # Standalone image — own figure with optional caption from alt text
        img_m = _IMAGE_LINE.match(stripped)
        if img_m:
            alt, src = img_m.group(1), img_m.group(2)
            resolved = _image_src(src, base_dir)
            caption = f"<figcaption>{html.escape(alt)}</figcaption>" if alt else ""
            out.append(
                f'<figure class="screenshot"><img src="{resolved}" alt="{html.escape(alt)}">{caption}</figure>'
            )
            i += 1
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ol>")
            continue

        # Unordered list
        if stripped.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue

        # Paragraph — gather until blank line
        para_lines = [stripped]
        i += 1
        while (
            i < n
            and lines[i].strip()
            and not lines[i].strip().startswith(("#", ">", "-", "|", "```", "---", "!["))
            and not re.match(r"^\d+\.\s+", lines[i].strip())
        ):
            para_lines.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_inline(' '.join(para_lines))}</p>")

    return "\n".join(out)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{
    margin: 0;
    background: #F5F8FF;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1B1E28;
  }}
  .hero {{
    background: linear-gradient(135deg, #3F6FE0, #7BA0F2);
    color: #FFFFFF;
    padding: 48px 24px 36px;
    text-align: center;
  }}
  .hero .icon {{ font-size: 44px; }}
  .hero h1 {{ font-size: 28px; font-weight: 800; margin: 8px 0 4px; }}
  .hero p {{ font-size: 15px; opacity: 0.9; margin: 0; }}
  .content {{
    max-width: 760px;
    margin: -28px auto 60px;
    background: #FFFFFF;
    border-radius: 16px;
    box-shadow: 0 12px 32px rgba(63, 111, 224, 0.16);
    padding: 40px 48px;
  }}
  h1 {{ font-size: 26px; font-weight: 800; color: #1B1E28; }}
  h2 {{
    font-size: 21px; font-weight: 800; color: #1B1E28;
    margin-top: 36px; padding-top: 10px; border-top: 1px solid #EEF1FA;
  }}
  h3 {{ font-size: 16px; font-weight: 700; color: #3F6FE0; margin-top: 22px; }}
  p, li {{ font-size: 14.5px; line-height: 1.65; color: #374151; }}
  a {{ color: #3F6FE0; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  strong {{ color: #1B1E28; }}
  hr {{ border: none; border-top: 1px solid #EEF1FA; margin: 28px 0; }}
  blockquote {{
    background: #F5F8FF;
    border-left: 4px solid #3F6FE0;
    border-radius: 8px;
    padding: 12px 18px;
    margin: 16px 0;
    color: #1B3A86;
    font-size: 14px;
  }}
  code {{
    background: #EEF1FA;
    color: #B7472A;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: "Cascadia Mono", Consolas, monospace;
    font-size: 13px;
  }}
  pre {{
    background: #1B1E28;
    color: #E8ECFB;
    padding: 16px 18px;
    border-radius: 10px;
    overflow-x: auto;
  }}
  pre code {{ background: transparent; color: inherit; padding: 0; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 13.5px;
  }}
  th, td {{ text-align: left; padding: 9px 12px; border-bottom: 1px solid #EEF1FA; }}
  th {{ color: #6B7390; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.4px; }}
  tr:hover td {{ background: #F5F8FF; }}
  ul, ol {{ padding-left: 22px; }}
  li {{ margin: 4px 0; }}
  figure.screenshot {{
    margin: 20px 0;
    text-align: center;
  }}
  figure.screenshot img {{
    max-width: 100%;
    border-radius: 10px;
    border: 1px solid #EEF1FA;
    box-shadow: 0 8px 24px rgba(27, 30, 40, 0.12);
  }}
  figure.screenshot figcaption {{
    font-size: 12.5px;
    color: #90A4AE;
    font-style: italic;
    margin-top: 8px;
  }}
  .footer {{ text-align: center; color: #90A4AE; font-size: 12px; margin-top: 36px; }}
</style>
</head>
<body>
  <div class="hero">
    <div class="icon">🪟 → 🐧</div>
    <h1>Migration Wizard — User Manual</h1>
    <p>Windows 11 to Linux Mint, step by step</p>
  </div>
  <div class="content">
{body}
  </div>
</body>
</html>
"""


def render_user_manual(md_text: str, base_dir: Path | None = None) -> str:
    """Render the full user manual Markdown into a branded standalone HTML page."""
    body = markdown_to_html_body(md_text, base_dir=base_dir)
    return PAGE_TEMPLATE.format(title="Migration Wizard — User Manual", body=body)
