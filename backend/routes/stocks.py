from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from prediction.stock_predictor import stock_predictor
from services.market_data import normalize_symbol, stock_summary

router = APIRouter()

@router.get("/trending", response_model=List[Dict[str, Any]])
async def get_trending_stocks():
    """
    Get trending stocks (for now, using a predefined list)
    In a real app, this would fetch from a financial news API
    """
    # For demo purposes, using popular Indian and US stocks
    trending_symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
                       "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    trending_stocks = []
    for symbol in trending_symbols[:6]:  # Limit to 6 for performance
        data = stock_summary(symbol, period="5d")
        if data:
            trending_stocks.append({
                "symbol": data["symbol"],
                "name": data["name"],
                "price": data["price"],
                "change": data["change"],
                "volume": data["volume"],
            })
    
    return trending_stocks

@router.get("/{symbol}")
async def get_stock_details(symbol: str):
    """
    Get detailed information for a specific stock
    """
    normalized = normalize_symbol(symbol)
    data = stock_summary(normalized, period="1mo")
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for symbol {normalized}"
        )
    return data

@router.get("/predict/{symbol}")
def get_stock_prediction(symbol: str):
    """
    Get AI prediction for a specific stock
    """
    try:
        prediction = stock_predictor.get_prediction(normalize_symbol(symbol))
        if "error" in prediction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=prediction["error"]
            )
        return prediction
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating prediction: {str(e)}"
        )
