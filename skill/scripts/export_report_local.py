from __future__ import annotations
"""
CLI:
  python3 skill/scripts/export_report_local.py SOURCE.md DEST.pdf [DEST.docx]
"""
import html
import os
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ACCENT = colors.HexColor("#0F4C5C")
ACCENT_DARK = colors.HexColor("#163A5F")
TEXT_DARK = colors.HexColor("#1E293B")
TEXT_MUTED = colors.HexColor("#64748B")
BG_TINT = colors.HexColor("#F1F5F9")
BG_ZEBRA = colors.HexColor("#F8FAFC")
BORDER = colors.HexColor("#CBD5E1")
CODE_COLOR = "#1E40AF"

SEP_ROW_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$")
IMG_RE = re.compile(r"^\x21\[(.*?)\]\((.+?)\)\s*$")
INLINE_RE = re.compile(r"(\*\*([^*]+)\*\*|`([^`]+)`)")


def register_korean_fonts():
    home_fonts = os.path.expanduser("~/Library/Fonts")
    regular_candidates = [
        os.path.join(home_fonts, "Pretendard-Regular.ttf"),
        "/Library/Fonts/Pretendard-Regular.ttf",
        os.path.join(home_fonts, "NanumGothic.ttf"),
        "/Library/Fonts/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    bold_candidates = [
        os.path.join(home_fonts, "Pretendard-Bold.ttf"),
        "/Library/Fonts/Pretendard-Bold.ttf",
        os.path.join(home_fonts, "NanumGothicBold.ttf"),
        "/Library/Fonts/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    ]

    reg_path = None
    bold_path = None

    for path in regular_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("KorReg", path))
                reg_path = path
                break
            except Exception:
                continue

    if not reg_path:
        raise RuntimeError("시스템에서 한글 TTF 폰트를 찾지 못했습니다.")

    for path in bold_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("KorBold", path))
                bold_path = path
                break
            except Exception:
                continue

    bold_name = "KorBold" if bold_path else "KorReg"
    pdfmetrics.registerFontFamily(
        "Korean",
        normal="KorReg",
        bold=bold_name,
        italic="KorReg",
        boldItalic=bold_name,
    )
    print(f"Fonts loaded -> Regular: {reg_path} | Bold: {bold_path or '(Regular fallback)'}")
    return "KorReg", bold_name, bool(bold_path)


def inline_md_to_rl(text: str, has_bold: bool) -> str:
    escaped = html.escape(text.strip(), quote=False)

    def repl(m):
        if m.group(2) is not None:
            inner = m.group(2)
            if has_bold:
                return f"<b>{inner}</b>"
            return f'<font color="#0F4C5C"><b>{inner}</b></font>'
        inner = m.group(3)
        return f'<font color="{CODE_COLOR}">{inner}</font>'

    return INLINE_RE.sub(repl, escaped)


