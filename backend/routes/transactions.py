from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from models import User, Transaction
from services.auth_service import get_user_by_email
from database import get_db
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from config import settings

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

@router.get("/", response_model=List[Dict[str, Any]])
async def get_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get user's transaction history
    """
    transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.created_at.desc()).all()
    
    transaction_data = []
    for tx in transactions:
        transaction_data.append({
            "id": tx.id,
            "stock_symbol": tx.stock_symbol,
            "action": tx.action,
            "quantity": tx.quantity,
            "price": round(tx.price, 2),
            "total": round(tx.price * tx.quantity, 2),
            "created_at": tx.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return transaction_data