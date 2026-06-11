# =============================================================================
# backend/app/ml/lstm_model.py
# PyTorch LSTM model for price prediction
# Model weights are server-side only - never exposed to frontend
# =============================================================================
import logging
import os
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

MODEL_DIR = Path("backend/prediction/saved_models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


class LSTMPricePredictor(nn.Module):
    """
    LSTM neural network for time-series price prediction.
    Architecture: 2-layer LSTM + Dropout + Fully connected output.
    """

    def __init__(
        self,
        input_size: int = 5,      # OHLCV features
        hidden_size: int = 128,
        num_layers: int = 2,
        output_size: int = 1,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.dropout(out[:, -1, :])
        return self.fc(out)


class PricePredictionService:
    """
    Service wrapper for LSTM price prediction.
    Loads pre-trained model weights from secure server-side storage.
    Model weights are NEVER sent to the frontend.
    """

    def __init__(self) -> None:
        self.models: dict = {}  # symbol -> (model, scaler)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.sequence_length = 60  # Look back 60 periods

    def _prepare_data(self, prices: np.ndarray) -> Tuple[np.ndarray, MinMaxScaler]:
        """Normalize price data to [0, 1] range for LSTM training."""
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = scaler.fit_transform(prices.reshape(-1, 1))
        return scaled, scaler

    def _create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create overlapping input/target sequences for LSTM."""
        X, y = [], []
        for i in range(self.sequence_length, len(data)):
            X.append(data[i - self.sequence_length:i])
            y.append(data[i])
        return np.array(X), np.array(y)

    def train(
        self,
        symbol: str,
        prices: np.ndarray,
        epochs: int = 50,
        lr: float = 0.001,
    ) -> float:
        """
        Train LSTM model for a given symbol.
        Returns final training loss.
        """
        if len(prices) < self.sequence_length + 10:
            raise ValueError(f"Insufficient data: need at least {self.sequence_length + 10} data points")

        scaled_prices, scaler = self._prepare_data(prices)
        X, y = self._create_sequences(scaled_prices)

        X_tensor = torch.FloatTensor(X).to(self.device)
        y_tensor = torch.FloatTensor(y).to(self.device)

        model = LSTMPricePredictor(input_size=1).to(self.device)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        model.train()
        final_loss = float("inf")
        for epoch in range(epochs):
            optimizer.zero_grad()
            output = model(X_tensor)
            loss = criterion(output, y_tensor)
            loss.backward()
            # Gradient clipping prevents exploding gradients
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            final_loss = loss.item()

            if (epoch + 1) % 10 == 0:
                logger.debug(f"Epoch [{epoch+1}/{epochs}], Loss: {final_loss:.6f}")

        # Save model and scaler to server-side storage
        self._save_model(symbol, model, scaler)
        self.models[symbol] = (model, scaler)
        return final_loss

    def predict(self, symbol: str, recent_prices: np.ndarray) -> Tuple[float, float]:
        """
        Predict next price for a symbol.
        Returns (predicted_price, confidence_score).
        Model NEVER returned to client - only the prediction value.
        """
        if symbol not in self.models:
            self._load_model(symbol)

        if symbol not in self.models:
            raise ValueError(f"No trained model found for {symbol}")

        model, scaler = self.models[symbol]
        model.eval()

        if len(recent_prices) < self.sequence_length:
            raise ValueError(f"Need at least {self.sequence_length} recent prices")

        # Use last `sequence_length` prices
        input_data = recent_prices[-self.sequence_length:]
        scaled = scaler.transform(input_data.reshape(-1, 1))
        X = torch.FloatTensor(scaled).unsqueeze(0).to(self.device)

        with torch.no_grad():
            prediction_scaled = model(X).cpu().numpy()

        predicted_price = float(scaler.inverse_transform(prediction_scaled)[0][0])

        # Confidence: based on consistency of recent predictions (simplified)
        confidence = min(0.95, max(0.5, 1.0 - (np.std(recent_prices[-10:]) / np.mean(recent_prices[-10:]))))

        return predicted_price, confidence

    def incremental_train(self, symbol: str, prices: np.ndarray, lr: float = 0.0001) -> float:
        """
        Perform a single epoch of training on the latest data sequence.
        Used for continuous real-time learning.
        """
        if symbol not in self.models:
            # Load or do initial full train
            self._load_model(symbol)
            if symbol not in self.models:
                return self.train(symbol, prices, epochs=5)

        model, scaler = self.models[symbol]
        if len(prices) < self.sequence_length + 1:
            return 0.0
            
        # Use only the very last sequence for incremental step
        recent_data = prices[-(self.sequence_length + 1):]
        scaled_prices = scaler.transform(recent_data.reshape(-1, 1))
        
        X = scaled_prices[:-1].reshape(1, self.sequence_length, 1)
        y = scaled_prices[-1].reshape(1, 1)

        X_tensor = torch.FloatTensor(X).to(self.device)
        y_tensor = torch.FloatTensor(y).to(self.device)

        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        optimizer.zero_grad()
        output = model(X_tensor)
        loss = criterion(output, y_tensor)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        loss_val = loss.item()
        
        # We don't save to disk every second to save IO, just keep in memory
        self.models[symbol] = (model, scaler)
        return loss_val

    def _save_model(self, symbol: str, model: LSTMPricePredictor, scaler: MinMaxScaler) -> None:
        """Save model weights to server-side secure storage."""
        import pickle
        model_path = MODEL_DIR / f"{symbol}_lstm.pt"
        scaler_path = MODEL_DIR / f"{symbol}_scaler.pkl"
        torch.save(model.state_dict(), model_path)
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)
        logger.info(f"Model saved for {symbol}")

    def _load_model(self, symbol: str) -> None:
        """Load pre-trained model from server-side storage."""
        import pickle
        model_path = MODEL_DIR / f"{symbol}_lstm.pt"
        scaler_path = MODEL_DIR / f"{symbol}_scaler.pkl"

        if not model_path.exists() or not scaler_path.exists():
            return

        model = LSTMPricePredictor(input_size=1).to(self.device)
        model.load_state_dict(torch.load(model_path, map_location=self.device))
        model.eval()

        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)

        self.models[symbol] = (model, scaler)
        logger.info(f"Model loaded for {symbol}")


prediction_service = PricePredictionService()
