#!/usr/bin/env python3
"""Import NSE listed equities and write a tickers.json for the backend.

Usage:
  python scripts/import_nse_tickers.py

This script downloads the official NSE equities list (EQUITY_L.csv) and
creates `backend/app/data/tickers.json` with entries like:
  [{"symbol":"TCS.NS","name":"Tata Consultancy Services"}, ...]

Note: You may need to run `pip install requests` if not already installed.
"""
import csv
import json
import sys
from pathlib import Path

import urllib.request

URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"


def main():
    print("Downloading NSE equities list...")
    with urllib.request.urlopen(URL, timeout=30) as resp:
        raw = resp.read()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    reader = csv.DictReader(lines)

    items = []
    for row in reader:
        # Common column names vary; attempt a few
        sym = row.get('SYMBOL') or row.get('Symbol') or row.get('SC_CODE') or row.get('TICKER')
        name = row.get('NAME OF COMPANY') or row.get('Company Name') or row.get('SC_NAME') or row.get('NAME')
        if not sym:
            # try first column as symbol
            keys = list(row.keys())
            if keys:
                sym = row.get(keys[0])
        if not name:
            # try second column as name
            keys = list(row.keys())
            if len(keys) > 1:
                name = row.get(keys[1])
        if sym and name:
            sym = sym.strip()
            name = name.strip()
            # ensure NSE suffix to match codebase convention
            if not sym.endswith('.NS'):
                sym = f"{sym}.NS"
            items.append({"symbol": sym, "name": name})

    if not items:
        print("No tickers parsed from NSE CSV — aborting.")
        sys.exit(1)

    # Write to both backend/app/data/tickers.json and backend/data/tickers.json
    repo_root = Path(__file__).resolve().parents[1]
    targets = [
        repo_root / 'backend' / 'app' / 'data',
        repo_root / 'backend' / 'data',
    ]
    for d in targets:
        d.mkdir(parents=True, exist_ok=True)
        out_file = d / 'tickers.json'
        with open(out_file, 'w', encoding='utf-8') as fh:
            json.dump(items, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {len(items)} tickers to {out_file}")


if __name__ == '__main__':
    main()
