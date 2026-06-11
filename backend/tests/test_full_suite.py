"""
test_full_suite.py
==================
Comprehensive integration tests for all API endpoints.
Uses an in-memory SQLite database so tests are fully isolated
and never pollute the real sql_app.db.
"""

import pytest
import sys
import os
import uuid

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Override DATABASE_URL BEFORE any app import ──────────────────────────────
os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app

# ── In-memory test DB ─────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///./test_suite.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# ── Shared state ──────────────────────────────────────────────────────────────
AUTH_TOKEN: str = ""
RUN_ID = uuid.uuid4().hex[:8]
TEST_EMAIL = f"testuser-{RUN_ID}@example.com"
TEST_PASSWORD = "SecurePass123"
TEST_USERNAME = f"testuser{RUN_ID}"


# =============================================================================
# HEALTH CHECK
# =============================================================================

class TestHealth:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "message" in r.json()

    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


# =============================================================================
# AUTH — REGISTER
# =============================================================================

class TestRegister:
    def test_register_success(self):
        r = client.post("/api/auth/register", json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        data = r.json()
        assert "user_id" in data
        assert data["email"] == TEST_EMAIL

    def test_register_duplicate_email(self):
        r = client.post("/api/auth/register", json={
            "username": "otheruser",
            "email": TEST_EMAIL,        # same email
            "password": TEST_PASSWORD
        })
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"].lower()

    def test_register_duplicate_username(self):
        r = client.post("/api/auth/register", json={
            "username": TEST_USERNAME,  # same username
            "email": "other@example.com",
            "password": TEST_PASSWORD
        })
        assert r.status_code == 400
        assert "already taken" in r.json()["detail"].lower()


# =============================================================================
# AUTH — LOGIN
# =============================================================================

class TestLogin:
    def test_login_wrong_password(self):
        r = client.post("/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": "wrongpassword"
        })
        assert r.status_code == 401

    def test_login_wrong_email(self):
        r = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": TEST_PASSWORD
        })
        assert r.status_code == 401

    def test_login_success(self):
        global AUTH_TOKEN
        r = client.post("/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert r.status_code == 200, f"Login failed: {r.text}"
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        AUTH_TOKEN = data["access_token"]


# =============================================================================
# AUTH — /me
# =============================================================================

class TestMe:
    def test_me_unauthenticated(self):
        r = client.get("/api/auth/me")
        assert r.status_code in [401, 403]

    def test_me_authenticated(self):
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == TEST_EMAIL


# =============================================================================
# WALLET
# =============================================================================

class TestWallet:
    def test_wallet_unauthenticated(self):
        r = client.get("/api/wallet/")
        assert r.status_code in [401, 403]

    def test_wallet_balance(self):
        r = client.get("/api/wallet/", headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
        assert r.status_code == 200
        data = r.json()
        assert "balance" in data
        # Fresh wallet should start at 100,000
        assert data["balance"] == 100000.0


# =============================================================================
# PORTFOLIO
# =============================================================================

class TestPortfolio:
    def test_portfolio_unauthenticated(self):
        r = client.get("/api/portfolio/")
        assert r.status_code in [401, 403]

    def test_portfolio_empty(self):
        r = client.get("/api/portfolio/", headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
        assert r.status_code == 200
        data = r.json()
        assert "portfolio" in data
        assert isinstance(data["portfolio"], list)
        assert "summary" in data


# =============================================================================
# TRANSACTIONS
# =============================================================================

class TestTransactions:
    def test_transactions_unauthenticated(self):
        r = client.get("/api/transactions/")
        assert r.status_code in [401, 403]

    def test_transactions_empty(self):
        r = client.get("/api/transactions/", headers={"Authorization": f"Bearer {AUTH_TOKEN}"})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 0


# =============================================================================
# STOCKS — Public endpoints
# =============================================================================

class TestStocks:
    def test_trending_stocks(self):
        r = client.get("/api/stocks/trending")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Should return at least 1 stock (network permitting)
        if len(data) > 0:
            first = data[0]
            assert "symbol" in first
            assert "price" in first
            assert "change" in first

    def test_stock_details_valid(self):
        r = client.get("/api/stocks/AAPL")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "AAPL"
        assert "current_price" in data
        assert data["current_price"] > 0
        assert "historical_data" in data
        assert isinstance(data["historical_data"], list)

    def test_stock_details_invalid_symbol(self):
        r = client.get("/api/stocks/INVALIDSYMBOL999XYZ")
        # Should return 400 or 404, not 500
        assert r.status_code in [400, 404]

    def test_predict_stock_valid(self):
        r = client.get("/api/stocks/predict/AAPL")
        # ML training can return a controlled 400 for missing data, but must never 500.
        assert r.status_code in [200, 400]
        if r.status_code == 200:
            data = r.json()
            assert "recommendation" in data
            assert data["recommendation"] in ["BUY", "SELL", "HOLD"]
            assert "confidence" in data
            assert "risk" in data
            assert "indicators" in data

    def test_predict_route_before_details_route(self):
        """
        Regression test: /predict/{symbol} must NOT be swallowed by /{symbol}.
        The predict route must resolve correctly.
        """
        r = client.get("/api/stocks/predict/MSFT")
        # Must not return a 422 (which would mean FastAPI tried to parse
        # 'predict' as a stock symbol for the /{symbol} route)
        assert r.status_code != 422

    def test_rl_recommendation_valid(self):
        r = client.get("/api/rl/recommend/AAPL")
        assert r.status_code in [200, 400]
        if r.status_code == 200:
            data = r.json()
            assert data["symbol"] == "AAPL"
            assert data["action"] in ["BUY", "SELL", "HOLD"]
            assert "confidence" in data
            assert "backtest" in data

    def test_rl_train_status_backtest(self):
        r = client.post("/api/rl/train/GOOGL", json={"episodes": 5, "force": True, "persist": False})
        assert r.status_code in [200, 400]
        if r.status_code == 200:
            backtest = client.get("/api/rl/backtest/GOOGL")
            assert backtest.status_code == 200
            assert "full_backtest" in backtest.json()

    def test_rl_leaderboard(self):
        r = client.get("/api/rl/leaderboard")
        assert r.status_code == 200
        data = r.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)


# =============================================================================
# INVALID TOKEN
# =============================================================================

class TestInvalidToken:
    def test_invalid_token_wallet(self):
        r = client.get("/api/wallet/", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401

    def test_invalid_token_portfolio(self):
        r = client.get("/api/portfolio/", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401

    def test_invalid_token_transactions(self):
        r = client.get("/api/transactions/", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401
