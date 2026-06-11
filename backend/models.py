from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from database import Base
from datetime import datetime, timedelta

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Wallet(Base):
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    balance = Column(Float, default=100000.0)

class Portfolio(Base):
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_symbol = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    buy_price = Column(Float, nullable=False)

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_symbol = Column(String(20), nullable=False)
    action = Column(String(10), nullable=False)  # BUY or SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_symbol = Column(String(20), nullable=False)
    current_price = Column(Float, nullable=False)
    short_term_prediction = Column(String(50))
    long_term_prediction = Column(String(50))
    confidence_score = Column(String(10))
    risk_level = Column(String(20))
    recommendation = Column(String(10))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RLAgentPolicy(Base):
    __tablename__ = "rl_agent_policies"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(30), unique=True, index=True, nullable=False)
    agent_type = Column(String(20), default="q", nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class MarketDataSnapshot(Base):
    __tablename__ = "market_data_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(30), index=True, nullable=False)
    price = Column(Float, nullable=False)
    change_percent = Column(Float, default=0.0)
    volume = Column(Integer, default=0)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
