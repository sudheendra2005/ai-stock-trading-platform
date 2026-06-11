from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api_router import api_router

app = FastAPI(
    title="AI Stock Trading Platform API",
    description="Backend API for AI-powered stock prediction and paper trading",
    version="1.0.0"
)

# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api", tags=["main"])

@app.get("/")
async def root():
    return {"message": "AI Stock Trading Platform API is running"}
