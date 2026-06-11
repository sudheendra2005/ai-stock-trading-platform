from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from services.market_data import get_history, normalize_symbol
from rl.q_agent import QLearningTradingAgent
from database import SessionLocal
from models import RLAgentPolicy


AGENT_DIR = Path(__file__).resolve().parent / "saved_agents"
AGENT_DIR.mkdir(exist_ok=True)

DEFAULT_RL_SYMBOLS = [
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


def _risk_from_return_gap(strategy_return: float, buy_hold_return: float) -> str:
    if strategy_return < -0.08:
        return "HIGH"
    if strategy_return + 0.04 < buy_hold_return:
        return "MEDIUM"
    return "LOW"


def _normalise_symbols(symbols: Iterable[str] | None) -> List[str]:
    source = symbols or DEFAULT_RL_SYMBOLS
    normalised = []
    for symbol in source:
        item = normalize_symbol(symbol)
        if item and item not in normalised:
            normalised.append(item)
    return normalised


def _policy_grade(backtest: Dict[str, Any]) -> str:
    score = float(backtest.get("stability_score", 0))
    excess = float(backtest.get("excess_return", 0))
    drawdown = abs(float(backtest.get("max_drawdown", 0)))
    if score > 0.12 and excess > 0 and drawdown < 0.18:
        return "A"
    if score > 0.04 and drawdown < 0.25:
        return "B"
    if score > -0.02:
        return "C"
    return "D"


def _agent_path(symbol: str) -> Path:
    safe = normalize_symbol(symbol).replace("^", "INDEX_").replace(".", "_")
    return AGENT_DIR / f"{safe}.json"


def _read_db_policy(symbol: str) -> Dict[str, Any] | None:
    db = SessionLocal()
    try:
        row = (
            db.query(RLAgentPolicy)
            .filter(RLAgentPolicy.symbol == normalize_symbol(symbol))
            .first()
        )
        if not row:
            return None
        return json.loads(row.payload_json)
    except Exception:
        return None
    finally:
        db.close()


def _write_db_policy(symbol: str, agent_type: str, payload: Dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        normalized = normalize_symbol(symbol)
        row = (
            db.query(RLAgentPolicy)
            .filter(RLAgentPolicy.symbol == normalized)
            .first()
        )
        payload_json = json.dumps(payload)
        if row:
            row.agent_type = agent_type
            row.payload_json = payload_json
        else:
            row = RLAgentPolicy(
                symbol=normalized,
                agent_type=agent_type,
                payload_json=payload_json,
            )
            db.add(row)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _load_history(symbol: str) -> pd.DataFrame:
    return get_history(normalize_symbol(symbol), period="2y")


def _split_history(history: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    split = max(int(len(history) * 0.75), 90)
    split = min(split, len(history) - 40)
    return history.iloc[:split].copy(), history.iloc[split:].copy()


def _save_agent(symbol: str, agent, metadata: Dict[str, Any]) -> None:
    safe = normalize_symbol(symbol).replace("^", "INDEX_").replace(".", "_")
    payload: Dict[str, Any] = {
        "symbol": normalize_symbol(symbol),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
    }
    agent_dict = agent.to_dict() if hasattr(agent, "to_dict") else {}
    if getattr(agent, "agent_type", "").lower() == "dqn":
        model_file = AGENT_DIR / f"{safe}.pt"
        try:
            agent.save(str(model_file))
            payload["model_file"] = str(model_file)
        except Exception:
            pass
        agent_dict["agent_type"] = "dqn"
    payload["agent"] = agent_dict
    agent_type = agent_dict.get("agent_type") or getattr(agent, "agent_type", "q") or "q"
    try:
        _agent_path(symbol).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass
    _write_db_policy(symbol, str(agent_type).lower(), payload)
    load_agent.cache_clear()
    get_rl_recommendation.cache_clear()


@lru_cache(maxsize=64)
def load_agent(symbol: str) -> Dict[str, Any] | None:
    path = _agent_path(symbol)
    payload = _read_db_policy(symbol)
    source = "database"
    if payload is None and path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        source = str(path)
    if payload is None:
        return None
    agent_meta = payload.get("agent", {}) or {}
    agent_type = str(agent_meta.get("agent_type", "q")).lower()
    if agent_type == "dqn":
        try:
            from rl.dqn_agent import DQNTradingAgent

            agent = DQNTradingAgent.from_dict(agent_meta) if hasattr(DQNTradingAgent, "from_dict") else DQNTradingAgent()
            model_file = payload.get("model_file")
            if model_file:
                try:
                    agent.load(str(model_file))
                except Exception:
                    pass
        except Exception:
            return None
    else:
        agent = QLearningTradingAgent.from_dict(agent_meta)

    return {
        "agent": agent,
        "agent_type": agent_type,
        "metadata": payload.get("metadata", {}),
        "created_at": payload.get("created_at"),
        "path": source,
    }


def train_rl_agent(
    symbol: str,
    episodes: int = 60,
    force: bool = False,
    persist: bool = True,
    agent_type: str = "q",
) -> Dict[str, Any]:
    normalized = normalize_symbol(symbol)
    episodes = max(5, min(int(episodes), 500))
    agent_type = str(agent_type or "q").lower()
    if persist and not force:
        existing = load_agent(normalized)
        if existing and existing.get("agent_type", "q") == agent_type:
            return {
                "symbol": normalized,
                "trained": False,
                "message": "Existing trained RL policy reused",
                "created_at": existing["created_at"],
                "metadata": existing["metadata"],
                "agent_type": existing.get("agent_type"),
            }

    history = _load_history(normalized)
    if history.empty or len(history) < 130:
        return {
            "symbol": normalized,
            "error": f"Not enough market history to train RL agent for {normalized}",
        }

    train_history, test_history = _split_history(history)
    if agent_type == "dqn":
        try:
            from rl.dqn_agent import DQNTradingAgent

            agent = DQNTradingAgent.from_dict({}) if hasattr(DQNTradingAgent, "from_dict") else DQNTradingAgent()
            training = agent.train_from_history(train_history, episodes=episodes)
            train_backtest = agent.evaluate(train_history)
            test_backtest = agent.evaluate(test_history)
        except Exception:
            return {
                "symbol": normalized,
                "error": "DQN support not available in this environment",
            }
    else:
        agent = QLearningTradingAgent(seed=abs(hash(normalized)) % (2**32))
        training = agent.train(train_history, episodes=episodes)
        train_backtest = agent.evaluate(train_history)
        test_backtest = agent.evaluate(test_history)
    metadata = {
        "episodes": episodes,
        "agent_type": agent_type,
        "training": training,
        "train_backtest": train_backtest,
        "test_backtest": test_backtest,
        "train_rows": len(train_history),
        "test_rows": len(test_history),
    }
    if persist:
        _save_agent(normalized, agent, metadata)

    return {
        "symbol": normalized,
        "trained": True,
        "persisted": persist,
        "message": "RL policy trained and saved" if persist else "RL policy trained without saving",
        "metadata": metadata,
    }


def backtest_rl_agent(symbol: str) -> Dict[str, Any]:
    normalized = normalize_symbol(symbol)
    loaded = load_agent(normalized)
    if not loaded:
        trained = train_rl_agent(normalized, episodes=60, force=True)
        if trained.get("error"):
            return trained
        loaded = load_agent(normalized)

    history = _load_history(normalized)
    if history.empty or len(history) < 80:
        return {
            "symbol": normalized,
            "error": f"Not enough market history to backtest RL agent for {normalized}",
        }

    agent = loaded["agent"]
    full_backtest = agent.evaluate(history)
    _, test_history = _split_history(history)
    holdout_backtest = agent.evaluate(test_history)

    return {
        "symbol": normalized,
        "created_at": loaded["created_at"],
        "full_backtest": full_backtest,
        "holdout_backtest": holdout_backtest,
        "grade": _policy_grade(holdout_backtest),
        "metadata": loaded["metadata"],
    }


def get_agent_status(symbol: str) -> Dict[str, Any]:
    normalized = normalize_symbol(symbol)
    loaded = load_agent(normalized)
    if not loaded:
        return {"symbol": normalized, "trained": False}
    return {
        "symbol": normalized,
        "trained": True,
        "created_at": loaded["created_at"],
        "metadata": loaded["metadata"],
    }


def train_rl_batch(
    symbols: Iterable[str] | None = None,
    episodes: int = 60,
    force: bool = False,
    agent_type: str = "q",
) -> Dict[str, Any]:
    results = []
    for symbol in _normalise_symbols(symbols):
        result = train_rl_agent(symbol, episodes=episodes, force=force, persist=True, agent_type=agent_type)
        results.append(result)
    trained = sum(1 for item in results if item.get("trained"))
    errors = [item for item in results if item.get("error")]
    return {
        "count": len(results),
        "trained": trained,
        "errors": errors,
        "results": results,
    }


def get_rl_leaderboard(symbols: Iterable[str] | None = None) -> Dict[str, Any]:
    rows = []
    for symbol in _normalise_symbols(symbols):
        recommendation = get_rl_recommendation(symbol)
        if recommendation.get("error"):
            rows.append({
                "symbol": normalize_symbol(symbol),
                "trained": False,
                "error": recommendation["error"],
            })
            continue

        holdout = recommendation.get("holdout_backtest") or {}
        full = recommendation.get("backtest") or {}
        ranking_backtest = holdout or full
        rows.append({
            "symbol": recommendation["symbol"],
            "trained": True,
            "action": recommendation["action"],
            "confidence": recommendation["confidence"],
            "risk": recommendation["risk"],
            "grade": _policy_grade(ranking_backtest),
            "score": ranking_backtest.get("stability_score", 0),
            "strategy_return": ranking_backtest.get("strategy_return", 0),
            "buy_hold_return": ranking_backtest.get("buy_hold_return", 0),
            "excess_return": ranking_backtest.get("excess_return", 0),
            "max_drawdown": ranking_backtest.get("max_drawdown", 0),
            "sharpe": ranking_backtest.get("sharpe", 0),
            "trades": ranking_backtest.get("trades", 0),
            "created_at": recommendation.get("created_at"),
        })

    rows.sort(key=lambda item: float(item.get("score") or -999), reverse=True)
    return {
        "count": len(rows),
        "leaderboard": rows,
    }


@lru_cache(maxsize=64)
def get_rl_recommendation(symbol: str) -> Dict[str, Any]:
    normalized = normalize_symbol(symbol)
    loaded = load_agent(normalized)
    if not loaded:
        trained = train_rl_agent(normalized, episodes=60, force=True)
        if trained.get("error"):
            return {
                "symbol": normalized,
                "action": "HOLD",
                "confidence": 0.0,
                "expected_reward": 0.0,
                "risk": "HIGH",
                "error": trained["error"],
            }
        loaded = load_agent(normalized)

    history = _load_history(normalized)
    if history.empty or len(history) < 80:
        return {
            "symbol": normalized,
            "action": "HOLD",
            "confidence": 0.0,
            "expected_reward": 0.0,
            "risk": "HIGH",
            "error": f"Not enough market history to train RL agent for {normalized}",
        }

    agent = loaded["agent"]
    evaluation = agent.evaluate(history)
    recommendation = agent.recommend(history)
    strategy_return = float(evaluation["strategy_return"])
    buy_hold_return = float(evaluation["buy_hold_return"])

    return {
        "symbol": normalized,
        "action": recommendation["action"],
        "confidence": recommendation["confidence"],
        "expected_reward": recommendation["expected_reward"],
        "risk": _risk_from_return_gap(strategy_return, buy_hold_return),
        "created_at": loaded["created_at"],
        "backtest": evaluation,
        "holdout_backtest": loaded["metadata"].get("test_backtest"),
        "training": loaded["metadata"].get("training"),
        "grade": _policy_grade(loaded["metadata"].get("test_backtest") or evaluation),
        "q_values": recommendation["q_values"],
        "method": "Persisted DQN paper-trading simulator" if loaded.get("agent_type") == "dqn" else "Persisted tabular Q-learning paper-trading simulator",
    }
