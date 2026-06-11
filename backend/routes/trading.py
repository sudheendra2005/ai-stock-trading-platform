"""
trading.py — Unified trading router
Exposes /api/trading/* endpoints that the frontend Dashboard expects.
Maps:
  GET  /api/trading/dashboard       → trending stocks (for watchlist)
  GET  /api/trading/wallet          → wallet balance
  GET  /api/trading/portfolio       → portfolio
  GET  /api/trading/transactions    → transaction history
  GET  /api/trading/predict/{sym}   → AI prediction
  POST /api/trading/trade           → buy or sell (side: BUY | SELL)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import JWTError, jwt
from typing import Dict, Any, List

from config import settings
from database import get_db
from models import User, Wallet, Portfolio, Transaction
from services.auth_service import get_user_by_email
from prediction.stock_predictor import stock_predictor
from services.market_data import latest_price, normalize_symbol, stock_summary
from pathlib import Path
import json
import difflib

router = APIRouter()

# ---------------------------------------------------------------------------
# Auth helper (shared across all endpoints in this file)
# ---------------------------------------------------------------------------
def get_current_user(token: str = Depends(HTTPBearer()), db: Session = Depends(get_db)) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise exc
    except JWTError:
        raise exc
    user = get_user_by_email(db, email=email)
    if user is None:
        raise exc
    return user


def _ensure_wallet(user_id: int, db: Session) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=100_000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


# ---------------------------------------------------------------------------
# GET /api/trading/dashboard  — trending stocks for the watchlist
# ---------------------------------------------------------------------------
TRENDING = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
]

@router.get("/dashboard")
async def get_dashboard():
    """Returns trending stocks for the watchlist cards."""
    trending_stocks = []
    for symbol in TRENDING[:6]:
        data = stock_summary(symbol, period="5d")
        if data:
            trending_stocks.append({
                "symbol":  data["symbol"],
                "name":    data["name"],
                "price":   data["price"],
                "change":  data["change"],
                "volume":  data["volume"],
            })
    return {"trending_stocks": trending_stocks}


# ---------------------------------------------------------------------------
# GET /api/trading/wallet
# ---------------------------------------------------------------------------
@router.get("/wallet")
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = _ensure_wallet(current_user.id, db)
    return {"balance": round(wallet.balance, 2), "user_id": current_user.id}


# ---------------------------------------------------------------------------
# GET /api/trading/portfolio
# ---------------------------------------------------------------------------
@router.get("/portfolio")
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    portfolio_data = []
    total_inv = total_val = 0.0
    for item in items:
        cur_price = latest_price(item.stock_symbol) or item.buy_price
        qty = item.quantity
        inv = item.buy_price * qty
        val = cur_price * qty
        pl  = val - inv
        portfolio_data.append({
            "id": item.id,
            "stock_symbol": item.stock_symbol,
            "quantity": qty,
            "buy_price": round(item.buy_price, 2),
            "current_price": round(cur_price, 2),
            "investment": round(inv, 2),
            "current_value": round(val, 2),
            "profit_loss": round(pl, 2),
            "profit_loss_percent": round(pl / inv * 100 if inv else 0, 2),
        })
        total_inv += inv
        total_val += val
    return {
        "portfolio": portfolio_data,
        "summary": {
            "total_investment": round(total_inv, 2),
            "total_current_value": round(total_val, 2),
            "total_profit_loss": round(total_val - total_inv, 2),
            "total_profit_loss_percent": round((total_val - total_inv) / total_inv * 100 if total_inv else 0, 2),
        },
    }


# ---------------------------------------------------------------------------
# GET /api/trading/transactions
# ---------------------------------------------------------------------------
@router.get("/transactions")
async def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return [
        {
            "id": tx.id,
            "stock_symbol": tx.stock_symbol,
            "action": tx.action,
            "quantity": tx.quantity,
            "price": round(tx.price, 2),
            "total": round(tx.price * tx.quantity, 2),
            "created_at": tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for tx in txs
    ]


# ---------------------------------------------------------------------------
# GET /api/trading/predict/{symbol}
# ---------------------------------------------------------------------------
@router.get("/predict/{symbol}")
def get_prediction(symbol: str):
    q = normalize_symbol(symbol)

    # Try direct prediction first
    try:
        prediction = stock_predictor.get_prediction(q)
        if not prediction.get("error"):
            # Enrich response with symbol/name for frontend compatibility
            summary = stock_summary(q) or {}
            resp = {"symbol": q, "name": summary.get("name") or q, **prediction}
            return resp
    except Exception:
        prediction = {"error": "direct lookup failed"}

    # Load local tickers (backend/data/tickers.json) and fallback symbol-name map
    def _load_tickers_map() -> dict:
        base = Path(__file__).resolve().parents[1]
        candidates = [
            base / 'data' / 'tickers.json',            # backend/data/tickers.json
            base / 'app' / 'data' / 'tickers.json',    # backend/app/data/tickers.json (if present)
        ]
        mapping = {}
        for p in candidates:
            try:
                if p.exists():
                    with open(p, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                        if isinstance(data, dict):
                            for s, n in data.items():
                                mapping[s.upper()] = n
                        elif isinstance(data, list):
                            for item in data:
                                sym = (item.get('symbol') or item.get('ticker') or '').strip()
                                name = (item.get('name') or item.get('company') or '').strip()
                                if sym and name:
                                    mapping[sym.upper()] = name
            except Exception:
                continue
        # Merge with built-in names from market_data
        try:
            from services.market_data import SYMBOL_NAMES as _SN
            for s, n in _SN.items():
                mapping.setdefault(s.upper(), n)
        except Exception:
            pass
        return mapping

    tickers_map = _load_tickers_map()

    # Try fuzzy / name-based lookup
    search_space = list(tickers_map.keys()) + [v.upper() for v in tickers_map.values()]
    candidates = difflib.get_close_matches(q, search_space, n=1, cutoff=0.5)
    mapped_sym = None
    if candidates:
        m = candidates[0]
        if m in tickers_map:
            mapped_sym = m
        else:
            # find symbol by matching name
            for s, n in tickers_map.items():
                if n.upper() == m:
                    mapped_sym = s
                    break

    # Try appending .NS as a last resort
    if not mapped_sym:
        if not q.endswith('.NS') and not q.endswith('.BO'):
            trial = f"{q}.NS"
            mapped_sym = trial

    if mapped_sym:
        try:
            prediction = stock_predictor.get_prediction(mapped_sym)
            if not prediction.get("error"):
                summary = stock_summary(mapped_sym) or {}
                resp = {"symbol": mapped_sym, "name": summary.get("name") or mapped_sym, **prediction}
                return resp
        except Exception:
            pass

    # Try simple substring match on company names (case-insensitive)
    for s, n in tickers_map.items():
        try:
            if q in (n or '').upper():
                try:
                    prediction = stock_predictor.get_prediction(s)
                    if not prediction.get("error"):
                        summary = stock_summary(s) or {}
                        resp = {"symbol": s, "name": summary.get("name") or s, **prediction}
                        return resp
                except Exception:
                    continue
        except Exception:
            continue

# ---------------------------------------------------------------------------
# POST /api/trading/trade  { symbol, quantity, side: "BUY"|"SELL" }
# ---------------------------------------------------------------------------
class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    side: str  # "BUY" or "SELL"


@router.post("/trade")
async def trade(
    req: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    symbol   = normalize_symbol(req.symbol)
    quantity = req.quantity
    side     = req.side.upper()

    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be > 0")
    if side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")

    price = latest_price(symbol)
    if price is None:
        raise HTTPException(status_code=400, detail=f"Cannot fetch price for {symbol}")

    wallet = _ensure_wallet(current_user.id, db)

    if side == "BUY":
        cost = price * quantity
        if wallet.balance < cost:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient funds. Need ₹{cost:.2f}, have ₹{wallet.balance:.2f}",
            )
        wallet.balance -= cost

        # Update or create portfolio entry
        pf = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.stock_symbol == symbol,
        ).first()
        if pf:
            total_qty  = pf.quantity + quantity
            total_cost = pf.buy_price * pf.quantity + price * quantity
            pf.buy_price = total_cost / total_qty
            pf.quantity  = total_qty
        else:
            db.add(Portfolio(user_id=current_user.id, stock_symbol=symbol, quantity=quantity, buy_price=price))

        msg = f"Bought {quantity} × {symbol} @ ₹{price:.2f}"

    else:  # SELL
        pf = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.stock_symbol == symbol,
        ).first()
        if not pf or pf.quantity < quantity:
            owned = pf.quantity if pf else 0
            raise HTTPException(status_code=400, detail=f"You only own {owned} shares of {symbol}")

        proceeds = price * quantity
        wallet.balance += proceeds

        if pf.quantity == quantity:
            db.delete(pf)
        else:
            pf.quantity -= quantity

        msg = f"Sold {quantity} × {symbol} @ ₹{price:.2f}"

    # Record transaction
    db.add(Transaction(
        user_id=current_user.id,
        stock_symbol=symbol,
        action=side,
        quantity=quantity,
        price=price,
    ))
    db.commit()

    return {
        "message": msg,
        "new_balance": round(wallet.balance, 2),
        "price": round(price, 2),
        "quantity": quantity,
        "symbol": symbol,
        "side": side,
    }
