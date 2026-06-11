from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from models import User, Portfolio
from services.auth_service import get_user_by_email
from database import get_db
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from config import settings
from services.market_data import latest_price

router = APIRouter()

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
async def get_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get user's portfolio with current values
    """
    portfolio_items = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    
    portfolio_data = []
    total_investment = 0.0
    total_current_value = 0.0
    
    for item in portfolio_items:
        current_price = latest_price(item.stock_symbol) or item.buy_price
        
        quantity = item.quantity
        buy_price = item.buy_price
        current_value = current_price * quantity
        investment = buy_price * quantity
        profit_loss = current_value - investment
        profit_loss_percent = (profit_loss / investment * 100) if investment > 0 else 0
        
        portfolio_data.append({
            "id": item.id,
            "stock_symbol": item.stock_symbol,
            "quantity": quantity,
            "buy_price": round(buy_price, 2),
            "current_price": round(current_price, 2),
            "investment": round(investment, 2),
            "current_value": round(current_value, 2),
            "profit_loss": round(profit_loss, 2),
            "profit_loss_percent": round(profit_loss_percent, 2)
        })
        
        total_investment += investment
        total_current_value += current_value
    
    total_profit_loss = total_current_value - total_investment
    total_profit_loss_percent = (total_profit_loss / total_investment * 100) if total_investment > 0 else 0
    
    return {
        "portfolio": portfolio_data,
        "summary": {
            "total_investment": round(total_investment, 2),
            "total_current_value": round(total_current_value, 2),
            "total_profit_loss": round(total_profit_loss, 2),
            "total_profit_loss_percent": round(total_profit_loss_percent, 2)
        }
    }

@router.get("/value")
async def get_portfolio_value(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get total portfolio value
    """
    portfolio = await get_portfolio(current_user, db)
    return {"total_value": portfolio["summary"]["total_current_value"]}
