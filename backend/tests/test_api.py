import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the backend directory to the path so we can import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

client = TestClient(app)

def test_trending_stocks():
    response = client.get("/api/stocks/trending")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_stock_details():
    # Test a known stock symbol, e.g., AAPL
    response = client.get("/api/stocks/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert "current_price" in data

def test_wallet_balance_unauthorized():
    # Wallet requires auth, so without it, it should return 401 or 403
    response = client.get("/api/wallet")
    assert response.status_code in [401, 403]

def test_predict_stock():
    # Test prediction endpoint
    response = client.get("/api/stocks/predict/AAPL")
    # Even if prediction might fail, it shouldn't 500, but rather return a valid structured response or 400
    assert response.status_code in [200, 400]


def test_rl_recommendation():
    response = client.get("/api/rl/recommend/AAPL")
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        data = response.json()
        assert data["action"] in ["BUY", "SELL", "HOLD"]
        assert "confidence" in data
        assert "backtest" in data


def test_rl_train_status_and_backtest():
    train = client.post("/api/rl/train/MSFT", json={"episodes": 5, "force": True, "persist": False})
    assert train.status_code in [200, 400]
    if train.status_code == 200:
        backtest = client.get("/api/rl/backtest/MSFT")
        assert backtest.status_code == 200
        assert "holdout_backtest" in backtest.json()


def test_rl_leaderboard_and_batch_train():
    batch = client.post(
        "/api/rl/train-batch",
        json={"symbols": ["AAPL", "MSFT"], "episodes": 5, "force": False},
    )
    assert batch.status_code == 200
    assert "results" in batch.json()

    leaderboard = client.get("/api/rl/leaderboard")
    assert leaderboard.status_code == 200
    data = leaderboard.json()
    assert "leaderboard" in data
    if data["leaderboard"]:
        first = data["leaderboard"][0]
        assert "symbol" in first
        assert "score" in first
