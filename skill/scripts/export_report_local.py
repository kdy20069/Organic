#!/usr/bin/env python3
"""
Markdown -> DOCX -> PDF 렌더러 (단일 스크립트, CLI 인자 기반)
- pandoc가 있고 LibreOffice(soffice/libreoffice)가 있으면 pandoc DOCX -> LibreOffice PDF
- pandoc가 없으면 python-docx DOCX 생성, 이어서 LibreOffice PDF 변환 가능하면 변환
- pandoc/LibreOffice 모두 없으면 ReportLab PDF 직접 생성 (한글 폰트 자동 등록)
- CLI: export_report_local.py SOURCE.md DEST.pdf [DEST.docx]
"""
import os
import sys
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from reportlab.lib.colors import HexColor
from pypdf import PdfReader, PdfWriter
from io import BytesIO
from reportlab.pdfgen import canvas as canvas_mod

SOURCE_MD = sys.argv[1] if len(sys.argv) > 1 else ""
DEST_PDF = sys.argv[2] if len(sys.argv) > 2 else ""
DEST_DOCX = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2].endswith(".pdf") else None

if not SOURCE_MD or not DEST_PDF:
    print("사용법: export_report_local.py SOURCE.md DEST.pdf [DEST.docx]")
    sys.exit(2)

SOURCE_DIR = os.path.dirname(os.path.abspath(SOURCE_MD))
RESOURCE_DIR = SOURCE_DIR
def _resolve_image(path):
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(RESOURCE_DIR, path))


def cmd_exists(name):
    return shutil.which(name) is not None


def page_count_pdf(pdf_path):
    if cmd_exists("pdfinfo"):
        out = subprocess.check_output(["pdfinfo", pdf_path], text=True)
        m = re.search(r"Pages:\s+(\d+)", out)
        if m:
            return int(m.group(1))
    try:
        import pypdf
        return len(pypdf.PdfReader(pdf_path).pages)
    except Exception:
        return None


def _md_to_text_plain(s):
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s


def _md_to_text_plain_for_pdf(s):
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s


def pandoc_to_docx(src_md, dst_docx):
    cmd = ["pandoc", "--from=gfm", "--resource-path", SOURCE_DIR, src_md, "--output", dst_docx]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst_docx) or os.path.getsize(dst_docx) == 0:
        raise RuntimeError("pandoc 실패: " + r.stderr[-1000:])
    return dst_docx


