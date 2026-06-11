from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from database import SessionLocal
from models import MarketDataSnapshot
from services.market_data import normalize_symbol, stock_summary


DEFAULT_CAPTURE_SYMBOLS = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
    "WIPRO.NS",
    "AAPL",
    "MSFT",
    "GOOGL",
]


def capture_market_snapshots(symbols: Iterable[str] | None = None) -> Dict[str, Any]:
    selected = [normalize_symbol(s) for s in (symbols or DEFAULT_CAPTURE_SYMBOLS) if normalize_symbol(s)]
    saved: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    db = SessionLocal()
    try:
        for symbol in selected:
            try:
                summary = stock_summary(symbol, period="5d")
                if not summary:
                    errors.append({"symbol": symbol, "error": "No market data available"})
                    continue
                row = MarketDataSnapshot(
                    symbol=symbol,
                    price=float(summary["price"]),
                    change_percent=float(summary.get("change") or 0.0),
                    volume=int(summary.get("volume") or 0),
                    payload_json=json.dumps(summary),
                )
                db.add(row)
                saved.append({
                    "symbol": symbol,
                    "price": row.price,
                    "change_percent": row.change_percent,
                    "volume": row.volume,
                })
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "requested": len(selected),
        "saved": len(saved),
        "snapshots": saved,
        "errors": errors,
    }
