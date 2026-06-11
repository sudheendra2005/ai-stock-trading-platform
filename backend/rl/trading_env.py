from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd


ACTIONS = {
    0: "HOLD",
    1: "BUY",
    2: "SELL",
}


@dataclass
class StepResult:
    state: Tuple[int, int, int, int]
    reward: float
    done: bool
    info: Dict[str, float]


class TradingEnvironment:
    """Small discrete paper-trading environment for tabular Q-learning.

    The agent sees technical market buckets plus its position state, then picks
    HOLD, BUY, or SELL. Rewards are based on portfolio value changes with a
    small trade penalty to discourage churn.
    """

    def __init__(
        self,
        history: pd.DataFrame,
        initial_cash: float = 100000.0,
        trade_fraction: float = 0.25,
        transaction_cost: float = 0.001,
    ):
        self.initial_cash = initial_cash
        self.trade_fraction = trade_fraction
        self.transaction_cost = transaction_cost
        self.data = self._prepare(history)
        self.index = 0
        self.cash = initial_cash
        self.shares = 0.0
        self.last_net_worth = initial_cash

    def _prepare(self, history: pd.DataFrame) -> pd.DataFrame:
        d = history.copy()
        close = d["Close"].astype(float)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        d["rsi"] = 100 - (100 / (1 + rs))
        d["ma_10"] = close.rolling(10).mean()
        d["ma_30"] = close.rolling(30).mean()
        d["trend"] = d["ma_10"] / (d["ma_30"] + 1e-9) - 1
        d["returns"] = close.pct_change()
        d["volatility"] = d["returns"].rolling(20).std()
        d = d.dropna(subset=["Close", "rsi", "trend", "volatility"]).reset_index(drop=True)
        if len(d) < 40:
            raise ValueError("Need at least 40 prepared rows for RL simulation")
        return d

    def reset(self) -> Tuple[int, int, int, int]:
        self.index = 0
        self.cash = self.initial_cash
        self.shares = 0.0
        self.last_net_worth = self.initial_cash
        return self._state()

    def current_price(self) -> float:
        return float(self.data.iloc[self.index]["Close"])

    def net_worth(self) -> float:
        return self.cash + self.shares * self.current_price()

    def _state(self) -> Tuple[int, int, int, int]:
        row = self.data.iloc[self.index]
        trend_bucket = 0 if row["trend"] < -0.015 else 2 if row["trend"] > 0.015 else 1
        rsi_bucket = 0 if row["rsi"] < 35 else 2 if row["rsi"] > 65 else 1
        vol_bucket = 0 if row["volatility"] < 0.012 else 2 if row["volatility"] > 0.028 else 1
        position_value = self.shares * self.current_price()
        exposure = position_value / max(self.net_worth(), 1)
        position_bucket = 0 if exposure < 0.05 else 2 if exposure > 0.65 else 1
        return (trend_bucket, rsi_bucket, vol_bucket, position_bucket)

    def step(self, action: int) -> StepResult:
        action = int(action)
        price = self.current_price()
        before = self.net_worth()
        traded = False

        if action == 1 and self.cash > price:
            budget = self.cash * self.trade_fraction
            shares_to_buy = budget / price
            cost = shares_to_buy * price
            fee = cost * self.transaction_cost
            if self.cash >= cost + fee:
                self.cash -= cost + fee
                self.shares += shares_to_buy
                traded = True
        elif action == 2 and self.shares > 0:
            shares_to_sell = self.shares * self.trade_fraction
            proceeds = shares_to_sell * price
            fee = proceeds * self.transaction_cost
            self.cash += proceeds - fee
            self.shares -= shares_to_sell
            traded = True

        self.index += 1
        done = self.index >= len(self.data) - 1
        after = self.net_worth()
        reward = (after - before) / max(before, 1)
        if traded:
            reward -= self.transaction_cost

        self.last_net_worth = after
        return StepResult(
            state=self._state(),
            reward=float(reward),
            done=done,
            info={
                "net_worth": float(after),
                "cash": float(self.cash),
                "shares": float(self.shares),
                "price": float(self.current_price()),
            },
        )

    def buy_and_hold_return(self) -> float:
        first = float(self.data.iloc[0]["Close"])
        last = float(self.data.iloc[-1]["Close"])
        return (last - first) / first if first else 0.0


def softmax(values: np.ndarray) -> np.ndarray:
    scaled = values - np.max(values)
    exp = np.exp(scaled)
    total = np.sum(exp)
    return exp / total if total else np.ones_like(values) / len(values)
