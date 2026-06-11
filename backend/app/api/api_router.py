from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.trading import router as trading_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(trading_router, prefix="/trading", tags=["Trading"])
