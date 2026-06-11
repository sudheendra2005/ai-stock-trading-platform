from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from models import User, Wallet, Portfolio, Transaction
from services.auth_service import get_user_by_email
from database import get_db
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from config import settings
from pydantic import BaseModel
from services.market_data import latest_price, normalize_symbol

router = APIRouter()


class TradeRequest(BaseModel):
    stock_symbol: str
    quantity: int


def get_current_user(token: str = Depends(HTTPBearer()), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


@router.get("/", response_model=Dict[str, Any])
async def get_wallet(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's wallet balance."""
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=100000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return {"balance": wallet.balance, "user_id": current_user.id}


@router.post("/buy", response_model=Dict[str, Any])
async def buy_stock(
    trade: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Buy stocks (paper trading)."""
    stock_symbol = normalize_symbol(trade.stock_symbol)
    quantity = trade.quantity

    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than 0")

    current_price = latest_price(stock_symbol)
    if current_price is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to fetch price for {stock_symbol}")

    total_cost = current_price * quantity

    # Get or create wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=100000.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

    if wallet.balance < total_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Need ₹{total_cost:.2f}, have ₹{wallet.balance:.2f}"
        )

    # Deduct from wallet
    wallet.balance -= total_cost

    # Update portfolio (average cost basis)
    portfolio_item = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.stock_symbol == stock_symbol
    ).first()

    if portfolio_item:
        total_quantity = portfolio_item.quantity + quantity
        total_cost_basis = (portfolio_item.buy_price * portfolio_item.quantity) + (current_price * quantity)
        portfolio_item.buy_price = total_cost_basis / total_quantity
        portfolio_item.quantity = total_quantity
    else:
        portfolio_item = Portfolio(
            user_id=current_user.id,
            stock_symbol=stock_symbol,
            quantity=quantity,
            buy_price=current_price
        )
        db.add(portfolio_item)

    # Record transaction
    transaction = Transaction(
        user_id=current_user.id,
        stock_symbol=stock_symbol,
        action="BUY",
        quantity=quantity,
        price=current_price
    )
    db.add(transaction)
    db.commit()

    return {
        "message": f"Successfully bought {quantity} shares of {stock_symbol} at ₹{current_price:.2f}",
        "transaction": {
            "stock_symbol": stock_symbol,
            "action": "BUY",
            "quantity": quantity,
            "price": round(current_price, 2),
            "total": round(total_cost, 2)
        },
        "new_balance": round(wallet.balance, 2)
    }


@router.post("/sell", response_model=Dict[str, Any])
async def sell_stock(
    trade: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sell stocks (paper trading)."""
    stock_symbol = normalize_symbol(trade.stock_symbol)
    quantity = trade.quantity

    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be greater than 0")

    # Check portfolio first
    portfolio_item = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.stock_symbol == stock_symbol
    ).first()

    if not portfolio_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You don't own any shares of {stock_symbol}")

    if portfolio_item.quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient shares. You own {portfolio_item.quantity} shares of {stock_symbol}"
        )

    current_price = latest_price(stock_symbol)
    if current_price is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to fetch price for {stock_symbol}")

    proceeds = current_price * quantity

    # Add to wallet
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=0.0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    wallet.balance += proceeds

    # Update portfolio
    if portfolio_item.quantity == quantity:
        db.delete(portfolio_item)
    else:
        portfolio_item.quantity -= quantity

    # Record transaction
    transaction = Transaction(
        user_id=current_user.id,
        stock_symbol=stock_symbol,
        action="SELL",
        quantity=quantity,
        price=current_price
    )
    db.add(transaction)
    db.commit()

    pl = (current_price - portfolio_item.buy_price if portfolio_item.quantity > quantity else current_price) * quantity

    return {
        "message": f"Successfully sold {quantity} shares of {stock_symbol} at ₹{current_price:.2f}",
        "transaction": {
            "stock_symbol": stock_symbol,
            "action": "SELL",
            "quantity": quantity,
            "price": round(current_price, 2),
            "total": round(proceeds, 2)
        },
        "new_balance": round(wallet.balance, 2)
    }
