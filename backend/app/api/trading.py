from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.auth import get_current_user
from app.models.models import User, Transaction
from app.schemas.schemas import PortfolioOut
from app.services.trading_service import execute_trade, get_user_portfolio
from app.ml.predictor import get_stock_prediction
import yfinance as yf
from rapidfuzz import process, fuzz
from pathlib import Path
import json


router = APIRouter()

INDIAN_STOCKS_MAP = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "TATA CONSULTANCY SERVICES": "TCS.NS",
    "INFOSYS": "INFY.NS",
    "INFY": "INFY.NS",
    "HDFC": "HDFCBANK.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "ICICI": "ICICIBANK.NS",
    "ICICI BANK": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "STATE BANK OF INDIA": "SBIN.NS",
    "SBIN": "SBIN.NS",
    "BHARTI AIRTEL": "BHARTIARTL.NS",
    "AIRTEL": "BHARTIARTL.NS",
    "ITC": "ITC.NS",
    "L&T": "LT.NS",
    "LARSEN & TOUBRO": "LT.NS",
    "HINDUSTAN UNILEVER": "HINDUNILVR.NS",
    "HUL": "HINDUNILVR.NS",
    "BAJAJ FINANCE": "BAJFINANCE.NS",
    "AXIS": "AXISBANK.NS",
    "AXIS BANK": "AXISBANK.NS",
    "KOTAK": "KOTAKBANK.NS",
    "KOTAK MAHINDRA BANK": "KOTAKBANK.NS",
    "WIPRO": "WIPRO.NS",
    "HCL": "HCLTECH.NS",
    "HCL TECH": "HCLTECH.NS",
    "MARUTI": "MARUTI.NS",
    "MARUTI SUZUKI": "MARUTI.NS",
    "SUN PHARMA": "SUNPHARMA.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "ASIAN PAINTS": "ASIANPAINT.NS",
    "TITAN": "TITAN.NS",
    "ULTRATECH": "ULTRACEMCO.NS",
    "ADANI": "ADANIENT.NS",
    "ADANI ENTERPRISES": "ADANIENT.NS",
    "POWER GRID": "POWERGRID.NS",
    "NTPC": "NTPC.NS",
    "JIO FINANCIAL": "JIOFIN.NS",
    "ONGC": "ONGC.NS",
    "COAL INDIA": "COALINDIA.NS",
    "TATA STEEL": "TATASTEEL.NS",
    "JSW STEEL": "JSWSTEEL.NS",
    "M&M": "M&M.NS",
    "MAHINDRA & MAHINDRA": "M&M.NS",
    "BAJAJ AUTO": "BAJAJ-AUTO.NS",
    "LTIMINDTREE": "LTIM.NS",
    "NESTLE": "NESTLEIND.NS",
    "NESTLE INDIA": "NESTLEIND.NS",
    "GRASIM": "GRASIM.NS",
    "TECH MAHINDRA": "TECHM.NS",
    "CIPLA": "CIPLA.NS",
    "APOLLO HOSPITALS": "APOLLOHOSP.NS",
    "DR REDDY": "DRREDDY.NS",
    "HINDALCO": "HINDALCO.NS",
    "INDUSIND": "INDUSINDBK.NS",
    "EICHER": "EICHERMOT.NS",
    "BPCL": "BPCL.NS",
    "SBI LIFE": "SBILIFE.NS",
    "BAJAJ FINSERV": "BAJAJFINSV.NS",
    "HDFC LIFE": "HDFCLIFE.NS",
    "BRITANNIA": "BRITANNIA.NS",
    "ADANI PORTS": "ADANIPORTS.NS",
    "HERO MOTOCORP": "HEROMOTOCO.NS",
    "JINDAL STEEL": "JINDALSTEL.NS",
    "TATA CONSUMER": "TATACONSUM.NS",
    "DIVIS LAB": "DIVISLAB.NS",
    "SHREE CEMENT": "SHREECEM.NS",
    "DLF": "DLF.NS",
    "HAL": "HAL.NS",
    "BEL": "BEL.NS",
    "SIEMENS": "SIEMENS.NS",
    "ABB": "ABB.NS",
    "TRENT": "TRENT.NS",
    "ZOMATO": "ZOMATO.NS",
    "PAYTM": "PAYTM.NS",
    "LIC": "LICI.NS",
    "IRCTC": "IRCTC.NS"
}

SYMBOL_NAMES = {
    "RELIANCE.NS": "Reliance Industries Ltd",
    "TCS.NS": "Tata Consultancy Services",
    "INFY.NS": "Infosys Ltd",
    "SBIN.NS": "State Bank of India",
    "HDFCBANK.NS": "HDFC Bank Ltd",
    "ZOMATO.NS": "Zomato Ltd",
    "AAPL": "Apple Inc",
    "MSFT": "Microsoft Corp",
    "TSLA": "Tesla Inc"
}