def soffice_to_pdf(docx_path, out_dir):
    office = shutil.which("soffice") or shutil.which("libreoffice")
    if not office:
        raise RuntimeError("LibreOffice(soffice/libreoffice)가 없습니다")
    subprocess.run([office, "--headless", "--convert-to", "pdf", "--outdir", out_dir, docx_path],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf_path = os.path.join(out_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        raise RuntimeError("LibreOffice가 비어 있는 PDF를 생성했습니다")
    return pdf_path


def build_docx_python(src_md, dst_docx):
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Arial Unicode MS"
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:ascii'), 'Arial Unicode MS')
    rfonts.set(qn('w:hAnsi'), 'Arial Unicode MS')
    rfonts.set(qn('w:eastAsia'), 'Arial Unicode MS')
    rfonts.set(qn('w:cs'), 'Arial Unicode MS')
    style.font.size = Pt(11)

    def _table_save(table, headers, body, ncols):
        from docx.oxml.ns import qn as _qn
        table.style = "Light List Accent 1"
        for i, h in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(_md_to_text_plain(h))
            run.font.size = Pt(9)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            _shade_cell(cell._element, "1B4F72")
        for r_idx, row in enumerate(body):
            for c_idx in range(0, min(ncols, len(row))):
                cell = table.cell(r_idx + 1, c_idx)
                cell.text = ""
                p = cell.paragraphs[0]
                run = p.add_run(_md_to_text_plain(row[c_idx]))
                run.font.size = Pt(9)
                if r_idx % 2 == 1:
                    _shade_cell(cell._element, "F7F9FC")
        _adjust_table_borders(table)

    def _shade_cell(cell_elem, color_hex):
        tcPr = cell_elem.find(qn('w:tcPr'))
        if tcPr is None:
            tcPr = OxmlElement('w:tcPr')
            cell_elem.insert(0, tcPr)
        shd = tcPr.find(qn('w:shd'))
        if shd is None:
            shd = OxmlElement('w:shd')
            tcPr.append(shd)
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), color_hex)

    def _adjust_table_borders(table):
        tbl = table._element
        tblPr = tbl.find(qn('w:tblPr'))
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl.insert(0, tblPr)
        tblBorders = tblPr.find(qn('w:tblBorders'))
        if tblBorders is not None:
            tblPr.remove(tblBorders)
        tblBorders = OxmlElement('w:tblBorders')
        for edge in ('top', 'bottom', 'insideH', 'insideV', 'left', 'right'):
            border = OxmlElement(f'w:{edge}')
            if edge in ('top', 'bottom'):
                border.set(qn('w:val'), 'single')
                border.set(qn('w:sz'), '12')
                border.set(qn('w:space'), '0')
                border.set(qn('w:color'), '1B4F72')
            elif edge == 'insideH':
                border.set(qn('w:val'), 'single')
                border.set(qn('w:sz'), '6')
                border.set(qn('w:space'), '0')
                border.set(qn('w:color'), 'D5DCE4')
            else:
                border.set(qn('w:val'), 'nil')
            tblBorders.append(border)
        tblPr.append(tblBorders)
        tblCellMar = OxmlElement('w:tblCellMar')
        for edge in ('top', 'bottom', 'left', 'right'):
            margin = OxmlElement(f'w:{edge}')
            if edge in ('top', 'bottom'):
                margin.set(qn('w:w'), '9')
                margin.set(qn('w:type'), 'dxa')
            else:
                margin.set(qn('w:w'), '10')
                margin.set(qn('w:type'), 'dxa')
            tblCellMar.append(margin)
        tblPr.append(tblCellMar)

    def get_md_bold_sub_runs(text):
        runs = []
        parts = re.split(r"(\*\*[^*]+\*\*)", text)
        for p in parts:
            if p.startswith("**") and p.endswith("**") and len(p) >= 4:
                inner = p[2:-2]
                runs.append((inner, True))
            else:
                runs.append((p, False))
        return runs

    def escape_xml(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def get_or_add_pPr(p_elem):
        pPr = p_elem.find(qn('w:pPr'))
        if pPr is None:
            pPr = OxmlElement('w:pPr')
            p_elem.insert(0, pPr)
        return pPr

    def _adjust_summary_box(pPr):
        shd = pPr.find(qn('w:shd'))
        if shd is None:
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear')
            shd.set(qn('w:color'), 'auto')
            shd.set(qn('w:fill'), 'F2F6FA')
            pPr.append(shd)
        pBdr = pPr.find(qn('w:pBdr'))
        if pBdr is None:
            pBdr = OxmlElement('w:pBdr')
            pPr.append(pBdr)
        left = pBdr.find(qn('w:left'))
        if left is None:
            left = OxmlElement('w:left')
            pBdr.append(left)
        left.set(qn('w:val'), 'single')
        left.set(qn('w:sz'), '24')
        left.set(qn('w:space'), '4')
        left.set(qn('w:color'), '1B4F72')

    in_summary = False

    def add_md_line(text):
        text = text.rstrip("\n")
        if not text:
            return
        if text.lstrip().startswith("#"):
            level = min(6, len(text) - len(text.lstrip("#")))
            color_map = {1: RGBColor(0x16, 0x3A, 0x5F), 2: RGBColor(0x1B, 0x4F, 0x72), 3: RGBColor(0x2C, 0x3E, 0x50)}
            h = doc.add_heading(text.lstrip("# ").strip(), level=level)
            for run in h.runs:
                run.font.color.rgb = color_map.get(level, RGBColor(0x1B, 0x4F, 0x72))
            return
        if text.startswith("!["):
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", text.strip())
            if m:
                caption, path = m.group(1), m.group(2)
                full = _resolve_image(path)
                if os.path.exists(full):
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = p.add_run()
                    run.add_picture(full, width=Inches(4.2))
                    cap = doc.add_paragraph()
                    cr = cap.add_run(caption)
                    cr.italic = True
                    cr.font.size = Pt(9)
                    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p = doc.add_paragraph()
                    p.add_run(f"[이미지 없음: {path}]").bold = True
            return
        if _is_standalone_hr(text):
            doc.add_paragraph()
            return
        p = doc.add_paragraph()
        if in_summary and re.match(r'^report/report\.md', src_md):
            p_adj = get_or_add_pPr(p._element)
            shd = OxmlElement('w:shd')
            shd.set(qn('w:val'), 'clear')
            shd.set(qn('w:color'), 'auto')
            shd.set(qn('w:fill'), 'F2F6FA')
            p_adj.append(shd)
            pBdr = OxmlElement('w:pBdr')
            left = OxmlElement('w:left')
            left.set(qn('w:val'), 'single')
            left.set(qn('w:sz'), '24')
            left.set(qn('w:space'), '4')
            left.set(qn('w:color'), '1B4F72')
            pBdr.append(left)
            p_adj.append(pBdr)
        for plain, is_bold in get_md_bold_sub_runs(_md_to_text_plain(text)):
            run = p.add_run(plain)
            run.bold = is_bold
            run.font.size = Pt(11)
        return p

    def _is_md_sep_line(text):
        stripped = text.strip()
        if not stripped.startswith("|"):
            return False
        inner = stripped.replace("|", "").strip()
        if not inner:
            return True
        return all(ch in "-: " for ch in inner)

    def _is_standalone_hr(text):
        stripped = text.strip()
        if not stripped:
            return False
        if stripped == "---":
            return True
        if all(ch in "-_= " for ch in stripped) and len(stripped) >= 3:
            return True
        return False

    def _flush_table_buf(lines):
        data_lines = [l for l in lines if l.strip().startswith("|")]
        if not data_lines:
            return
        first = data_lines[0]
        parts_first = [c.strip() for c in first.split("|")[1:-1]]
        if not parts_first:
            return
        ncols = len(parts_first)
        headers = [c.strip() for c in data_lines[0].split("|")[1:-1]]
        body_lines = []
        started = False
        for line in data_lines[1:]:
            stripped = line.strip()
            if stripped.startswith("|"):
                if _is_md_sep_line(line):
                    continue
                started = True
                row = [c.strip() for c in line.split("|")[1:-1]]
                if len(row) < ncols:
                    row = row + [""] * (ncols - len(row))
                body_lines.append(row[:ncols])
        if not started:
            body_lines = []
        table = doc.add_table(rows=1 + len(body_lines), cols=ncols)
        _table_save(table, headers, body_lines, ncols)

    def _flush_table_buf_in_runs(lines):
        buf = []
        for raw_line in lines:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if stripped.startswith("|") and not _is_md_sep_line(line):
                if buf and not buf[-1].strip().startswith("|"):
                    _flush_table_buf(buf)
                    buf = []
                buf.append(line)
            elif stripped.startswith("|") and _is_md_sep_line(line):
                if buf:
                    _flush_table_buf(buf)
                    buf = []
                continue
            else:
                if buf:
                    _flush_table_buf(buf)
                    buf = []
                add_md_line(line)
        if buf:
            _flush_table_buf(buf)

    with open(src_md, encoding="utf-8") as f:
        _flush_table_buf_in_runs(f)

    doc.save(dst_docx)
    if not os.path.exists(dst_docx) or os.path.getsize(dst_docx) == 0:
        raise RuntimeError("python-docx가 비어 있는 DOCX를 생성했습니다")


def _is_truetype_with_kr(path):
    if not os.path.exists(path) or not path.lower().endswith(".ttf"):
        return False
    try:
        from fontTools.ttLib import TTFont
        tt = TTFont(path)
        if 'glyf' not in tt:
            return False
        kr_sample = "아세트아미노펜 p-아미노페놀 아세트산 무수물 디클로로메탄 트리에틸아민"
        charset = set()
        for table in tt['cmap'].tables:
            for cp in table.cmap:
                charset.add(cp)
        return all(ord(ch) in charset for ch in kr_sample)
    except Exception:
        return False


def _find_kr_font():
    candidates = [
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/ArialUnicode.ttf",
    ]
    for path in candidates:
        if _is_truetype_with_kr(path):
            return path, "ArialUnicode"
    import glob
    for name in [
        "NanumGothic",
        "NanumBarunGothic",
        "NanumSquareRound",
        "NanumSquare",
        "Noto Sans CJK KR",
        "NotoSansCJK-Regular",
        "AppleGothic",
        "AppleMyungjo",
        "Batang",
        "Dotum",
    ]:
        for pattern in [
            f"/Library/Fonts/{name}.ttf",
            f"/System/Library/Fonts/{name}.ttf",
            f"/Library/Fonts/{name}*.ttf",
            f"/System/Library/Fonts/{name}*.ttf",
            f"/usr/local/share/fonts/{name}.ttf",
            f"/opt/homebrew/share/fonts/{name}.ttf",
        ]:
            matches = glob.glob(pattern)
            if matches:
                for m in matches:
                    if _is_truetype_with_kr(m):
                        return m, name
    return None, None


def _is_truetype_with_kr(path):
    if not os.path.exists(path) or not path.lower().endswith(".ttf"):
        return False
    try:
        from fontTools.ttLib import TTFont
        tt = TTFont(path)
        if 'glyf' not in tt:
            return False
        kr_sample = "아세트아미노펜 p-아미노페놀 아세트산 무수물 디클로로메탄 트리에틸아민"
        charset = set()
        for table in tt['cmap'].tables:
            for cp in table.cmap:
                charset.add(cp)
        return all(ord(ch) in charset for ch in kr_sample)
    except Exception:
        return False


def _find_kr_font():
    candidates = [
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/ArialUnicode.ttf",
    ]
    for path in candidates:
        if _is_truetype_with_kr(path):
            return path, "ArialUnicode"
    import glob
    for name in [
        "NanumGothic",
        "NanumBarunGothic",
        "NanumSquareRound",
        "NanumSquare",
        "Noto Sans CJK KR",
        "NotoSansCJK-Regular",
        "AppleGothic",
        "AppleMyungjo",
        "Batang",
        "Dotum",
    ]:
        for pattern in [
            f"/Library/Fonts/{name}.ttf",
            f"/System/Library/Fonts/{name}.ttf",
            f"/Library/Fonts/{name}*.ttf",
            f"/System/Library/Fonts/{name}*.ttf",
            f"/usr/local/share/fonts/{name}.ttf",
            f"/opt/homebrew/share/fonts/{name}.ttf",
        ]:
            matches = glob.glob(pattern)
            if matches:
                for m in matches:
                    if _is_truetype_with_kr(m):
                        return m, name
    return None, None


def build_pdf_reportlab(src_md, dst_pdf, is_main_report=False):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, Table,
                                    TableStyle, KeepTogether, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path, font_name = _find_kr_font()
    font_family = "Helvetica"
    font_registered = False
    if font_path and os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(font_name + "-Regular", font_path))
            font_family = font_name + "-Regular"
            font_registered = True
        except Exception as exc:
            print("WARNING: 한글 폰트 등록 실패 (%s: %s); PDF 한글은 깨질 수 있습니다." % (font_name, exc), file=sys.stderr)
    else:
        print("WARNING: 한글 TTF를 찾지 못했습니다; PDF 한글은 깨질 수 있습니다.", file=sys.stderr)


