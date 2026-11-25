#!/usr/bin/env python3
import zipfile, re, os, sys

docx_path = "/Users/kdy20069/Downloads/Organic/report/acetaminophen_report.docx"
z = zipfile.ZipFile(docx_path)

rels = z.read("word/_rels/document.xml.rels").decode("utf-8","replace")
doc = z.read("word/document.xml").decode("utf-8","replace")

# 이미지 관계/문서 내 미디어 존재 확인
media_rels = re.findall(r'Target="[^"]*media[^"]*"', rels)
img_elements = (
    doc.count("<w:drawing>")
    + doc.count("<a:blip")
    + doc.count("<pic:pic")
    + doc.count("<v:shape")
    + doc.count("<wp:inline")
)

# [이미지 없음: ...] 카운트
missing = re.findall(r"\[이미지 없음:", doc)

# &gt; &lt; &amp; 카운트
amp = doc.count("&gt;") + doc.count("&lt;") + doc.count("&amp;")

# 표 구분선 ---: 패턴 카운트
sep_col = len(re.findall(r"---:", doc))

print("=== DOCX 검증 ===")
print("media_rels:", len(media_rels))
print("img_elements( drawing/blip/pic/vshape/wp:inline 합계 ):", img_elements)
print("[이미지 없음: ...] 수:", len(missing))
print("&gt;/&lt;/&amp; 수:", amp)
print("표 구분선(---:) 수:", sep_col)
print("\n[이미지 없음] 경로 목록:")
for m in sorted(set(re.findall(r"\[이미지 없음: ([^\]]+)\]", doc))):
    print(" -", m)
print("\npkg 내 media 파일:", [n for n in z.namelist() if "media" in n or n.lower().endswith((".png",".jpg",".jpeg",".emf",".wmf",".ppm"))])
