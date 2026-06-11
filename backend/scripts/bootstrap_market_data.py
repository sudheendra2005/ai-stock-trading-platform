from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from prediction.stock_predictor import stock_predictor  # noqa: E402
from rl.agent_service import DEFAULT_RL_SYMBOLS, train_rl_batch  # noqa: E402
from services.market_capture import capture_market_snapshots  # noqa: E402
from services.market_data import get_history, normalize_symbol, cached_history_path  # noqa: E402


DEFAULT_PERIODS = ("5d", "1mo", "2y")


def parse_symbols(raw: str | None) -> list[str]:
    if not raw:
        return DEFAULT_RL_SYMBOLS
    symbols = [normalize_symbol(part) for part in raw.split(",") if normalize_symbol(part)]
    return symbols or DEFAULT_RL_SYMBOLS


def download_history(symbols: list[str], periods: tuple[str, ...], interval: str) -> list[dict]:
    results = []
    for symbol in symbols:
        for period in periods:
            history = get_history(symbol, period=period, interval=interval)
            path = cached_history_path(symbol, period=period, interval=interval)
            results.append({
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "rows": int(len(history)),
                "path": str(path),
                "ok": not history.empty,
            })
    return results


def warm_predictions(symbols: list[str]) -> list[dict]:
    warmed = []
    for symbol in symbols:
        try:
            prediction = stock_predictor.get_prediction(symbol)
            warmed.append({
                "symbol": symbol,
                "ok": "error" not in prediction,
                "recommendation": prediction.get("recommendation"),
                "confidence": prediction.get("confidence"),
                "error": prediction.get("error"),
            })
        except Exception as exc:
            warmed.append({
                "symbol": symbol,
                "ok": False,
                "recommendation": None,
                "confidence": None,
                "error": str(exc),
            })
    return warmed


def main() -> int:
    parser = argparse.ArgumentParser(description="Download initial stock data and warm AI/RL predictions.")
    parser.add_argument("--symbols", help="Comma-separated symbols. Defaults to the platform watchlist.")
    parser.add_argument("--periods", default=",".join(DEFAULT_PERIODS), help="Comma-separated yfinance periods.")
    parser.add_argument("--interval", default="1d", help="yfinance interval, default 1d.")
    parser.add_argument("--episodes", type=int, default=20, help="RL episodes for bootstrap training.")
    parser.add_argument("--skip-rl", action="store_true", help="Only download data and warm ML predictions.")
    args = parser.parse_args()

    symbols = parse_symbols(args.symbols)
    periods = tuple(part.strip() for part in args.periods.split(",") if part.strip())
    episodes = max(5, min(args.episodes, 120))

    history = download_history(symbols, periods, args.interval)
    snapshots = capture_market_snapshots(symbols)
    predictions = warm_predictions(symbols)
    rl = None
    if not args.skip_rl:
        rl = train_rl_batch(symbols=symbols, episodes=episodes, force=True, agent_type="q")

    print(json.dumps({
        "symbols": symbols,
        "history": history,
        "snapshots": snapshots,
        "predictions": predictions,
        "rl_training": rl,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
