#!/usr/bin/env python3
"""Quick test for fuzzy/company-name -> symbol mapping using backend/data/tickers.json

Run from repository root:
  python scripts/test_search_mapping.py
"""
import json
from pathlib import Path
import difflib

def load_tickers():
    repo = Path(__file__).resolve().parents[1]
    p = repo / 'backend' / 'data' / 'tickers.json'
    if not p.exists():
        print('tickers.json not found at', p)
        return {}
    data = json.loads(p.read_text(encoding='utf-8'))
    mapping = {}
    if isinstance(data, dict):
        for s, n in data.items():
            mapping[s.upper()] = n
    else:
        for item in data:
            sym = (item.get('symbol') or item.get('ticker') or '').strip()
            name = (item.get('name') or item.get('company') or '').strip()
            if sym and name:
                mapping[sym.upper()] = name
    return mapping

def find_symbol(query, mapping):
    q = (query or '').strip().upper()
    if not q:
        return None
    # Prefer exact symbol lookups for short alpha-only queries (avoid false positives)
    if q.isalpha() and len(q) <= 5:
        if q in mapping:
            return q
        if f"{q}.NS" in mapping:
            return f"{q}.NS"

    if q in mapping:
        return q
    if not q.endswith('.NS') and (q + '.NS') in mapping:
        return q + '.NS'
    # direct name match
    for s, n in mapping.items():
        if n.upper() == q:
            return s
    # fuzzy (higher cutoff)
    names = list(mapping.keys()) + [v.upper() for v in mapping.values()]
    m = difflib.get_close_matches(q, names, n=1, cutoff=0.65)
    if m:
        mm = m[0]
        if mm in mapping:
            return mm
        for s, n in mapping.items():
            if n.upper() == mm:
                return s
    # substring match as a fallback (helps with partial company names)
    for s, n in mapping.items():
        if n and q in n.upper():
            return s
    return None

def main():
    mapping = load_tickers()
    tests = [
        'Reliance', 'Tata Consultancy Services', 'INFY', 'TCS', 'AAPL', 'State Bank of India',
        'Bajaj Fin', 'Kotak Mahindra Bank', 'Maruti Suzuki', 'ITC', 'Zomato'
    ]
    for t in tests:
        sym = find_symbol(t, mapping)
        print(f"{t!r} -> {sym}")

if __name__ == '__main__':
    main()
