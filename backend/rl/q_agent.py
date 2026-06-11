from __future__ import annotations

from collections import defaultdict
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from rl.trading_env import ACTIONS, TradingEnvironment, softmax


State = Tuple[int, int, int, int]


class QLearningTradingAgent:
    """Tabular Q-learning agent for a discrete trading policy."""

    def __init__(
        self,
        learning_rate: float = 0.12,
        discount: float = 0.92,
        epsilon: float = 0.22,
        epsilon_decay: float = 0.94,
        min_epsilon: float = 0.03,
        seed: int = 42,
    ):
        self.learning_rate = learning_rate
        self.discount = discount
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.rng = np.random.default_rng(seed)
        self.q_table: Dict[State, np.ndarray] = defaultdict(lambda: np.zeros(len(ACTIONS)))

    def choose_action(self, state: State, explore: bool = True) -> int:
        if explore and self.rng.random() < self.epsilon:
            return int(self.rng.integers(0, len(ACTIONS)))
        return int(np.argmax(self.q_table[state]))

    def train(self, history: pd.DataFrame, episodes: int = 35) -> Dict[str, float]:
        episode_rewards = []
        final_values = []

        for _ in range(episodes):
            env = TradingEnvironment(history)
            state = env.reset()
            total_reward = 0.0

            while True:
                action = self.choose_action(state, explore=True)
                result = env.step(action)
                old_q = self.q_table[state][action]
                future_q = float(np.max(self.q_table[result.state]))
                self.q_table[state][action] = old_q + self.learning_rate * (
                    result.reward + self.discount * future_q - old_q
                )
                state = result.state
                total_reward += result.reward
                if result.done:
                    final_values.append(result.info["net_worth"])
                    break

            episode_rewards.append(total_reward)
            self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

        return {
            "episodes": episodes,
            "avg_episode_reward": float(np.mean(episode_rewards)) if episode_rewards else 0.0,
            "avg_final_value": float(np.mean(final_values)) if final_values else 0.0,
        }

    def evaluate(self, history: pd.DataFrame) -> Dict[str, float | str]:
        env = TradingEnvironment(history)
        state = env.reset()
        trades = 0
        equity_curve = [env.net_worth()]

        while True:
            action = self.choose_action(state, explore=False)
            if action in (1, 2):
                trades += 1
            result = env.step(action)
            equity_curve.append(float(result.info["net_worth"]))
            state = result.state
            if result.done:
                final_value = result.info["net_worth"]
                break

        equity = np.array(equity_curve, dtype=float)
        returns = np.diff(equity) / np.maximum(equity[:-1], 1)
        running_peak = np.maximum.accumulate(equity)
        drawdowns = (equity - running_peak) / np.maximum(running_peak, 1)
        max_drawdown = float(np.min(drawdowns)) if len(drawdowns) else 0.0
        sharpe = 0.0
        if len(returns) > 1 and float(np.std(returns)) > 1e-9:
            sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252))

        strategy_return = (final_value - env.initial_cash) / env.initial_cash
        buy_hold_return = env.buy_and_hold_return()
        excess_return = strategy_return - buy_hold_return
        stability_score = strategy_return + max_drawdown * 0.7 + sharpe * 0.03
        return {
            "final_value": round(float(final_value), 2),
            "strategy_return": round(float(strategy_return), 4),
            "buy_hold_return": round(float(buy_hold_return), 4),
            "excess_return": round(float(excess_return), 4),
            "max_drawdown": round(float(max_drawdown), 4),
            "sharpe": round(float(sharpe), 3),
            "stability_score": round(float(stability_score), 4),
            "trades": trades,
        }

    def recommend(self, history: pd.DataFrame) -> Dict[str, float | str | Dict[str, float]]:
        env = TradingEnvironment(history)
        state = env.reset()
        env.index = len(env.data) - 1
        state = env._state()
        q_values = self.q_table[state]
        probabilities = softmax(q_values)
        action_idx = int(np.argmax(q_values))

        return {
            "action": ACTIONS[action_idx],
            "confidence": round(float(probabilities[action_idx]), 2),
            "expected_reward": round(float(q_values[action_idx]), 5),
            "q_values": {
                ACTIONS[idx]: round(float(value), 5)
                for idx, value in enumerate(q_values)
            },
        }

    def to_dict(self) -> Dict[str, object]:
        return {
            "learning_rate": self.learning_rate,
            "discount": self.discount,
            "epsilon": self.epsilon,
            "epsilon_decay": self.epsilon_decay,
            "min_epsilon": self.min_epsilon,
            "q_table": {
                "|".join(str(part) for part in state): values.tolist()
                for state, values in self.q_table.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "QLearningTradingAgent":
        agent = cls(
            learning_rate=float(payload.get("learning_rate", 0.12)),
            discount=float(payload.get("discount", 0.92)),
            epsilon=float(payload.get("epsilon", 0.03)),
            epsilon_decay=float(payload.get("epsilon_decay", 0.94)),
            min_epsilon=float(payload.get("min_epsilon", 0.03)),
        )
        raw_table = payload.get("q_table", {})
        if isinstance(raw_table, dict):
            for key, values in raw_table.items():
                state = tuple(int(part) for part in str(key).split("|"))
                if len(state) == 4 and isinstance(values, list):
                    agent.q_table[state] = np.array(values, dtype=float)
        return agent
