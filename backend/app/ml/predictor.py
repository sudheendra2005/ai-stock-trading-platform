import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timedelta

class StockPredictor:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = MinMaxScaler()

    def fetch_data(self, period="2y"):
        try:
            df = yf.download(self.symbol, period=period, interval="1d")
            if df.empty:
                return None
            # Handle multi-index columns if they exist (yfinance v1.3.0+ often delivers these)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception as e:
            print(f"Error fetching data for {self.symbol}: {e}")
            return None

    def prepare_features(self, df):
        # Use closing price for prediction
        df = df[['Close']].copy()
        
        # Feature engineering: Moving Averages
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()
        
        # Return percentage change
        df['Return'] = df['Close'].pct_change()
        
        # Target: Next day closing price
        df['Target'] = df['Close'].shift(-1)
        
        df = df.dropna()
        
        X = df[['Close', 'MA5', 'MA20', 'MA50', 'Return']]
        y = df['Target']
        
        return X, y

    def train_and_predict(self):
        df = self.fetch_data()
        if df is None or len(df) < 50:
            return None, None

        X, y = self.prepare_features(df)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model on all but the last record
        self.model.fit(X_scaled[:-1], y[:-1])
        
        # Predict for the next day using the most recent data point
        last_features = X_scaled[-1].reshape(1, -1)
        prediction = self.model.predict(last_features)[0]
        
        # Return current price and predicted price
        current_price = df['Close'].iloc[-1]
        if isinstance(current_price, pd.Series): # Handle potential pandas series from multi-index
            current_price = current_price.iloc[0]
            
        return float(current_price), float(prediction)

def get_stock_prediction(symbol: str):
    predictor = StockPredictor(symbol)
    return predictor.train_and_predict()
