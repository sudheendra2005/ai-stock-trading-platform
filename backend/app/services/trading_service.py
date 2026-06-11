import yfinance as yf
from sqlalchemy.orm import Session
from app.models.models import User, Portfolio, Transaction
from app.schemas.schemas import PortfolioOut, PortfolioItem
from datetime import datetime

def get_current_stock_price(symbol: str):
    ticker = yf.Ticker(symbol)
    # Use fast_info or history to get the latest price
    data = ticker.history(period="1d")
    if data.empty:
        return None
    return float(data['Close'].iloc[-1])

def execute_trade(db: Session, user_id: int, symbol: str, quantity: int, transaction_type: str):
    price = get_current_stock_price(symbol)
    if price is None:
        raise ValueError(f"Could not fetch price for symbol {symbol}")

    user = db.query(User).filter(User.id == user_id).first()
    total_cost = price * quantity

    if transaction_type == "BUY":
        if user.balance < total_cost:
            raise ValueError("Insufficient balance for this trade")
        
        user.balance -= total_cost
        
        portfolio_item = db.query(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.stock_symbol == symbol).first()
        if portfolio_item:
            # Update average price
            total_qty = portfolio_item.quantity + quantity
            new_avg_price = ((portfolio_item.average_price * portfolio_item.quantity) + total_cost) / total_qty
            portfolio_item.quantity = total_qty
            portfolio_item.average_price = new_avg_price
        else:
            portfolio_item = Portfolio(user_id=user_id, stock_symbol=symbol, quantity=quantity, average_price=price)
            db.add(portfolio_item)

    elif transaction_type == "SELL":
        portfolio_item = db.query(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.stock_symbol == symbol).first()
        if not portfolio_item or portfolio_item.quantity < quantity:
            raise ValueError("Insufficient stock quantity to sell")
        
        user.balance += total_cost
        portfolio_item.quantity -= quantity
        if portfolio_item.quantity == 0:
            db.delete(portfolio_item)

    transaction = Transaction(user_id=user_id, symbol=symbol, transaction_type=transaction_type, quantity=quantity, price=price)
    db.add(transaction)
    db.commit()
    db.refresh(user)
    return transaction

def get_user_portfolio(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    items = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    
    portfolio_data = []
    total_investment = 0.0
    total_current_value = 0.0
    
    for item in items:
        current_price = get_current_stock_price(item.stock_symbol) or item.average_price
        quantity = item.quantity
        buy_price = item.average_price
        
        investment = buy_price * quantity
        current_value = current_price * quantity
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
        "items": portfolio_data,
        "summary": {
            "total_investment": round(total_investment, 2),
            "total_current_value": round(total_current_value, 2),
            "total_profit_loss": round(total_profit_loss, 2),
            "total_profit_loss_percent": round(total_profit_loss_percent, 2)
        }
    }