# Try to load an external tickers file (optional). This allows bulk imports
# (e.g. from NSE/BSE) into `backend/app/data/tickers.json` with format:
# [ {"symbol":"TCS.NS","name":"Tata Consultancy Services"}, ... ]
def _load_external_tickers():
    try:
        app_root = Path(__file__).resolve().parents[1]
        data_file = app_root / 'data' / 'tickers.json'
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                if isinstance(data, dict):
                    # symbol->name mapping
                    for sym, name in data.items():
                        SYMBOL_NAMES[sym] = name
                        INDIAN_STOCKS_MAP[name.upper()] = sym
                        INDIAN_STOCKS_MAP[sym.upper()] = sym
                elif isinstance(data, list):
                    for item in data:
                        sym = item.get('symbol') or item.get('ticker') or item.get('code')
                        name = item.get('name') or item.get('company') or item.get('longName')
                        if sym and name:
                            SYMBOL_NAMES[sym] = name
                            INDIAN_STOCKS_MAP[name.upper()] = sym
                            INDIAN_STOCKS_MAP[sym.upper()] = sym
    except Exception:
        # Fail silently — the bundled maps remain available
        pass


# Load external tickers if present
_load_external_tickers()

@router.get("/dashboard")
async def get_dashboard_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    portfolio = get_user_portfolio(db, current_user.id)
    
    # Get some trending stocks for dashboard
    trending_symbols = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "SBIN.NS", "HDFCBANK.NS",
        "ZOMATO.NS", "AAPL", "MSFT", "TSLA"
    ]
    stock_data = []
    for symbol in trending_symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                change = ((price - float(hist['Open'].iloc[-1])) / float(hist['Open'].iloc[-1])) * 100
                stock_data.append({
                    "symbol": symbol,
                    "name": SYMBOL_NAMES.get(symbol, symbol),
                    "price": round(price, 2),
                    "change": round(change, 2)
                })
        except Exception:
            # Fallback in case of temporary network glitches
            pass
            
    return {
        "user": current_user,
        "portfolio": portfolio,
        "trending_stocks": stock_data
    }

@router.get("/predict/{symbol}")
async def predict_stock(symbol: str, current_user: User = Depends(get_current_user)):
    cleaned_symbol = symbol.upper().strip()
    
    # 1. Check direct map
    mapped_symbol = INDIAN_STOCKS_MAP.get(cleaned_symbol)
    
    # 2. Check direct match in values
    if not mapped_symbol:
        for name, sym in INDIAN_STOCKS_MAP.items():
            if cleaned_symbol == sym.replace(".NS", "") or cleaned_symbol == sym:
                mapped_symbol = sym
                break

    # 3. Fuzzy search using RapidFuzz (broadened to include company names and external list)
    if not mapped_symbol:
        try:
            keys_list = list(INDIAN_STOCKS_MAP.keys())
            values_list = list(INDIAN_STOCKS_MAP.values())
            name_list = [n.upper() for n in SYMBOL_NAMES.values()]

            # Build combined search space (company names and symbols)
            search_space = keys_list + values_list + name_list

            best = process.extractOne(cleaned_symbol, search_space, scorer=fuzz.WRatio)
            if best:
                match_value, score, _ = best
                # Use a slightly lower threshold to be more helpful for keyword queries
                if score >= 50.0:
                    if match_value in INDIAN_STOCKS_MAP:
                        mapped_symbol = INDIAN_STOCKS_MAP[match_value]
                    elif match_value in values_list:
                        mapped_symbol = match_value
                    else:
                        # try matching back to SYMBOL_NAMES values
                        for sym, nm in SYMBOL_NAMES.items():
                            if nm.upper() == match_value:
                                mapped_symbol = sym
                                break
        except Exception:
            # Safe fallback if fuzzy library has issues
            pass

    final_symbol = mapped_symbol if mapped_symbol else cleaned_symbol
    
    # Try fetching prediction
    current, predicted = get_stock_prediction(final_symbol)
    
    # 4. Fallback: If not found, try appending .NS (for NSE)
    if current is None and not final_symbol.endswith(".NS") and not final_symbol.endswith(".BO") and len(final_symbol) <= 8:
        try_symbol = f"{final_symbol}.NS"
        current, predicted = get_stock_prediction(try_symbol)
        if current is not None:
            final_symbol = try_symbol
            
    if current is None:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for symbol '{symbol}'")
    
    company_name = SYMBOL_NAMES.get(final_symbol, final_symbol)
    if company_name == final_symbol:
        if final_symbol.endswith(".NS"):
            company_name = final_symbol.replace(".NS", "") + " (NSE)"
        elif final_symbol.endswith(".BO"):
            company_name = final_symbol.replace(".BO", "") + " (BSE)"
        
    return {
        "symbol": final_symbol,
        "name": company_name,
        "current_price": round(current, 2),
        "predicted_price": round(predicted, 2),
        "direction": "UP" if predicted > current else "DOWN",
        "confidence": "Medium"
    }


from pydantic import BaseModel

class TradeRequest(BaseModel):
    symbol: str
    quantity: int
    side: str

@router.post("/trade")
async def trade_stock(request: TradeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    symbol = request.symbol
    quantity = request.quantity
    side = request.side
    if side.upper() not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")
        
    try:
        transaction = execute_trade(db, current_user.id, symbol.upper(), quantity, side.upper())
        return {"message": f"Successfully {side} {quantity} shares of {symbol}", "transaction": transaction}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/portfolio")
async def get_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_user_portfolio(db, current_user.id)

@router.get("/wallet")
async def get_wallet(current_user: User = Depends(get_current_user)):
    return {"balance": current_user.balance}

@router.get("/transactions")
async def get_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.timestamp.desc()).all()
    return [
        {
            "id": tx.id,
            "stock_symbol": tx.symbol,
            "action": tx.transaction_type,
            "quantity": tx.quantity,
            "price": tx.price,
            "created_at": tx.timestamp.isoformat()
        }
        for tx in txs
    ]

