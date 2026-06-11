from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn
from config import settings
from database import engine, Base
from routes import auth, stocks, wallet, portfolio, transactions, trading, rl, cron
import models

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Stock Trading Platform",
    description="A cloud-based AI-powered stock analysis and paper trading platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["Stocks"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(rl.router, prefix="/api/rl", tags=["Reinforcement Learning"])
app.include_router(cron.router, prefix="/api/cron", tags=["Scheduled AI Training"])

@app.get("/")
async def root():
    return {"message": "Welcome to AI Stock Trading Platform API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
