from __future__ import annotations

import os
import time
import logging
import signal
from typing import Iterable, List

from rl.agent_service import train_rl_batch, DEFAULT_RL_SYMBOLS
from prediction.stock_predictor import stock_predictor
from services.market_capture import capture_market_snapshots

LOG_LEVEL = os.getenv("TRAINER_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("rl.trainer")

shutdown = False


def _handle_signal(signum, frame):
    global shutdown
    logger.info("Received signal %s, shutting down trainer...", signum)
    shutdown = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def _normalize_symbols(env_val: str | None) -> List[str] | None:
    if not env_val:
        return None
    return [s.strip() for s in env_val.split(",") if s.strip()]


def retrain_ml_for_symbols(symbols: Iterable[str]):
    for s in symbols:
        try:
            logger.info("Retraining ML predictor for %s", s)
            prediction = stock_predictor.get_prediction(s)
            logger.info("ML %s: %s", s, prediction)
        except Exception:
            logger.exception("ML retrain failed for %s", s)


def run_cycle(symbols: List[str] | None, episodes: int, force: bool):
    logger.info(
        "Starting RL training cycle: episodes=%s force=%s symbols=%s",
        episodes,
        force,
        symbols or "ALL",
    )
    try:
        capture = capture_market_snapshots(symbols or DEFAULT_RL_SYMBOLS)
        logger.info("Market capture result: %s", capture)
        agent_type = os.getenv("RL_AGENT_TYPE", "q").lower()
        result = train_rl_batch(symbols=symbols, episodes=episodes, force=force, agent_type=agent_type)
        logger.info("RL batch training result: %s", result)
    except Exception:
        logger.exception("RL batch training failed")

    ml_symbols = symbols if symbols else DEFAULT_RL_SYMBOLS
    retrain_ml_for_symbols(ml_symbols)


def main():
    interval = max(60, int(os.getenv("TRAIN_INTERVAL_SECONDS", "21600")))
    episodes = max(5, int(os.getenv("RL_EPISODES", "60")))
    force = str(os.getenv("FORCE_RETRAIN", "false")).lower() in ("1", "true", "yes")
    symbols_env = os.getenv("RL_SYMBOLS")
    symbols = _normalize_symbols(symbols_env)

    run_once = str(os.getenv("TRAIN_ONCE", "false")).lower() in ("1", "true", "yes")
    logger.info(
        "Trainer starting (interval=%s, episodes=%s, force=%s, symbols=%s, run_once=%s)",
        interval,
        episodes,
        force,
        symbols or "ALL",
        run_once,
    )

    if run_once:
        run_cycle(symbols, episodes, force)
        return

    while not shutdown:
        run_cycle(symbols, episodes, force)
        if shutdown:
            break
        logger.info("Trainer sleeping for %s seconds", interval)
        try:
            time.sleep(interval)
        except Exception:
            # interrupted by signal
            if shutdown:
                break


if __name__ == "__main__":
    main()
