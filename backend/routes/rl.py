from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rl.agent_service import (
    backtest_rl_agent,
    get_agent_status,
    get_rl_leaderboard,
    get_rl_recommendation,
    train_rl_batch,
    train_rl_agent,
)


router = APIRouter()


class TrainRequest(BaseModel):
    episodes: int = Field(default=60, ge=5, le=500)
    force: bool = False
    persist: bool = True
    agent_type: str = Field(default="q")


class BatchTrainRequest(BaseModel):
    symbols: list[str] | None = None
    episodes: int = Field(default=60, ge=5, le=500)
    force: bool = False
    agent_type: str = Field(default="q")


@router.get("/recommend/{symbol}")
def recommend(symbol: str):
    result = get_rl_recommendation(symbol)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/train/{symbol}")
def train(symbol: str, request: TrainRequest):
    result = train_rl_agent(
        symbol,
        episodes=request.episodes,
        force=request.force,
        persist=request.persist,
        agent_type=request.agent_type,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/backtest/{symbol}")
def backtest(symbol: str):
    result = backtest_rl_agent(symbol)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/status/{symbol}")
def status(symbol: str):
    return get_agent_status(symbol)


@router.post("/train-batch")
def train_batch(request: BatchTrainRequest):
    return train_rl_batch(
        symbols=request.symbols,
        episodes=request.episodes,
        force=request.force,
        agent_type=request.agent_type,
    )


@router.get("/leaderboard")
def leaderboard():
    return get_rl_leaderboard()