def strip_md_inline(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def resolve_image(source_dir: Path, raw_path: str) -> Path | None:
    p = (source_dir / raw_path).resolve()
    if p.is_file():
        return p
    alt = (source_dir.parent / raw_path.lstrip("./")).resolve()
    if alt.is_file():
        return alt
    return None


def split_table_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def parse_markdown(md_text: str):
    lines = md_text.splitlines()
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if re.match(r"^-{3,}\s*$", stripped):
            blocks.append(("hr", None))
            i += 1
            continue

        if stripped.startswith("# "):
            blocks.append(("h1", stripped[2:].strip()))
            i += 1
            continue

        if stripped.startswith("## "):
            blocks.append(("h2", stripped[3:].strip()))
            i += 1
            continue

        if stripped.startswith("### "):
            blocks.append(("h3", stripped[4:].strip()))
            i += 1
            continue

        if "|" in stripped and i + 1 < n and SEP_ROW_RE.match(lines[i + 1].strip()):
            header = split_table_row(lines[i])
            rows = []
            i += 2
            while i < n and lines[i].strip() and "|" in lines[i]:
                if not SEP_ROW_RE.match(lines[i].strip()):
                    row = split_table_row(lines[i])
                    if len(row) < len(header):
                        row += [""] * (len(header) - len(row))
                    rows.append(row[: len(header)])
                i += 1
            blocks.append(("table", (header, rows)))
            continue

        m_img = IMG_RE.match(stripped)
        if m_img:
            blocks.append(("image", (m_img.group(1).strip(), m_img.group(2).strip())))
            i += 1
            continue

        m_ul = re.match(r"^(\s*)[-*]\s+(.+)$", line)
        if m_ul:
            level = 2 if len(m_ul.group(1)) >= 2 else 1
            blocks.append(("bullet", (level, m_ul.group(2).strip())))
            i += 1
            continue

        m_ol = re.match(r"^(\s*)(\d+)\.\s+(.+)$", line)
        if m_ol:
            blocks.append(("ol", (m_ol.group(2), m_ol.group(3).strip())))
            i += 1
            continue

        para_lines = [line]
        i += 1
        while i < n:
            nxt = lines[i]
            nxt_s = nxt.strip()
            if (
                not nxt_s
                or nxt_s.startswith("#")
                or re.match(r"^-{3,}\s*$", nxt_s)
                or IMG_RE.match(nxt_s)
                or re.match(r"^(\s*)[-*]\s+", nxt)
                or re.match(r"^(\s*)\d+\.\s+", nxt)
                or ("|" in nxt_s and i + 1 < n and SEP_ROW_RE.match(lines[i + 1].strip()))
            ):
                break
            para_lines.append(nxt)
            i += 1

        blocks.append(("para", para_lines))

    return blocks


def compute_col_widths(header: list[str], rows: list[list[str]], avail_w: float) -> list[float]:
    ncols = len(header)
    min_w = min(13 * mm, avail_w / ncols)

    def visual_len(s: str) -> float:
        plain = strip_md_inline(s)
        total = 0.0
        for ch in plain:
            total += 1.75 if ord(ch) > 127 else 0.95
        return total

    weights = []
    for c in range(ncols):
        h_text = strip_md_inline(header[c])
        h_len = visual_len(h_text)
        cell_lens = [visual_len(r[c]) for r in rows] or [h_len]
        avg_len = sum(cell_lens) / len(cell_lens)
        max_len = max(cell_lens)
        score = max(h_len * 0.95, avg_len * 0.7 + max_len * 0.3)

        if "순위" in h_text:
            score = 8.0
        elif any(k in h_text for k in ("CAS", "온도(K)", "온도(°C)", "score", "ASKCOS 온도")):
            score = max(min(score, 17.5), 14.5)
        elif any(k in h_text for k in ("역할", "실행")):
            score = max(min(score, 22.0), 17.5)
        elif any(k in h_text for k in ("저장소", "화학 검토", "성분", "종료 상태")):
            score = max(score, 32.0)

        weights.append(max(score, 6.0))

    total_wt = sum(weights)
    widths = [max(min_w, avail_w * (w / total_wt)) for w in weights]

    diff = sum(widths) - avail_w
    if abs(diff) > 0.1:
        flex = [max(0.0, w - min_w) for w in widths]
        flex_sum = sum(flex)
        if flex_sum > 0:
            widths = [w - diff * (f / flex_sum) for w, f in zip(widths, flex)]
        else:
            widths = [avail_w / ncols] * ncols
    return widths


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(total)
            super().showPage()
        super().save()

    def draw_footer(self, total_pages: int):
        page_num = self._pageNumber
        w, _ = A4
        self.saveState()
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.5)
        self.line(18 * mm, 13 * mm, w - 18 * mm, 13 * mm)
        self.setFont("KorReg", 8)
        self.setFillColor(TEXT_MUTED)
        self.drawString(18 * mm, 9 * mm, "아세트아미노펜 AI 유기합성 최종 보고서")
        self.drawRightString(w - 18 * mm, 9 * mm, f"{page_num} / {total_pages}")
        self.restoreState()


