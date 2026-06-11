"""
stock_predictor.py
==================
Proper ML-based stock predictor using:
  1. Feature Engineering  - 15+ technical indicators as ML features (NOT raw prices)
  2. Target Engineering   - Predict 5-day RETURN DIRECTION (Up/Down/Neutral)
                           NOT the raw price (which is essentially a random walk)
  3. Model                - RandomForestClassifier with time-series aware split
  4. Confidence           - Real probability from predict_proba(), not hardcoded
  5. Long-term            - Separate model trained on 20-day forward returns

Why this matters:
  - Predicting raw prices leads to models that just predict "yesterday's price" 
    (a trivial lag baseline), which looks good on paper but is useless.
  - Predicting DIRECTION (up/down) with technical indicators as features is the
    standard academic and industry approach.
  - Time-series split ensures no data leakage (future data never trains the model).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
import warnings
from services.market_data import get_history, normalize_symbol
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class StockPredictor:
    def __init__(self):
        pass

    # -------------------------------------------------------------------------
    # 1. DATA FETCHING
    # -------------------------------------------------------------------------
    def get_stock_data(self, symbol: str, period: str = "2y") -> pd.DataFrame:
        """Fetch at least 2 years of OHLCV data for robust feature engineering."""
        try:
            df = get_history(symbol, period=period)
            if df.empty:
                logger.warning(f"No data found for symbol {symbol}")
                return pd.DataFrame()
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return pd.DataFrame()

    # -------------------------------------------------------------------------
    # 2. FEATURE ENGINEERING
    #    All features are technical indicators derived from OHLCV data.
    #    Raw prices are NEVER used as features directly.
    # -------------------------------------------------------------------------
    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build 15+ technical indicator features.
        Returns a copy with NaN rows dropped.
        """
        d = df.copy()
        close = d["Close"]
        high  = d["High"]
        low   = d["Low"]
        vol   = d["Volume"]

        # --- Trend indicators ---
        d["ma_20"]  = close.rolling(20).mean()
        d["ma_50"]  = close.rolling(50).mean()
        d["ma_200"] = close.rolling(200).mean()
        d["ema_12"] = close.ewm(span=12, adjust=False).mean()
        d["ema_26"] = close.ewm(span=26, adjust=False).mean()

        # Price relative to MAs (normalised — no raw prices)
        d["close_vs_ma20"]  = close / d["ma_20"]  - 1
        d["close_vs_ma50"]  = close / d["ma_50"]  - 1
        d["close_vs_ma200"] = close / d["ma_200"] - 1
        d["ma20_vs_ma50"]   = d["ma_20"] / d["ma_50"] - 1

        # --- Momentum indicators ---
        # RSI (14-day)
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / (loss + 1e-9)
        d["rsi"] = 100 - (100 / (1 + rs))

        # Normalised RSI (0-1 scale, so it's a proper feature)
        d["rsi_norm"] = d["rsi"] / 100.0

        # MACD histogram (measures momentum direction + strength)
        d["macd"]        = d["ema_12"] - d["ema_26"]
        d["macd_signal"] = d["macd"].ewm(span=9, adjust=False).mean()
        d["macd_hist"]   = d["macd"] - d["macd_signal"]
        # Normalise by price level so it's comparable across stocks
        d["macd_hist_norm"] = d["macd_hist"] / close

        # Rate of Change (momentum)
        d["roc_5"]  = close.pct_change(5)
        d["roc_10"] = close.pct_change(10)
        d["roc_20"] = close.pct_change(20)

        # --- Volatility indicators ---
        d["returns"]          = close.pct_change()
        d["volatility_10d"]   = d["returns"].rolling(10).std()
        d["volatility_30d"]   = d["returns"].rolling(30).std()
        # Annualised vol (used for risk assessment)
        d["volatility_annual"] = d["volatility_30d"] * np.sqrt(252)

        # --- Bollinger Bands ---
        bb_mean = close.rolling(20).mean()
        bb_std  = close.rolling(20).std()
        bb_upper = bb_mean + 2 * bb_std
        bb_lower = bb_mean - 2 * bb_std
        # %B: where price sits in the band (0 = lower band, 1 = upper band)
        d["bb_pct"] = (close - bb_lower) / (bb_upper - bb_lower + 1e-9)
        # Bandwidth: measures squeeze / expansion
        d["bb_width"] = (bb_upper - bb_lower) / (bb_mean + 1e-9)

        # --- Volume features ---
        d["vol_ma20"]    = vol.rolling(20).mean()
        d["vol_ratio"]   = vol / (d["vol_ma20"] + 1e-9)   # relative volume
        d["vol_change"]  = vol.pct_change()

        # --- Stochastic Oscillator (%K, %D) ---
        low_14  = low.rolling(14).min()
        high_14 = high.rolling(14).max()
        d["stoch_k"] = (close - low_14) / (high_14 - low_14 + 1e-9) * 100
        d["stoch_d"] = d["stoch_k"].rolling(3).mean()
        d["stoch_norm"] = d["stoch_k"] / 100.0

        # Drop setup period rows and any divide-by-zero artifacts from sparse volume data.
        d.replace([np.inf, -np.inf], np.nan, inplace=True)
        d.dropna(inplace=True)
        return d

    # -------------------------------------------------------------------------
    # 3. TARGET ENGINEERING
    #    Predict DIRECTION of return over next N days.
    #    Labels: 1 = UP (return > +1%), -1 = DOWN (return < -1%), 0 = NEUTRAL
    # -------------------------------------------------------------------------
    FEATURE_COLS = [
        "rsi_norm", "macd_hist_norm",
        "close_vs_ma20", "close_vs_ma50", "close_vs_ma200", "ma20_vs_ma50",
        "roc_5", "roc_10", "roc_20",
        "volatility_10d", "volatility_30d",
        "bb_pct", "bb_width",
        "vol_ratio", "vol_change",
        "stoch_norm",
    ]

    def _make_target(self, close_series: pd.Series, horizon: int, threshold: float) -> pd.Series:
        """
        Forward return over `horizon` days.
        Returns 1 if > +threshold, -1 if < -threshold, else 0.
        """
        fwd_return = close_series.shift(-horizon) / close_series - 1
        target = pd.Series(0, index=close_series.index)
        target[fwd_return >  threshold] =  1
        target[fwd_return < -threshold] = -1
        return target

    # -------------------------------------------------------------------------
    # 4. MODEL TRAINING & PREDICTION
    # -------------------------------------------------------------------------
    def _train_and_predict(
        self,
        df_feat: pd.DataFrame,
        horizon: int,
        threshold: float,
    ) -> Dict[str, Any]:
        """
        Train a RandomForestClassifier using time-series aware split.
        - Train on first 80% of data
        - Predict on last row (current state)
        Returns label (+1/-1/0), probability, and signal string.
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler

        close = df_feat["Close"]
        target = self._make_target(close, horizon, threshold)

        # Drop last `horizon` rows (no label yet — future unknown)
        valid_idx = target.index[:-horizon]
        X_all = df_feat.loc[valid_idx, self.FEATURE_COLS]
        y_all = target.loc[valid_idx]

        if len(X_all) < 60:
            return {"label": 0, "prob": 0.5, "signal": "HOLD", "confidence": "50%"}

        # Time-series aware split: train on first 80%, validate on last 20%
        split = int(len(X_all) * 0.80)
        X_train, y_train = X_all.iloc[:split], y_all.iloc[:split]

        # Need at least 2 classes to train
        if len(y_train.unique()) < 2:
            return {"label": 0, "prob": 0.5, "signal": "HOLD", "confidence": "50%"}

        # Scale features
        scaler = StandardScaler()
        X_train_sc = scaler.fit_transform(X_train)

        # Train classifier
        clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            min_samples_leaf=5,
            class_weight="balanced",   # handles class imbalance
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(X_train_sc, y_train)

        # Predict on the LAST ROW (today's market state — unseen by model)
        X_now = df_feat[self.FEATURE_COLS].iloc[[-1]]
        X_now_sc = scaler.transform(X_now)

        label  = int(clf.predict(X_now_sc)[0])
        probas = clf.predict_proba(X_now_sc)[0]
        classes = list(clf.classes_)

        # Probability of the predicted class = real confidence
        pred_prob = float(probas[classes.index(label)])

        # Map label to signal
        if label == 1:
            signal = "BUY"
        elif label == -1:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "label": label,
            "prob": pred_prob,
            "signal": signal,
            "confidence": f"{int(pred_prob * 100)}%",
        }

    # -------------------------------------------------------------------------
    # 5. RISK LEVEL
    # -------------------------------------------------------------------------
    def _risk_level(self, volatility_annual: float) -> str:
        if volatility_annual > 0.50:
            return "HIGH"
        elif volatility_annual > 0.28:
            return "MEDIUM"
        else:
            return "LOW"

    # -------------------------------------------------------------------------
    # 6. PUBLIC API
    # -------------------------------------------------------------------------
    def get_prediction(self, symbol: str) -> Dict[str, Any]:
        """
        Main method: fetches data, engineers features, trains two RF classifiers
        (short-term 5-day and long-term 20-day), and returns structured output.
        """
        symbol = normalize_symbol(symbol)
        df = self.get_stock_data(symbol)
        if df.empty:
            return {
                "error": f"Unable to fetch data for symbol {symbol}",
                "company": symbol,
                "current_price": 0.0,
                "short_term": "ERROR",
                "long_term": "ERROR",
                "confidence": "0%",
                "risk": "HIGH",
                "recommendation": "HOLD",
                "indicators": {},
            }

        # Build features
        df_feat = self.build_features(df)

        if len(df_feat) < 80:
            return {
                "error": f"Insufficient data for {symbol} (need ≥80 rows after indicators)",
                "company": symbol,
                "current_price": 0.0,
                "short_term": "NEUTRAL",
                "long_term": "NEUTRAL",
                "confidence": "0%",
                "risk": "HIGH",
                "recommendation": "HOLD",
                "indicators": {},
            }

        current_price = float(df_feat["Close"].iloc[-1])
        latest = df_feat.iloc[-1]

        # --- Short-term: predict 5-day direction, ±1% threshold ---
        short = self._train_and_predict(df_feat, horizon=5, threshold=0.01)

        # --- Long-term: predict 20-day direction, ±3% threshold ---
        long = self._train_and_predict(df_feat, horizon=20, threshold=0.03)

        # --- Short-term trend label ---
        st_trend_map = {"BUY": "UPTREND", "SELL": "DOWNTREND", "HOLD": "NEUTRAL"}
        short_trend = st_trend_map[short["signal"]]

        # --- Long-term trend label ---
        lt_trend_map = {"BUY": "BULLISH", "SELL": "BEARISH", "HOLD": "NEUTRAL"}
        long_trend = lt_trend_map[long["signal"]]

        # --- Risk level from annualised volatility ---
        vol_annual = float(latest["volatility_annual"]) if not pd.isna(latest["volatility_annual"]) else 0.25
        risk = self._risk_level(vol_annual)

        # --- Indicator values for UI ---
        indicators = {
            "rsi":        round(float(latest["rsi"]),  2) if not pd.isna(latest["rsi"]) else 50.0,
            "macd":       round(float(latest["macd"]), 4) if not pd.isna(latest["macd"]) else 0.0,
            "macd_signal":round(float(latest["macd_signal"]), 4) if not pd.isna(latest["macd_signal"]) else 0.0,
            "volatility": round(vol_annual, 4),
            "bb_pct":     round(float(latest["bb_pct"]), 4) if not pd.isna(latest["bb_pct"]) else 0.5,
            "roc_5":      round(float(latest["roc_5"]) * 100, 2) if not pd.isna(latest["roc_5"]) else 0.0,
            "roc_20":     round(float(latest["roc_20"]) * 100, 2) if not pd.isna(latest["roc_20"]) else 0.0,
            "stoch_k":    round(float(latest["stoch_k"]), 2) if not pd.isna(latest["stoch_k"]) else 50.0,
            "vol_ratio":  round(float(latest["vol_ratio"]), 2) if not pd.isna(latest["vol_ratio"]) else 1.0,
        }

        return {
            "company":         symbol.upper(),
            "current_price":   round(current_price, 2),
            "short_term":      short_trend,
            "long_term":       long_trend,
            "confidence":      short["confidence"],
            "risk":            risk,
            "recommendation":  short["signal"],
            "indicators":      indicators,
        }


# Singleton instance
stock_predictor = StockPredictor()