def _copy_if_exists(src, dst):
    if src and os.path.exists(src):
        shutil.copy(src, dst)
        return True
    return False


def build_pdf_reportlab_body(story, src_md, dst_pdf, font_family, font_registered, font_name):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, Table,
                                    TableStyle, KeepTogether, HRFlowable)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.colors import HexColor

    styles = {
        name: ParagraphStyle(name=name, fontName=font_family, fontSize=sz, leading=ld,
                             textColor=colors.HexColor("#222222"),
                             spaceAfter=4)
        for name, sz, ld in [("Body", 9.8, 15), ("Bullet", 9.8, 15), ("BulletSub", 9.8, 15)]
    }
    styles["Body"].spaceAfter = 4
    styles["Bullet"].leftIndent = 12
    styles["Bullet"].firstLineIndent = -8
    styles["Bullet"].spaceAfter = 2.5
    styles["BulletSub"].leftIndent = 22
    styles["BulletSub"].spaceAfter = 2.5

    for lvl, sz, ld, color, sb, sa in [
        (1, 17, 21, colors.HexColor("#163A5F"), 14, 5),
        (2, 13, 16, colors.HexColor("#1B4F72"), 14, 5),
        (3, 11, 13, colors.HexColor("#2C3E50"), 6, 6),
    ]:
        styles[f"Heading{lvl}"] = ParagraphStyle(
            name=f"Heading{lvl}",
            fontName=font_family,
            fontSize=sz,
            leading=ld,
            textColor=color,
            spaceBefore=sb,
            spaceAfter=sa,
            keepWithNext=True,
        )
    styles["Caption"] = ParagraphStyle(
        name="Caption",
        fontName=font_family,
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
    )
    styles["Cell"] = ParagraphStyle(
        name="Cell",
        fontName=font_family,
        fontSize=7.5,
        leading=9.5,
    )
    styles["SummaryBox"] = ParagraphStyle(
        name="SummaryBox",
        fontName=font_family,
        fontSize=9.8,
        leading=15,
        textColor=colors.HexColor("#222222"),
        backColor=colors.HexColor("#F2F6FA"),
        borderLeftColor=colors.HexColor("#1B4F72"),
        borderLeftWidth=3,
        leftIndent=6,
        rightIndent=6,
        spaceAfter=4,
        spaceBefore=0,
    )

    def escape_text(text):
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if not font_registered:
            text = re.sub(r"\*\*([^*]+)\*\*", r"<font color=\"#163A5F\">\1</font>", text)
            return text
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        return text

    def _cell(text):
        if not text:
            return Paragraph("", styles["Cell"])
        return Paragraph(escape_text(text).replace("\n", "<br/>"), styles["Cell"])

    def _img_stream(path, width_mm=95):
        full = os.path.normpath(os.path.join(SOURCE_DIR, path))
        if not os.path.exists(full):
            return Paragraph("[이미지 없음: %s]" % os.path.basename(path), styles["Body"])
        from reportlab.lib.utils import ImageReader
        ir = ImageReader(full)
        iw, ih = ir.getSize()
        if iw and ih:
            ratio = ih / iw
            if ratio <= 0.4:
                width_mm = 170
            w = width_mm * mm
            h = w * ratio
            return Image(full, width=w, height=h)
        return Image(full, width=width_mm*mm, height=width_mm*mm*0.8)

    def _parse_md(path):
        items = []
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        table_buf = []
        in_table = False
        for line in lines:
            stripped = line.strip()
            if in_table:
                if not stripped:
                    in_table = False
                    if table_buf:
                        items.append(("table", table_buf))
                        table_buf = []
                    items.append(("spacer", None))
                    continue
                if stripped.startswith("|"):
                    table_buf.append(stripped)
                    continue
                else:
                    in_table = False
                    if table_buf:
                        items.append(("table", table_buf))
                        table_buf = []
                    add_paragraph_item(stripped, items)
                    continue
            if not stripped:
                items.append(("spacer", None))
                continue
            if stripped == "---":
                items.append(("hr", None))
                continue
            if stripped.startswith("!["):
                m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
                if m:
                    items.append(("img", (m.group(1), m.group(2))))
                continue
            if stripped.startswith("#"):
                level = min(6, len(stripped) - len(stripped.lstrip("#")))
                text = stripped.lstrip("# ").strip()
            if level == 2 and text.strip() == "요약":
                items.append(("sum", (level, text)))
                continue
            items.append(("h", (level, text)))
            continue
            if stripped.startswith("|"):
                in_table = True
                table_buf = [stripped]
                continue
            add_paragraph_item(stripped, items)
        if in_table and table_buf:
            items.append(("table", table_buf))
        return items

    def _is_sep_row(cells):
        joined = "".join(cells)
        if not joined:
            return True
        return all(ch in "-: " for ch in joined)

    def _parse_table(data):
        rows = [ [c.strip() for c in line.split("|")[1:-1]] for line in data if line.strip().startswith("|") ]
        if not rows:
            return [], []
        header_rows = []
        body_rows = []
        first = True
        for r in rows:
            if _is_sep_row(r):
                continue
            if first:
                header_rows.append(r)
                first = False
            else:
                body_rows.append(r)
        if not header_rows:
            header_rows = rows[0:1]
            body_rows = rows[1:]
        n = max(len(header_rows[0]), max((len(r) for r in body_rows), default=1))
        header_rows = [r + [""] * (n - len(r)) for r in header_rows]
        body_rows = [r + [""] * (n - len(r)) for r in body_rows]
        return header_rows, body_rows

    def add_paragraph_item(text, items):
        if not text:
            return
        if text.lstrip().startswith("#"):
            level = min(6, len(text) - len(text.lstrip("#")))
            items.append(("h", (level, text.lstrip("# ").strip())))
            if level == 2 and text.strip() == "요약":
                in_summary = True
            return
        if text.startswith("!["):
            return
        if text.strip() == "---":
            items.append(("hr", None))
            return
        if text.startswith("|"):
            return
        if in_summary:
            in_summary = False
        items.append(("p", text))

    in_summary = False
    heading_after = None

    for kind, data in _parse_md(src_md):
        if kind == "h":
            level, text = data
            style_name = f"Heading{level}"
            story.append(Paragraph(escape_text(text), styles[style_name]))
            if level == 2 and text == "요약":
                in_summary = True
            continue
        if kind == "p":
            story.append(Paragraph(escape_text(data), styles["Body"]))
            continue
        if kind == "spacer":
            story.append(Spacer(1, 4*mm))
            continue
        if kind == "img":
            caption, path = data
            img_flow = _img_stream(path)
            cap_flow = Paragraph(escape_text(caption), styles["Caption"])
            if path.endswith((".png", ".jpg", ".jpeg", ".tiff", ".gif")):
                if "cpk" in path or "stick" in path:
                    width_mm = 145
                elif "_reaction.png" in path or "reaction" in path:
                    width_mm = 165
                elif "2d" in path or "structure" in path:
                    width_mm = 75
                else:
                    width_mm = 95
                img_flow = _img_stream(path, width_mm=width_mm)
            story.append(KeepTogether([img_flow, cap_flow, Spacer(1, 2*mm)]))
            continue
        if kind == "table":
            header_rows, body_rows = _parse_table(data)
            if not header_rows:
                continue
            table_data = [ [_cell(c) for c in row] for row in (header_rows + body_rows) ]
            ncol = len(header_rows[0])
            col_widths = _compute_col_widths(header_rows, body_rows, ncol)
            t = Table(table_data, colWidths=col_widths)
            t.setStyle(_table_style_basic())
            t.repeatRows = 1
            story.append(t)
            story.append(Spacer(1, 4*mm))
            continue
        if kind == "hr":
            story.append(HRFlowable(width="40%", thickness=0.6, color=HexColor("#D5DCE4"),
                                    spaceBefore=6, spaceAfter=6, hAlign='CENTER'))
            continue

    doc = SimpleDocTemplate(dst_pdf, pagesize=A4,
                             rightMargin=18*mm, leftMargin=18*mm,
                             topMargin=18*mm, bottomMargin=18*mm)
    doc.build(story)

    def _add_page_numbers(pdf_path):
        from pypdf import PdfReader, PdfWriter
        from io import BytesIO
        from reportlab.pdfgen import canvas as canvas_mod
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            writer.add_page(page)
            packet = BytesIO()
            can = canvas_mod.Canvas(packet, pagesize=A4)
            can.setFont(font_family, 8.5)
            can.setFillColor(HexColor("#888888"))
            page_num = f"- {i+1} / {len(reader.pages)} -"
            can.drawCentredString(A4[0] / 2, 12 * mm, page_num)
            can.save()
            packet.seek(0)
            overlay = PdfReader(packet)
            writer.pages[i].merge_page(overlay.pages[0])
        with open(pdf_path, "wb") as f:
            writer.write(f)

    def _compute_col_widths(header_rows, body_rows, ncol, available_mm=150, min_mm=12):
        max_len = [0] * ncol
        for row in header_rows + body_rows:
            for i, cell in enumerate(row):
                clean = escape_text(cell).replace("<br/>", " ")
                max_len[i] = max(max_len[i], len(clean))
        total = sum(max_len)
        if total == 0:
            w = available_mm / ncol
            return [w * mm] * ncol
        widths = [max(min_mm, (w / total) * available_mm) for w in max_len]
        sum_w = sum(widths)
        if sum_w > available_mm:
            ratio = available_mm / sum_w
            widths = [w * ratio for w in widths]
        elif sum_w < available_mm:
            extra = available_mm - sum_w
            widths = [w + extra / ncol for w in widths]
        return [w * mm for w in widths]

    def _table_style_basic():
        return TableStyle([
            ("FONTNAME", (0,0), (-1,-1), font_family),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1B4F72")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FC")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 4.5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4.5),
            ("LINEABOVE", (0,0), (-1,0), 0.6, colors.HexColor("#1B4F72")),
            ("LINEBELOW", (0,0), (-1,0), 0.6, colors.HexColor("#D5DCE4")),
            ("LINEBELOW", (0,-1), (-1,-1), 0.6, colors.HexColor("#D5DCE4")),
            ("LINEABOVE", (0,-1), (-1,-1), 0.6, colors.HexColor("#1B4F72")),
            ("INNERGRID", (0,1), (-1,-1), 0.25, colors.white),
            ("BOX", (0,0), (-1,-1), 0, colors.white),
        ])

    if is_main_report:
        _add_page_numbers(dst_pdf)


