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
    from docx.shared import Pt, Inches
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
        table.style = "Light List Accent 1"
        for i, h in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = _md_to_text_plain(h)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
                    run.font.bold = True
        for r_idx, row in enumerate(body):
            for c_idx in range(0, min(ncols, len(row))):
                cell = table.cell(r_idx + 1, c_idx)
                cell.text = _md_to_text_plain(row[c_idx])
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9)

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

    def add_md_line(text):
        text = text.rstrip("\n")
        if not text:
            return
        if text.lstrip().startswith("#"):
            level = min(6, len(text) - len(text.lstrip("#")))
            doc.add_heading(text.lstrip("# ").strip(), level=level)
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
        p = doc.add_paragraph(_md_to_text_plain(text))
        return p

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


def build_pdf_reportlab(src_md, dst_pdf):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
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

    if not font_registered:
        print("DEBUG: 등록된 한글 폰트 없음 -> Helvetica로 PDF 생성", file=sys.stderr)

    RESOURCE_DIR = SOURCE_DIR

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Caption", fontName=font_family, fontSize=9, leading=11, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Cell", fontName=font_family, fontSize=7.5, leading=9.5))
    styles.add(ParagraphStyle(name="Body", fontName=font_family, fontSize=10.5, leading=14))
    for lvl in range(1, 7):
        style_name = "Heading%d" % lvl
        if style_name in styles:
            existing = styles[style_name]
            existing.fontName = font_family
            existing.fontSize = (18 if lvl == 1 else (14 if lvl == 2 else 12))
            existing.leading = (20 if lvl == 1 else (16 if lvl == 2 else 14))
            existing.spaceBefore = (10 if lvl <= 2 else 6)
            existing.spaceAfter = 6
        else:
            existing = None
            styles.add(ParagraphStyle(
                name=style_name,
                fontName=font_family,
                fontSize=(18 if lvl == 1 else (14 if lvl == 2 else 12)),
                leading=(20 if lvl == 1 else (16 if lvl == 2 else 14)),
                spaceBefore=(10 if lvl <= 2 else 6),
                spaceAfter=6,
            ))

    def _cell(text):
        if not text:
            return Paragraph("", styles["Cell"])
        return Paragraph(_md_to_text_plain_for_pdf(text).replace("\n", "<br/>"), styles["Cell"])

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
                    items.append(("p", stripped))
                    continue
            if not stripped:
                items.append(("spacer", None))
                continue
            if stripped == "---":
                items.append(("spacer", None))
                continue
            if stripped.startswith("!["):
                m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
                if m:
                    items.append(("img", (m.group(1), m.group(2))))
                continue
            if stripped.startswith("#"):
                level = min(6, len(stripped) - len(stripped.lstrip("#")))
                items.append(("h", (level, stripped.lstrip("# ").strip())))
                continue
            if stripped.startswith("|"):
                in_table = True
                table_buf = [stripped]
                continue
            items.append(("p", stripped))
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

    story = []
    for kind, data in _parse_md(src_md):
        if kind == "h":
            lvl, text = data
            style_name = "Heading%d" % lvl
            if style_name not in styles:
                style_name = "Heading1"
            story.append(Paragraph(_md_to_text_plain_for_pdf(text), styles[style_name]))
        elif kind == "p":
            story.append(Paragraph(_md_to_text_plain_for_pdf(data), styles["Body"]))
        elif kind == "spacer":
            story.append(Spacer(1, 4*mm))
        elif kind == "img":
            caption, path = data
            story.append(_img_stream(path))
            story.append(Paragraph(_md_to_text_plain_for_pdf(caption), styles["Caption"]))
            story.append(Spacer(1, 4*mm))
        elif kind == "table":
            header_rows, body_rows = _parse_table(data)
            if not header_rows:
                continue
            table_data = [ [_cell(c) for c in row] for row in (header_rows + body_rows) ]
            ncol = len(header_rows[0])
            col_widths = [190*mm/ncol]*ncol
            t = Table(table_data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), font_family),
                ("FONTSIZE", (0,0), (-1,-1), 7.5),
                ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#888888")),
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e6e6e6")),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 3),
                ("RIGHTPADDING", (0,0), (-1,-1), 3),
                ("TOPPADDING", (0,0), (-1,-1), 2),
                ("BOTTOMPADDING", (0,0), (-1,-1), 2),
            ]))
            story.append(t)
            story.append(Spacer(1, 4*mm))

    doc = SimpleDocTemplate(dst_pdf, pagesize=A4, rightMargin=12*mm, leftMargin=12*mm,
                             topMargin=12*mm, bottomMargin=12*mm)
    doc.build(story)


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
                build_pdf_reportlab(src_md, dst_pdf)
            _copy_if_exists(docx_path, dst_docx)
        else:
            if pandoc_ok and office_ok:
                docx_path = os.path.join(work, "report.docx")
                pandoc_to_docx(src_md, docx_path)
                pdf_tmp = soffice_to_pdf(docx_path, work)
                shutil.copy(pdf_tmp, dst_pdf)
            else:
                build_pdf_reportlab(src_md, dst_pdf)

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
