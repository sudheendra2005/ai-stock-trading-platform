from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from prediction.stock_predictor import stock_predictor
from rl.agent_service import DEFAULT_RL_SYMBOLS, train_rl_batch
from services.market_capture import capture_market_snapshots
from services.market_data import normalize_symbol


router = APIRouter()


def _parse_symbols(raw: Optional[str]) -> list[str] | None:
    if not raw:
        env_symbols = os.getenv("RL_SYMBOLS")
        raw = env_symbols or ""
    symbols = [normalize_symbol(part) for part in raw.split(",") if normalize_symbol(part)]
    return symbols or None


def _authorize(authorization: str | None) -> None:
    secret = os.getenv("CRON_SECRET")
    if not secret:
        return
    expected = f"Bearer {secret}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cron authorization",
        )


@router.get("/train-ai")
def train_ai_cron(
    authorization: str | None = Header(default=None),
    symbols: str | None = None,
    episodes: int = 40,
    force: bool = False,
):
    """Serverless-friendly training cycle for Vercel Cron or any scheduler."""
    _authorize(authorization)
    selected_symbols = _parse_symbols(symbols) or DEFAULT_RL_SYMBOLS
    bounded_episodes = max(5, min(int(episodes), 120))

    capture_result = capture_market_snapshots(selected_symbols)
    rl_result = train_rl_batch(
        symbols=selected_symbols,
        episodes=bounded_episodes,
        force=force,
        agent_type=os.getenv("RL_AGENT_TYPE", "q"),
    )

    ml_results = []
    for symbol in selected_symbols:
        prediction = stock_predictor.get_prediction(symbol)
        ml_results.append({
            "symbol": symbol,
            "ok": "error" not in prediction,
            "recommendation": prediction.get("recommendation"),
            "confidence": prediction.get("confidence"),
            "error": prediction.get("error"),
        })

    return {
        "status": "ok",
        "symbols": selected_symbols,
        "episodes": bounded_episodes,
        "market_capture": capture_result,
        "rl_training": rl_result,
        "ml_predictions": ml_results,
    }
