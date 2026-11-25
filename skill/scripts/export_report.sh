#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: export_report.sh SOURCE.md DESTINATION.docx|DESTINATION.pdf

Requirements: pandoc and LibreOffice (soffice or libreoffice). For page count,
pdfinfo or Python with pypdf must be available. Markdown image paths are
resolved relative to SOURCE.md's directory. Exports are rejected above 20 pages.
EOF
}

if [[ $# -ne 2 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  [[ $# -eq 2 ]] || exit 0
fi

source_md="$1"
destination="$2"

if [[ ! -f "$source_md" ]]; then
  printf 'Source Markdown not found: %s\n' "$source_md" >&2
  exit 2
fi
if [[ -e "$destination" ]]; then
  printf 'Destination already exists; choose a new filename to preserve the earlier report: %s\n' "$destination" >&2
  exit 2
fi

if ! command -v pandoc >/dev/null 2>&1; then
  printf 'Missing dependency: pandoc\n' >&2
  exit 2
fi

office_bin=""
if command -v soffice >/dev/null 2>&1; then
  office_bin="$(command -v soffice)"
elif command -v libreoffice >/dev/null 2>&1; then
  office_bin="$(command -v libreoffice)"
fi
if [[ -z "$office_bin" ]]; then
  printf 'Missing dependency: LibreOffice (soffice/libreoffice)\n' >&2
  exit 2
fi

extension="${destination##*.}"
extension="${extension,,}"
if [[ "$extension" != "docx" && "$extension" != "pdf" ]]; then
  printf 'Destination must end in .docx or .pdf\n' >&2
  exit 2
fi

source_dir="$(cd "$(dirname "$source_md")" && pwd)"
destination_dir="$(dirname "$destination")"
mkdir -p "$destination_dir"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/organic-report.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

docx_path="$work_dir/report.docx"
pandoc --from=gfm --resource-path="$source_dir" "$source_md" --output="$docx_path"
if [[ ! -s "$docx_path" ]]; then
  printf 'Pandoc did not create a non-empty DOCX.\n' >&2
  exit 1
fi

"$office_bin" --headless --convert-to pdf --outdir "$work_dir" "$docx_path" >/dev/null
pdf_path="$work_dir/report.pdf"
if [[ ! -s "$pdf_path" ]]; then
  printf 'LibreOffice did not create a non-empty PDF preview.\n' >&2
  exit 1
fi

if command -v pdfinfo >/dev/null 2>&1; then
  page_count="$(pdfinfo "$pdf_path" | awk '/^Pages:/ {print $2}')"
elif python3 -c 'import pypdf' >/dev/null 2>&1; then
  page_count="$(python3 -c 'from pypdf import PdfReader; import sys; print(len(PdfReader(sys.argv[1]).pages))' "$pdf_path")"
else
  printf 'Page count could not be checked: install pdfinfo or Python pypdf.\n' >&2
  exit 2
fi

if [[ ! "$page_count" =~ ^[0-9]+$ ]]; then
  printf 'Could not read a valid page count from PDF preview.\n' >&2
  exit 1
fi
if (( page_count > 20 )); then
  printf 'Report is %s pages; maximum is 20. No destination file was written.\n' "$page_count" >&2
  exit 1
fi

if [[ "$extension" == "docx" ]]; then
  cp "$docx_path" "$destination"
else
  cp "$pdf_path" "$destination"
fi
if [[ ! -s "$destination" ]]; then
  printf 'Export verification failed: destination is missing or empty.\n' >&2
  exit 1
fi
printf 'Created %s (%s pages; existence and page limit verified).\n' "$destination" "$page_count"
