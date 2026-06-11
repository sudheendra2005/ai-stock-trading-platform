from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict
from urllib.parse import unquote

import numpy as np
import pandas as pd
import yfinance as yf


MARKET_HISTORY_DIR = Path(__file__).resolve().parents[1] / "data" / "market_history"
MARKET_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL_NAMES = {
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services",
    "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys",
    "ICICIBANK.NS": "ICICI Bank",
    "WIPRO.NS": "Wipro Ltd",
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corp",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
    "^NSEI": "NIFTY 50",
    "^BSESN": "SENSEX",
    "^NSEBANK": "BANK NIFTY",
}

FALLBACK_BASE_PRICES = {
    "RELIANCE.NS": 2850.0,
    "TCS.NS": 3900.0,
    "HDFCBANK.NS": 1510.0,
    "INFY.NS": 1460.0,
    "ICICIBANK.NS": 1120.0,
    "WIPRO.NS": 470.0,
    "AAPL": 190.0,
    "MSFT": 420.0,
    "GOOGL": 175.0,
    "AMZN": 185.0,
    "TSLA": 175.0,
    "^NSEI": 23500.0,
    "^BSESN": 77500.0,
    "^NSEBANK": 50000.0,
}


def normalize_symbol(symbol: str) -> str:
    return unquote(symbol or "").strip().upper()


def cache_key(symbol: str, period: str = "1mo", interval: str = "1d") -> str:
    safe_symbol = normalize_symbol(symbol).replace("^", "INDEX_").replace(".", "_")
    safe_period = (period or "1mo").replace("/", "_")
    safe_interval = (interval or "1d").replace("/", "_")
    return f"{safe_symbol}_{safe_period}_{safe_interval}.csv"


def cached_history_path(symbol: str, period: str = "1mo", interval: str = "1d") -> Path:
    return MARKET_HISTORY_DIR / cache_key(symbol, period, interval)


def _clean_history(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    expected = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in expected if col not in df.columns]
    if missing:
        return pd.DataFrame()
    cleaned = df[expected].copy()
    cleaned = cleaned.dropna(subset=["Open", "High", "Low", "Close"])
    cleaned["Volume"] = cleaned["Volume"].fillna(0)
    return cleaned


def read_cached_history(symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    path = cached_history_path(symbol, period, interval)
    if not path.exists():
        return pd.DataFrame()
    try:
        hist = pd.read_csv(path, index_col=0, parse_dates=True)
        return _clean_history(hist)
    except Exception:
        return pd.DataFrame()


def write_cached_history(symbol: str, history: pd.DataFrame, period: str = "1mo", interval: str = "1d") -> Path | None:
    hist = _clean_history(history)
    if hist.empty:
        return None
    path = cached_history_path(symbol, period, interval)
    hist.to_csv(path)
    return path


def _period_to_rows(period: str) -> int:
    period = (period or "1mo").lower()
    if period.endswith("d"):
        return max(int(period[:-1] or 1), 5)
    if period.endswith("mo"):
        return max(int(period[:-2] or 1) * 22, 22)
    if period.endswith("y"):
        return max(int(period[:-1] or 1) * 252, 252)
    return 66


def _fallback_history(symbol: str, period: str) -> pd.DataFrame:
    base_price = FALLBACK_BASE_PRICES.get(symbol)
    if base_price is None:
        return pd.DataFrame()

    rows = _period_to_rows(period)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=rows)
    seed = abs(hash(symbol)) % (2**32)
    rng = np.random.default_rng(seed)
    trend = np.linspace(-0.08, 0.06, rows)
    seasonal = np.sin(np.linspace(0, 8 * np.pi, rows)) * 0.025
    noise = rng.normal(0, 0.008, rows).cumsum() / 4
    close = base_price * (1 + trend + seasonal + noise)
    open_ = close * (1 + rng.normal(0, 0.004, rows))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.002, 0.015, rows))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.002, 0.015, rows))
    volume = rng.integers(500_000, 8_000_000, rows)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=dates,
    )


@lru_cache(maxsize=256)
def get_history(symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV data through yfinance with local cache and synthetic fallback."""
    normalized = normalize_symbol(symbol)
    try:
        hist = yf.Ticker(normalized).history(period=period, interval=interval, auto_adjust=False)
        hist = _clean_history(hist)
        if not hist.empty:
            write_cached_history(normalized, hist, period, interval)
            return hist
    except Exception:
        pass

    try:
        hist = yf.download(
            normalized,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        hist = _clean_history(hist)
        if not hist.empty:
            write_cached_history(normalized, hist, period, interval)
            return hist
    except Exception:
        pass

    cached = read_cached_history(normalized, period, interval)
    if not cached.empty:
        return cached

    return _fallback_history(normalized, period)


@lru_cache(maxsize=128)
def get_info(symbol: str) -> Dict[str, Any]:
    normalized = normalize_symbol(symbol)
    try:
        info = yf.Ticker(normalized).get_info()
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def latest_price(symbol: str) -> float | None:
    hist = get_history(symbol, period="5d")
    if hist.empty:
        return None
    return float(hist["Close"].iloc[-1])


def stock_summary(symbol: str, period: str = "1mo") -> Dict[str, Any] | None:
    normalized = normalize_symbol(symbol)
    hist = get_history(normalized, period=period)
    if hist.empty:
        return None

    info = get_info(normalized)
    current_price = float(hist["Close"].iloc[-1])
    open_price = float(hist["Open"].iloc[-1])
    change = ((current_price - open_price) / open_price * 100) if open_price else 0.0

    return {
        "symbol": normalized,
        "name": info.get("longName") or info.get("shortName") or SYMBOL_NAMES.get(normalized, normalized),
        "current_price": round(current_price, 2),
        "price": round(current_price, 2),
        "change": round(change, 2),
        "volume": int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0,
        "currency": info.get("currency", "INR" if normalized.endswith(".NS") or normalized.startswith("^NSE") else "USD"),
        "exchange": info.get("exchange", "NSE" if normalized.endswith(".NS") or normalized.startswith("^NSE") else "NASDAQ"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "dividend_yield": info.get("dividendYield"),
        "52_week_high": info.get("fiftyTwoWeekHigh") or float(hist["High"].max()),
        "52_week_low": info.get("fiftyTwoWeekLow") or float(hist["Low"].min()),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "description": ((info.get("longBusinessSummary") or "")[:500] + "...") if info.get("longBusinessSummary") else "",
        "historical_data": [
            {
                "date": str(date.date()),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
            }
            for date, row in hist.tail(30).iterrows()
        ],
    }
