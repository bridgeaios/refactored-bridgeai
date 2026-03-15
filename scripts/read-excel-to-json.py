#!/usr/bin/env python3
"""Read first sheet of an Excel file (.xlsx) and write JSON to data/storage-sync.json format."""
import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("Usage: read-excel-to-json.py <input.xlsx> <output.json>", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        import openpyxl
    except ImportError:
        print("pip install openpyxl", file=sys.stderr)
        sys.exit(1)
    from datetime import datetime
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = [list(row) for row in ws.iter_rows(values_only=True)]
    wb.close()
    headers = [str(c) for c in rows[0]] if rows else []
    data_rows = []
    for r in rows[1:]:
        row = list(r)
        while len(row) < len(headers):
            row.append(None)
        data_rows.append(dict(zip(headers, row[:len(headers)])))
    out = {
        "source": "local_excel",
        "path": str(path),
        "syncedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "headers": headers,
        "rows": data_rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {out_path} ({len(data_rows)} rows)")

if __name__ == "__main__":
    main()