def _copy_if_exists(src, dst):
    if src and os.path.exists(src):
        shutil.copy(src, dst)
        return True
    return False

def _copy_if_exists(src, dst):
    if src and os.path.exists(src):
        shutil.copy(src, dst)
        return True
    return False

def main():
    src_md = SOURCE_MD
    dst_pdf = DEST_PDF
    dst_docx = DEST_DOCX

    if not os.path.exists(src_md):
        print("소스 Markdown 없음:", src_md)
        sys.exit(2)

    pandoc_ok = cmd_exists("pandoc")
    office_ok = cmd_exists("soffice") or cmd_exists("libreoffice")
    print("pandoc=%s office=%s" % (pandoc_ok, office_ok), file=sys.stderr)

    work = tempfile.mkdtemp(prefix="organic-export-")
    try:
        if dst_docx:
            docx_path = os.path.join(work, "report.docx")
            if pandoc_ok:
                pandoc_to_docx(src_md, docx_path)
            else:
                build_docx_python(src_md, docx_path)
            if office_ok:
                pdf_tmp = soffice_to_pdf(docx_path, work)
                shutil.copy(pdf_tmp, dst_pdf)
            else:
                build_pdf_reportlab(src_md, dst_pdf, is_main_report=(os.path.basename(src_md) == "report.md"))
            _copy_if_exists(docx_path, dst_docx)
        else:
            if pandoc_ok and office_ok:
                docx_path = os.path.join(work, "report.docx")
                pandoc_to_docx(src_md, docx_path)
                pdf_tmp = soffice_to_pdf(docx_path, work)
                shutil.copy(pdf_tmp, dst_pdf)
            else:
                build_pdf_reportlab(src_md, dst_pdf, is_main_report=(os.path.basename(src_md) == "report.md"))

        pages = page_count_pdf(dst_pdf)
        print("생성됨: %s (%s쪽; 존재·쪽수 확인 완료)" % (dst_pdf, pages))
        if pages is not None and pages > 20:
            print("경고: 보고서가 %s쪽으로 20쪽을 초과합니다." % pages, file=sys.stderr)
        if dst_docx and os.path.exists(dst_docx):
            print("DOCX 생성됨: %s" % dst_docx)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()