import json
import os
import sys
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from services import market_data
from services.market_capture import capture_market_snapshots


client = TestClient(app)


def _sample_history(rows=90):
    dates = pd.bdate_range("2024-01-01", periods=rows)
    close = pd.Series(range(100, 100 + rows), index=dates, dtype=float)
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000_000,
        },
        index=dates,
    )


def test_market_history_cache_is_used_when_yfinance_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(market_data, "MARKET_HISTORY_DIR", tmp_path)
    market_data.get_history.cache_clear()

    history = _sample_history()
    market_data.write_cached_history("AAPL", history, "2y", "1d")

    class BrokenTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *args, **kwargs):
            raise RuntimeError("offline")

    monkeypatch.setattr(market_data.yf, "Ticker", BrokenTicker)
    monkeypatch.setattr(
        market_data.yf,
        "download",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    cached = market_data.get_history("AAPL", "2y", "1d")
    assert len(cached) == len(history)
    assert float(cached["Close"].iloc[-1]) == float(history["Close"].iloc[-1])


def test_market_snapshot_capture_persists_book_data(monkeypatch):
    monkeypatch.setattr(
        "services.market_capture.stock_summary",
        lambda symbol, period="5d": {
            "symbol": symbol,
            "price": 123.45,
            "change": 1.25,
            "volume": 987654,
            "historical_data": [],
        },
    )

    result = capture_market_snapshots(["AAPL"])
    assert result["requested"] == 1
    assert result["saved"] == 1
    assert result["snapshots"][0]["symbol"] == "AAPL"
    assert result["snapshots"][0]["price"] == 123.45


def test_cron_endpoint_requires_secret_and_runs_ai_cycle(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-secret")
    monkeypatch.setattr(
        "routes.cron.capture_market_snapshots",
        lambda symbols: {"requested": len(symbols), "saved": len(symbols), "snapshots": [], "errors": []},
    )
    monkeypatch.setattr(
        "routes.cron.train_rl_batch",
        lambda symbols, episodes, force, agent_type: {
            "count": len(symbols),
            "trained": len(symbols),
            "errors": [],
            "results": [],
        },
    )
    monkeypatch.setattr(
        "routes.cron.stock_predictor.get_prediction",
        lambda symbol: {
            "recommendation": "HOLD",
            "confidence": "50%",
            "risk": "LOW",
            "indicators": {},
        },
    )

    unauthorized = client.get("/api/cron/train-ai?symbols=AAPL&episodes=5")
    assert unauthorized.status_code == 401

    authorized = client.get(
        "/api/cron/train-ai?symbols=AAPL,MSFT&episodes=5",
        headers={"Authorization": "Bearer test-secret"},
    )
    assert authorized.status_code == 200
    data = authorized.json()
    assert data["status"] == "ok"
    assert data["symbols"] == ["AAPL", "MSFT"]
    assert data["rl_training"]["trained"] == 2
    assert all(item["ok"] for item in data["ml_predictions"])


def test_vercel_entrypoint_exports_fastapi_app():
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    import api.index

    assert api.index.app.title == "AI Stock Trading Platform"


def test_vercel_config_routes_api_and_schedules_training():
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / "vercel.json").read_text(encoding="utf-8"))

    # Vercel Hobby projects only allow daily cron jobs.
    assert {"path": "/api/cron/train-ai", "schedule": "0 0 * * *"} in config["crons"]
    assert any(
        rewrite["source"] == "/api/(.*)" and rewrite["destination"] == "/api/index.py"
        for rewrite in config["rewrites"]
    )


def test_frontend_uses_shared_api_config_for_cloud_connections():
    root = Path(__file__).resolve().parents[2]
    src = root / "frontend" / "src"
    config = (src / "config" / "api.js").read_text(encoding="utf-8")
    assert "import.meta.env.PROD ? ''" in config

    direct_localhost = []
    for path in src.rglob("*.jsx"):
        text = path.read_text(encoding="utf-8")
        if "localhost:8000" in text:
            direct_localhost.append(path.name)
    assert direct_localhost == []


def test_bootstrap_helpers_report_prediction_errors(monkeypatch):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
    import bootstrap_market_data

    def broken_prediction(symbol):
        raise ValueError("bad feature data")

    monkeypatch.setattr(bootstrap_market_data.stock_predictor, "get_prediction", broken_prediction)
    result = bootstrap_market_data.warm_predictions(["AAPL"])
    assert result == [
        {
            "symbol": "AAPL",
            "ok": False,
            "recommendation": None,
            "confidence": None,
            "error": "bad feature data",
        }
    ]
