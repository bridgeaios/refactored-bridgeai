#!/usr/bin/env bash
# One-shot: bring in storage from Google Drive, new Google Sheet, or local Excel → data/storage-sync.json (configurable & viewable).
# Requires: gcloud CLI (for Google), optional: python3 + openpyxl (for local Excel).
# Usage:
#   GOOGLE_DRIVE_FILE_ID=xxx ./scripts/google-storage-sync.sh
#   GOOGLE_SHEET_ID=xxx ./scripts/google-storage-sync.sh
#   LOCAL_EXCEL_PATH=./config.xlsx ./scripts/google-storage-sync.sh
# View: http://localhost:4202/ (Taurus Showcase) or GET http://localhost:4202/api/storage-sync

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data"
OUT="$DATA_DIR/storage-sync.json"
mkdir -p "$DATA_DIR"

# --- Get gcloud token (for Google sources) ---
get_token() {
  if ! command -v gcloud &>/dev/null; then
    echo "gcloud not found. Install: https://cloud.google.com/sdk/docs/install"
    exit 1
  fi
  gcloud auth application-default print-access-token 2>/dev/null || {
    echo "Run: gcloud auth application-default login"
    exit 1
  }
}

# --- 1) Google Drive: download/export file by ID ---
from_drive() {
  local FILE_ID="$1"
  local TOKEN="$(get_token)"
  local MIME
  MIME=$(curl -s -H "Authorization: Bearer $TOKEN" "https://www.googleapis.com/drive/v3/files/$FILE_ID?fields=mimeType,name" | sed -n 's/.*"mimeType": "\([^"]*\)".*/\1/p')
  local NAME
  NAME=$(curl -s -H "Authorization: Bearer $TOKEN" "https://www.googleapis.com/drive/v3/files/$FILE_ID?fields=name" | sed -n 's/.*"name": "\([^"]*\)".*/\1/p')
  if [[ "$MIME" == *"spreadsheet"* ]]; then
    curl -s -H "Authorization: Bearer $TOKEN" "https://www.googleapis.com/drive/v3/files/$FILE_ID/export?mimeType=text/csv" -o "$DATA_DIR/drive_export.csv"
    SYNCED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 -c "
import json,csv
with open('$DATA_DIR/drive_export.csv', newline='', encoding='utf-8') as f:
    r = list(csv.DictReader(f))
out = {'source': 'google_drive', 'fileId': '$FILE_ID', 'name': '$NAME', 'syncedAt': '$SYNCED_AT', 'rows': r}
with open('$OUT', 'w', encoding='utf-8') as f: json.dump(out, f, indent=2)
" 2>/dev/null || {
    echo "{\"source\":\"google_drive\",\"fileId\":\"$FILE_ID\",\"name\":\"$NAME\",\"syncedAt\":\"$SYNCED_AT\",\"rawPath\":\"data/drive_export.csv\"}" > "$OUT"
  }
  elif [[ -n "$MIME" ]]; then
    curl -sL -H "Authorization: Bearer $TOKEN" "https://www.googleapis.com/drive/v3/files/$FILE_ID?alt=media" -o "$DATA_DIR/drive_file"
    echo "{\"source\":\"google_drive\",\"fileId\":\"$FILE_ID\",\"name\":\"$NAME\",\"syncedAt\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"localPath\":\"data/drive_file\"}" > "$OUT"
  fi
}

# --- 2) Google Sheet: read first sheet via Sheets API ---
from_sheet() {
  local SHEET_ID="$1"
  local RANGE="${2:-A1:Z1000}"
  local TOKEN="$(get_token)"
  SYNCED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  curl -s -H "Authorization: Bearer $TOKEN" "https://sheets.googleapis.com/v4/spreadsheets/$SHEET_ID/values/$RANGE" | python3 -c "
import json,sys
d = json.load(sys.stdin)
vals = d.get('values', [])
headers = [str(x) for x in vals[0]] if vals else []
rows = [dict(zip(headers, row)) for row in vals[1:]] if len(headers) else []
out = {'source': 'google_sheet', 'sheetId': '$SHEET_ID', 'range': '$RANGE', 'syncedAt': '$SYNCED_AT', 'headers': headers, 'rows': rows}
with open('$OUT', 'w', encoding='utf-8') as f: json.dump(out, f, indent=2)
" 2>/dev/null || echo "{\"source\":\"google_sheet\",\"sheetId\":\"$SHEET_ID\",\"syncedAt\":\"$SYNCED_AT\",\"error\":\"parse failed\"}" > "$OUT"
}

# --- 3) Local Excel: convert to JSON (python3 + openpyxl or csv) ---
from_local_excel() {
  local EXCEL_PATH="$1"
  if [[ ! -f "$EXCEL_PATH" ]]; then
    echo "File not found: $EXCEL_PATH"
    exit 1
  fi
  if python3 -c "import openpyxl" 2>/dev/null; then
    python3 "$SCRIPT_DIR/read-excel-to-json.py" "$EXCEL_PATH" "$OUT"
  else
    # Fallback: if it's actually a .csv, use it
    if [[ "${EXCEL_PATH,,}" == *.csv ]]; then
      python3 -c "
import json,csv
with open('$EXCEL_PATH', newline='', encoding='utf-8') as f:
    r = list(csv.DictReader(f))
out = {'source': 'local_excel', 'path': '$EXCEL_PATH', 'syncedAt': '$(date -u +%Y-%m-%dT%H:%M:%SZ)', 'rows': r}
with open('$OUT', 'w', encoding='utf-8') as f: json.dump(out, f, indent=2)
"
    else
      echo "Install openpyxl for .xlsx: pip install openpyxl. Or use a .csv file."
      echo "{\"source\":\"local_excel\",\"path\":\"$EXCEL_PATH\",\"syncedAt\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"error\":\"openpyxl required for xlsx\"}" > "$OUT"
    fi
  fi
}

# --- Main: pick source ---
if [[ -n "$GOOGLE_DRIVE_FILE_ID" ]]; then
  from_drive "$GOOGLE_DRIVE_FILE_ID"
elif [[ -n "$GOOGLE_SHEET_ID" ]]; then
  from_sheet "$GOOGLE_SHEET_ID" "${GOOGLE_SHEET_RANGE:-A1:Z1000}"
elif [[ -n "$LOCAL_EXCEL_PATH" ]]; then
  from_local_excel "$LOCAL_EXCEL_PATH"
else
  echo "Set one of: GOOGLE_DRIVE_FILE_ID, GOOGLE_SHEET_ID, LOCAL_EXCEL_PATH"
  echo "Example: GOOGLE_SHEET_ID=1abc... ./scripts/google-storage-sync.sh"
  echo "Writing placeholder."
  echo '{"source":"none","syncedAt":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","hint":"Set GOOGLE_DRIVE_FILE_ID, GOOGLE_SHEET_ID, or LOCAL_EXCEL_PATH"}' > "$OUT"
fi

echo "Wrote $OUT"
echo "Viewable: http://localhost:4202/api/storage-sync  (start Taurus Showcase: ./scripts/serve-taurus-showcase.ps1)"
