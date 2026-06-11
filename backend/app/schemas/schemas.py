from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    balance: float
    is_verified: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class PortfolioItem(BaseModel):
    stock_symbol: str
    quantity: int
    average_price: float

    class Config:
        from_attributes = True

class PortfolioOut(BaseModel):
    items: List[PortfolioItem]
    total_value: float
    cash_balance: float