def build_pdf(blocks, source_dir: Path, dest_pdf: Path):
    reg_font, bold_font, has_bold = register_korean_fonts()
    avail_w = A4[0] - 36 * mm

    styles = {
        "h1": ParagraphStyle(
            "H1", fontName=bold_font, fontSize=17, leading=23,
            textColor=ACCENT_DARK, spaceAfter=6, keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2", fontName=bold_font, fontSize=12.5, leading=18,
            textColor=ACCENT, spaceBefore=13, spaceAfter=5, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3", fontName=bold_font, fontSize=10.5, leading=15,
            textColor=ACCENT_DARK, spaceBefore=9, spaceAfter=3, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", fontName=reg_font, fontSize=9.4, leading=14.6,
            textColor=TEXT_DARK, spaceAfter=4.0,
        ),
        "meta": ParagraphStyle(
            "Meta", fontName=reg_font, fontSize=9.0, leading=13.8,
            textColor=TEXT_DARK, spaceAfter=1.5,
        ),
        "summary": ParagraphStyle(
            "Summary", fontName=reg_font, fontSize=9.3, leading=14.8,
            textColor=TEXT_DARK, spaceAfter=0,
        ),
        "b1": ParagraphStyle(
            "Bullet1", fontName=reg_font, fontSize=9.3, leading=14.3,
            textColor=TEXT_DARK, leftIndent=12, firstLineIndent=-8,
            spaceAfter=2.2,
        ),
        "b1_keep": ParagraphStyle(
            "Bullet1Keep", fontName=bold_font, fontSize=9.3, leading=14.0,
            textColor=ACCENT_DARK, leftIndent=0, spaceBefore=5, spaceAfter=3,
            keepWithNext=True,
        ),
        "b2": ParagraphStyle(
            "Bullet2", fontName=reg_font, fontSize=9.0, leading=13.8,
            textColor=TEXT_DARK, leftIndent=22, firstLineIndent=-8,
            spaceAfter=1.8,
        ),
        "ol": ParagraphStyle(
            "OL", fontName=reg_font, fontSize=9.3, leading=14.3,
            textColor=TEXT_DARK, leftIndent=14, firstLineIndent=-10,
            spaceAfter=2.2,
        ),
        "caption": ParagraphStyle(
            "Caption", fontName=reg_font, fontSize=8.4, leading=12,
            textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=3, spaceAfter=8,
        ),
        "th": ParagraphStyle(
            "TH", fontName=bold_font, fontSize=8.2, leading=11.2,
            textColor=colors.white, alignment=TA_LEFT, wordWrap="CJK",
        ),
        "td": ParagraphStyle(
            "TD", fontName=reg_font, fontSize=8.0, leading=11.3,
            textColor=TEXT_DARK, alignment=TA_LEFT, wordWrap="CJK",
        ),
        "td_small": ParagraphStyle(
            "TDSmall", fontName=reg_font, fontSize=7.4, leading=10.5,
            textColor=TEXT_DARK, alignment=TA_LEFT, wordWrap="CJK",
        ),
    }

    def make_image_flowable(caption: str, raw_path: str):
        img_path = resolve_image(source_dir, raw_path)
        if not img_path:
            raise FileNotFoundError(f"이미지 파일 없음: {raw_path} (기준: {source_dir})")
        iw, ih = ImageReader(str(img_path)).getSize()
        name_l = img_path.name.lower()
        if "forward_reaction_scheme" in name_l:
            max_w, max_h = 166 * mm, 54 * mm
        elif "_cpk" in name_l or "_stick" in name_l:
            max_w, max_h = 148 * mm, 88 * mm
        else:
            max_w, max_h = 74 * mm, 48 * mm
        scale = min(max_w / iw, max_h / ih)
        img = Image(str(img_path), width=iw * scale, height=ih * scale)
        img.hAlign = "CENTER"
        cap = Paragraph(html.escape(caption, quote=False), styles["caption"])
        return [img, cap]

    story = []
    idx = 0
    total_blocks = len(blocks)
    in_summary = False

    while idx < total_blocks:
        kind, payload = blocks[idx]

        if kind == "h1":
            story.append(Paragraph(inline_md_to_rl(payload, has_bold), styles["h1"]))
            story.append(HRFlowable(width="100%", thickness=1.4, color=ACCENT, spaceBefore=0, spaceAfter=7))
            if idx + 1 < total_blocks and blocks[idx + 1][0] == "para":
                meta_lines = blocks[idx + 1][1]
                if any("SMILES" in l or "대상 분자" in l for l in meta_lines):
                    meta_html = "<br/>".join(inline_md_to_rl(l, has_bold) for l in meta_lines)
                    card = Table([[Paragraph(meta_html, styles["meta"])]], colWidths=[avail_w])
                    card.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), BG_ZEBRA),
                        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]))
                    story.append(card)
                    story.append(Spacer(1, 6))
                    idx += 2
                    continue
            idx += 1
            continue

        if kind == "hr":
            in_summary = False
            story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=5, spaceAfter=4))
            idx += 1
            continue

        if kind == "h2":
            in_summary = (payload.strip() == "요약")
            story.append(Paragraph(inline_md_to_rl(payload, has_bold), styles["h2"]))
            idx += 1
            continue

        if kind == "h3":
            in_summary = False
            story.append(Paragraph(inline_md_to_rl(payload, has_bold), styles["h3"]))
            idx += 1
            continue

        if kind == "para":
            joined = "<br/>".join(inline_md_to_rl(l, has_bold) for l in payload)
            if in_summary:
                box = Table([[Paragraph(joined, styles["summary"])]], colWidths=[avail_w])
                box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), BG_TINT),
                    ("LINEBEFORE", (0, 0), (0, -1), 3.0, ACCENT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(box)
                story.append(Spacer(1, 5))
                in_summary = False
            else:
                st_p = styles["body"]
                if (
                    len(payload) == 1
                    and len(payload[0].strip()) <= 30
                    and idx + 1 < total_blocks
                    and blocks[idx + 1][0] in ("image", "bullet", "table")
                ):
                    st_p = ParagraphStyle("BodyKeep", parent=styles["body"], keepWithNext=True)
                story.append(Paragraph(joined, st_p))
            idx += 1
            continue

        if kind == "bullet":
            level, text = payload
            if idx + 1 < total_blocks and blocks[idx + 1][0] == "image":
                cap, raw_p = blocks[idx + 1][1]
                lbl = Paragraph(f"■ {inline_md_to_rl(text, has_bold)}", styles["b1_keep"])
                story.append(KeepTogether([lbl] + make_image_flowable(cap, raw_p)))
                idx += 2
                continue
            prefix = "• " if level == 1 else "– "
            st = styles["b1"] if level == 1 else styles["b2"]
            story.append(Paragraph(prefix + inline_md_to_rl(text, has_bold), st))
            idx += 1
            continue

        if kind == "ol":
            num, text = payload
            story.append(Paragraph(f"{num}. {inline_md_to_rl(text, has_bold)}", styles["ol"]))
            idx += 1
            continue

        if kind == "image":
            cap, raw_p = payload
            story.append(KeepTogether(make_image_flowable(cap, raw_p)))
            idx += 1
            continue

        if kind == "table":
            header, rows = payload
            ncols = len(header)
            col_widths = compute_col_widths(header, rows, avail_w)
            td_style = styles["td_small"] if ncols >= 6 else styles["td"]

            t_data = [[Paragraph(inline_md_to_rl(h, has_bold), styles["th"]) for h in header]]
            for r in rows:
                t_data.append([Paragraph(inline_md_to_rl(c, has_bold), td_style) for c in r])

            tbl = Table(t_data, colWidths=col_widths, repeatRows=1)
            t_style = [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEABOVE", (0, 0), (-1, 0), 1.1, ACCENT),
                ("LINEBELOW", (0, 0), (-1, 0), 0.9, ACCENT),
                ("LINEBELOW", (0, 1), (-1, -2), 0.4, BORDER),
                ("LINEBELOW", (0, -1), (-1, -1), 1.0, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
            for r_i in range(1, len(t_data)):
                if r_i % 2 == 0:
                    t_style.append(("BACKGROUND", (0, r_i), (-1, r_i), BG_ZEBRA))
            if len(t_data) >= 2:
                t_style.append(("NOSPLIT", (0, 0), (-1, 1)))
            tbl.setStyle(TableStyle(t_style))
            story.append(Spacer(1, 3))
            story.append(tbl)
            story.append(Spacer(1, 6))
            idx += 1
            continue

        idx += 1

    doc = SimpleDocTemplate(
        str(dest_pdf),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="아세트아미노펜 최종 보고서",
    )
    doc.build(story, canvasmaker=NumberedCanvas)


def _set_run_font(run, font_name="Pretendard", size_pt=9.4, rgb=(30, 41, 59), bold=False):
    run.bold = bold
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.font.color.rgb = RGBColor(*rgb)
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), font_name)


def _add_inline_runs(para, text: str, font_name="Pretendard", font_size=9.4, base_rgb=(30, 41, 59), force_bold=False):
    pos = 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            r = para.add_run(text[pos : m.start()])
            _set_run_font(r, font_name, font_size, base_rgb, bold=force_bold)
        if m.group(2) is not None:
            r = para.add_run(m.group(2))
            _set_run_font(r, font_name, font_size, base_rgb, bold=True)
        else:
            r = para.add_run(m.group(3))
            _set_run_font(r, font_name, font_size - 0.2, (30, 64, 175), bold=force_bold)
        pos = m.end()
    if pos < len(text):
        r = para.add_run(text[pos:])
        _set_run_font(r, font_name, font_size, base_rgb, bold=force_bold)


def _set_cell_shading(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for side, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_cell_borders(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side, cfg in kwargs.items():
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), cfg.get("val", "none"))
        if cfg.get("val", "none") != "none":
            b.set(qn("w:sz"), str(cfg.get("sz", 4)))
            b.set(qn("w:space"), "0")
            b.set(qn("w:color"), cfg.get("color", "CBD5E1"))
        tcBorders.append(b)
    tcPr.append(tcBorders)


def _set_table_borders(tbl, top_color="0F4C5C", bottom_color="0F4C5C", inside_h="CBD5E1"):
    tblPr = tbl._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    specs = {
        "top": ("single", 10, top_color),
        "bottom": ("single", 10, bottom_color),
        "insideH": ("single", 4, inside_h),
        "left": ("none", 0, "auto"),
        "right": ("none", 0, "auto"),
        "insideV": ("none", 0, "auto"),
    }
    for side, (val, sz, color) in specs.items():
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), val)
        if val != "none":
            el.set(qn("w:sz"), str(sz))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def _set_para_bottom_border(para, color="0F4C5C", sz=10):
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(sz))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_field(para, field_name: str):
    r = para.add_run()
    _set_run_font(r, "Pretendard", 8.0, (100, 116, 139))
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {field_name} "
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "separate")
    fld3 = OxmlElement("w:fldChar")
    fld3.set(qn("w:fldCharType"), "end")
    r._r.extend([fld1, instr, fld2, fld3])


