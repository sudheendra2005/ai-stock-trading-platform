from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from rl.trading_env import TradingEnvironment, ACTIONS


class DQNNet(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class Transition:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


class DQNTradingAgent:
    def __init__(
        self,
        input_dim: int = 4,
        lr: float = 1e-3,
        gamma: float = 0.99,
        buffer_size: int = 50_000,
        batch_size: int = 64,
        epsilon_start: float = 1.0,
        epsilon_final: float = 0.05,
        epsilon_decay: int = 5000,
        device: str | torch.device = None,
    ):
        self.device = device or (torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu"))
        self.agent_type = "dqn"
        self.net = DQNNet(input_dim, len(ACTIONS)).to(self.device)
        self.target = DQNNet(input_dim, len(ACTIONS)).to(self.device)
        self.target.load_state_dict(self.net.state_dict())
        self.optimizer = optim.Adam(self.net.parameters(), lr=lr)
        self.gamma = gamma
        self.buffer = deque(maxlen=buffer_size)
        self.batch_size = batch_size
        self.epsilon_start = epsilon_start
        self.epsilon_final = epsilon_final
        self.epsilon_decay = epsilon_decay
        self.steps = 0

    def act(self, state: np.ndarray, eval_mode: bool = False) -> int:
        eps = self.epsilon_final if eval_mode else self.epsilon_start + (self.epsilon_final - self.epsilon_start) * min(1.0, self.steps / self.epsilon_decay)
        self.steps += 1
        if random.random() < eps:
            return random.randrange(len(ACTIONS))
        with torch.no_grad():
            s = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            q = self.net(s)
            return int(q.argmax().item())

    def store(self, transition: Transition) -> None:
        self.buffer.append(transition)

    def sample(self) -> list[Transition]:
        return random.sample(self.buffer, min(len(self.buffer), self.batch_size))

    def update(self, tau: float = 0.005) -> dict:
        if len(self.buffer) < self.batch_size:
            return {}
        batch = self.sample()
        states = torch.tensor(np.vstack([b.state for b in batch]), dtype=torch.float32, device=self.device)
        actions = torch.tensor([b.action for b in batch], dtype=torch.long, device=self.device).unsqueeze(1)
        rewards = torch.tensor([b.reward for b in batch], dtype=torch.float32, device=self.device).unsqueeze(1)
        next_states = torch.tensor(np.vstack([b.next_state for b in batch]), dtype=torch.float32, device=self.device)
        dones = torch.tensor([b.done for b in batch], dtype=torch.float32, device=self.device).unsqueeze(1)

        q_values = self.net(states).gather(1, actions)
        with torch.no_grad():
            next_q = self.target(next_states).max(1)[0].unsqueeze(1)
            target = rewards + (1.0 - dones) * self.gamma * next_q

        loss = nn.functional.mse_loss(q_values, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # Soft update
        for p, tp in zip(self.net.parameters(), self.target.parameters()):
            tp.data.mul_(1 - tau)
            tp.data.add_(p.data * tau)

        return {"loss": float(loss.item())}

    def train_from_history(self, history, episodes: int = 100, max_steps: int = 512):
        stats = {"episodes": episodes, "avg_reward": 0.0}
        rewards = []
        for ep in range(episodes):
            env = TradingEnvironment(history)
            state = np.array(env.reset(), dtype=float)
            total = 0.0
            for step in range(max_steps):
                action = self.act(state)
                result = env.step(action)
                next_state = np.array(result.state, dtype=float)
                self.store(Transition(state, action, result.reward, next_state, result.done))
                state = next_state
                total += result.reward
                self.update()
                if result.done:
                    break
            rewards.append(total)
        stats["avg_reward"] = float(np.mean(rewards) if rewards else 0.0)
        return stats

    def save(self, path: str):
        torch.save({"net": self.net.state_dict(), "target": self.target.state_dict()}, path)

    def load(self, path: str):
        data = torch.load(path, map_location=self.device)
        self.net.load_state_dict(data.get("net", {}))
        self.target.load_state_dict(data.get("target", {}))

    def evaluate(self, history):
        env = TradingEnvironment(history)
        state = env.reset()
        trades = 0
        equity_curve = [env.net_worth()]

        while True:
            action = self.act(np.array(state, dtype=float), eval_mode=True)
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

    def recommend(self, history):
        env = TradingEnvironment(history)
        env.reset()
        env.index = len(env.data) - 1
        state = env._state()
        s = torch.tensor(np.array(state, dtype=float), dtype=torch.float32, device=self.device).unsqueeze(0)
        with torch.no_grad():
            q = self.net(s).cpu().numpy().flatten()
        scaled = q - np.max(q)
        exp = np.exp(scaled)
        total = np.sum(exp)
        probs = exp / total if total else np.ones_like(q) / len(q)
        action_idx = int(np.argmax(q))
        return {
            "action": ACTIONS[action_idx],
            "confidence": round(float(probs[action_idx]), 2),
            "expected_reward": round(float(q[action_idx]), 5),
            "q_values": {ACTIONS[i]: round(float(val), 5) for i, val in enumerate(q)},
        }

    def to_dict(self) -> dict:
        return {
            "input_dim": int(self.net.net[0].in_features) if hasattr(self.net, "net") else 4,
            "batch_size": int(self.batch_size),
            "epsilon_start": float(self.epsilon_start),
            "epsilon_final": float(self.epsilon_final),
            "epsilon_decay": int(self.epsilon_decay),
            "gamma": float(self.gamma),
            "agent_type": "dqn",
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "DQNTradingAgent":
        return cls(
            input_dim=int(payload.get("input_dim", 4)),
            lr=float(payload.get("lr", 1e-3)),
            gamma=float(payload.get("gamma", 0.99)),
            buffer_size=int(payload.get("buffer_size", 50_000)),
            batch_size=int(payload.get("batch_size", 64)),
            epsilon_start=float(payload.get("epsilon_start", 1.0)),
            epsilon_final=float(payload.get("epsilon_final", 0.05)),
            epsilon_decay=int(payload.get("epsilon_decay", 5000)),
        )