def build_docx(blocks, source_dir: Path, dest_docx: Path):
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement as _OxmlElement
    from docx.oxml.ns import qn as _qn
    from docx.shared import Inches, Mm, Pt as _Pt, RGBColor as _RGBColor

    globals().update({"OxmlElement": _OxmlElement, "qn": _qn, "Pt": _Pt, "RGBColor": _RGBColor})

    doc = Document()
    doc.styles['Normal'].font.size = _Pt(9.2)
    avail_w_pt = A4[0] - 36 * mm
    avail_w_in = avail_w_pt / 72.0

    for sec in doc.sections:
        sec.page_width = Mm(210)
        sec.page_height = Mm(297)
        sec.top_margin = Mm(16)
        sec.bottom_margin = Mm(16)
        sec.left_margin = Mm(18)
        sec.right_margin = Mm(18)
        sec.footer_distance = Mm(9)

        # 하단 바닥글 (PDF와 동일: 좌측 보고서 제목 / 우측 쪽번호)
        footer = sec.footer
        fp = footer.paragraphs[0]
        fp.paragraph_format.space_before = _Pt(0)
        fp.paragraph_format.space_after = _Pt(0)
        fp.paragraph_format.line_spacing = _Pt(1)
        ftbl = footer.add_table(rows=1, cols=2, width=Inches(avail_w_in))
        ftbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(ftbl, top_color="CBD5E1", bottom_color="auto", inside_h="auto")
        # 하단 선 제거
        for side in ("bottom", "insideH"):
            el = ftbl._tbl.tblPr.find(qn("w:tblBorders")).find(qn(f"w:{side}"))
            if el is not None:
                el.set(qn("w:val"), "none")
        c_left, c_right = ftbl.rows[0].cells
        c_left.width = Inches(avail_w_in * 0.75)
        c_right.width = Inches(avail_w_in * 0.25)
        _set_cell_margins(c_left, top=40, bottom=0, left=0, right=0)
        _set_cell_margins(c_right, top=40, bottom=0, left=0, right=0)
        pl = c_left.paragraphs[0]
        pl.paragraph_format.space_after = _Pt(0)
        rl = pl.add_run("아세트아미노펜 AI 유기합성 최종 보고서")
        _set_run_font(rl, "Pretendard", 8.0, (100, 116, 139))
        pr = c_right.paragraphs[0]
        pr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        pr.paragraph_format.space_after = _Pt(0)
        _add_field(pr, "PAGE")
        r_sep = pr.add_run(" / ")
        _set_run_font(r_sep, "Pretendard", 8.0, (100, 116, 139))
        _add_field(pr, "NUMPAGES")

    def add_image_block(caption: str, raw_path: str):
        img_path = resolve_image(source_dir, raw_path)
        if not img_path:
            raise FileNotFoundError(f"DOCX 이미지 파일 없음: {raw_path}")
        iw, ih = ImageReader(str(img_path)).getSize()
        name_l = img_path.name.lower()
        if "forward_reaction_scheme" in name_l:
            max_w_in, max_h_in = 166 * mm / 72.0, 54 * mm / 72.0
        elif "_cpk" in name_l or "_stick" in name_l:
            max_w_in, max_h_in = 142 * mm / 72.0, 80 * mm / 72.0
        else:
            max_w_in, max_h_in = 70 * mm / 72.0, 44 * mm / 72.0
        scale = min(max_w_in / iw, max_h_in / ih)
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = _Pt(2)
        p_img.paragraph_format.space_after = _Pt(2)
        p_img.paragraph_format.keep_with_next = True
        p_img.add_run().add_picture(str(img_path), width=Inches(iw * scale))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = _Pt(0)
        p_cap.paragraph_format.space_after = _Pt(4)
        r = p_cap.add_run(caption)
        _set_run_font(r, "Pretendard", 8.4, (100, 116, 139))

    idx = 0
    total_blocks = len(blocks)
    in_summary = False

    while idx < total_blocks:
        kind, payload = blocks[idx]

        if kind == "h1":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = _Pt(0)
            p.paragraph_format.space_after = _Pt(6)
            p.paragraph_format.keep_with_next = True
            _set_para_bottom_border(p, color="0F4C5C", sz=12)
            r = p.add_run(strip_md_inline(payload))
            _set_run_font(r, "Pretendard", 17, (22, 58, 95), bold=True)

            if idx + 1 < total_blocks and blocks[idx + 1][0] == "para":
                meta_lines = blocks[idx + 1][1]
                if any("SMILES" in l or "대상 분자" in l for l in meta_lines):
                    card = doc.add_table(rows=1, cols=1)
                    card.alignment = WD_TABLE_ALIGNMENT.CENTER
                    card.autofit = False
                    cell = card.rows[0].cells[0]
                    cell.width = Inches(avail_w_in)
                    _set_cell_shading(cell, "F8FAFC")
                    _set_cell_margins(cell, top=90, bottom=90, left=140, right=140)
                    _set_cell_borders(
                        cell,
                        top={"val": "single", "sz": 4, "color": "CBD5E1"},
                        bottom={"val": "single", "sz": 4, "color": "CBD5E1"},
                        left={"val": "single", "sz": 4, "color": "CBD5E1"},
                        right={"val": "single", "sz": 4, "color": "CBD5E1"},
                    )
                    cp = cell.paragraphs[0]
                    cp.paragraph_format.space_after = _Pt(0)
                    cp.paragraph_format.line_spacing = _Pt(12.5)
                    for i_l, line in enumerate(meta_lines):
                        if i_l > 0:
                            cp.add_run().add_break()
                        _add_inline_runs(cp, line.strip(), font_size=9.0)
                    sp = doc.add_paragraph()
                    sp.paragraph_format.space_before = _Pt(0)
                    sp.paragraph_format.space_after = _Pt(2)
                    sp.paragraph_format.line_spacing = _Pt(2)
                    idx += 2
                    continue
            idx += 1
            continue

        if kind == "hr":
            in_summary = False
            p = doc.add_paragraph()
            p.paragraph_format.space_before = _Pt(3)
            p.paragraph_format.space_after = _Pt(4)
            p.paragraph_format.line_spacing = _Pt(2)
            _set_para_bottom_border(p, color="CBD5E1", sz=4)
            idx += 1
            continue

        if kind == "h2":
            in_summary = (payload.strip() == "요약")
            p = doc.add_paragraph()
            p.paragraph_format.space_before = _Pt(9)
            p.paragraph_format.space_after = _Pt(4)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(strip_md_inline(payload))
            _set_run_font(r, "Pretendard", 12.5, (15, 76, 92), bold=True)
            idx += 1
            continue

        if kind == "h3":
            in_summary = False
            p = doc.add_paragraph()
            p.paragraph_format.space_before = _Pt(8)
            p.paragraph_format.space_after = _Pt(3)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(strip_md_inline(payload))
            _set_run_font(r, "Pretendard", 10.5, (22, 58, 95), bold=True)
            idx += 1
            continue

        if kind == "para":
            if in_summary:
                box = doc.add_table(rows=1, cols=1)
                box.alignment = WD_TABLE_ALIGNMENT.CENTER
                box.autofit = False
                cell = box.rows[0].cells[0]
                cell.width = Inches(avail_w_in)
                _set_cell_shading(cell, "F1F5F9")
                _set_cell_margins(cell, top=110, bottom=110, left=160, right=140)
                _set_cell_borders(
                    cell,
                    left={"val": "single", "sz": 24, "color": "0F4C5C"},
                    top={"val": "none"},
                    bottom={"val": "none"},
                    right={"val": "none"},
                )
                bp = cell.paragraphs[0]
                bp.paragraph_format.space_after = _Pt(0)
                bp.paragraph_format.line_spacing = _Pt(13.5)
                for i_l, line in enumerate(payload):
                    if i_l > 0:
                        bp.add_run().add_break()
                    _add_inline_runs(bp, line.strip(), font_size=9.3)
                sp = doc.add_paragraph()
                sp.paragraph_format.space_before = _Pt(0)
                sp.paragraph_format.space_after = _Pt(2)
                sp.paragraph_format.line_spacing = _Pt(2)
                in_summary = False
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = _Pt(4)
                p.paragraph_format.line_spacing = _Pt(13.5)
                if (
                    len(payload) == 1
                    and len(payload[0].strip()) <= 30
                    and idx + 1 < total_blocks
                    and blocks[idx + 1][0] in ("image", "bullet", "table")
                ):
                    p.paragraph_format.keep_with_next = True
                for i_l, line in enumerate(payload):
                    if i_l > 0:
                        p.add_run().add_break()
                    _add_inline_runs(p, line.strip(), font_size=9.4)
            idx += 1
            continue

        if kind == "bullet":
            level, text = payload
            if idx + 1 < total_blocks and blocks[idx + 1][0] == "image":
                cap, raw_p = blocks[idx + 1][1]
                p = doc.add_paragraph()
                p.paragraph_format.space_before = _Pt(5)
                p.paragraph_format.space_after = _Pt(2)
                p.paragraph_format.keep_with_next = True
                _add_inline_runs(p, "■ " + text, font_size=9.3, base_rgb=(22, 58, 95), force_bold=True)
                add_image_block(cap, raw_p)
                idx += 2
                continue
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.18 if level == 1 else 0.34)
            p.paragraph_format.first_line_indent = Inches(-0.12)
            p.paragraph_format.space_after = _Pt(2.2)
            p.paragraph_format.line_spacing = _Pt(13.0)
            prefix = "• " if level == 1 else "– "
            _add_inline_runs(p, prefix + text, font_size=9.3 if level == 1 else 9.0)
            idx += 1
            continue

        if kind == "ol":
            num, text = payload
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.20)
            p.paragraph_format.first_line_indent = Inches(-0.14)
            p.paragraph_format.space_after = _Pt(2.2)
            p.paragraph_format.line_spacing = _Pt(13.0)
            _add_inline_runs(p, f"{num}. {text}", font_size=9.3)
            idx += 1
            continue

        if kind == "image":
            cap, raw_p = payload
            add_image_block(cap, raw_p)
            idx += 1
            continue

        if kind == "table":
            header, rows = payload
            ncols = len(header)
            col_widths_pt = compute_col_widths(header, rows, avail_w_pt)
            td_size = 7.6 if ncols >= 6 else 8.1

            tbl = doc.add_table(rows=1 + len(rows), cols=ncols)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            tbl.autofit = False
            tblLayout = OxmlElement("w:tblLayout")
            tblLayout.set(qn("w:type"), "fixed")
            tbl._tbl.tblPr.append(tblLayout)
            _set_table_borders(tbl)

            hdr_trPr = tbl.rows[0]._tr.get_or_add_trPr()
            hdr_trPr.append(_OxmlElement("w:tblHeader"))
            hdr_trPr.append(_OxmlElement("w:cantSplit"))

            for c_i, h_text in enumerate(header):
                w_in = Inches(col_widths_pt[c_i] / 72.0)
                cell = tbl.rows[0].cells[c_i]
                cell.width = w_in
                _set_cell_shading(cell, "0F4C5C")
                _set_cell_margins(cell, top=55, bottom=55, left=75, right=75)
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = _Pt(0)
                p.paragraph_format.line_spacing = _Pt(10.5)
                r = p.add_run(strip_md_inline(h_text))
                _set_run_font(r, "Pretendard", 8.2, (255, 255, 255), bold=True)

            for r_i, row_data in enumerate(rows, start=1):
                trPr = tbl.rows[r_i]._tr.get_or_add_trPr()
                trPr.append(_OxmlElement("w:cantSplit"))
                for c_i, val in enumerate(row_data):
                    w_in = Inches(col_widths_pt[c_i] / 72.0)
                    cell = tbl.rows[r_i].cells[c_i]
                    cell.width = w_in
                    if r_i % 2 == 0:
                        _set_cell_shading(cell, "F8FAFC")
                    _set_cell_margins(cell, top=50, bottom=50, left=75, right=75)
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_after = _Pt(0)
                    p.paragraph_format.line_spacing = _Pt(10.6)
                    _add_inline_runs(p, val, font_size=td_size)

            sp = doc.add_paragraph()
            sp.paragraph_format.space_before = _Pt(0)
            sp.paragraph_format.space_after = _Pt(2)
            sp.paragraph_format.line_spacing = _Pt(2)
            idx += 1
            continue

        idx += 1

    doc.save(str(dest_docx))


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 export_report_local.py SOURCE.md DEST.pdf [DEST.docx]", file=sys.stderr)
        sys.exit(1)

    source_md = Path(sys.argv[1]).resolve()
    dest_pdf = Path(sys.argv[2]).resolve()
    dest_docx = Path(sys.argv[3]).resolve() if len(sys.argv) >= 4 else None

    md_text = source_md.read_text(encoding="utf-8")
    blocks = parse_markdown(md_text)

    dest_pdf.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(blocks, source_md.parent, dest_pdf)
    print(f"PDF generated: {dest_pdf}")

    if dest_docx:
        dest_docx.parent.mkdir(parents=True, exist_ok=True)
        build_docx(blocks, source_md.parent, dest_docx)
        print(f"DOCX generated: {dest_docx}")


if __name__ == "__main__":
    main()
