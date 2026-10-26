"""
stock_predictor.py - simple ML price forecasting (educational only).

Two models:
  * StockPredictor        - Random Forest on a sliding window of past closes
  * simple_linear_prediction - linear regression trend line (fallback)

NOTE: stock prices are very hard to predict. Treat output as a demo,
not as trading advice.
"""
from datetime import timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression


def _next_business_days(last_date, days: int) -> list:
    dates, d = [], pd.Timestamp(last_date)
    while len(dates) < days:
        d += timedelta(days=1)
        if d.weekday() < 5:          # skip Sat/Sun
            dates.append(d)
    return dates


class StockPredictor:
    def __init__(self):                       # NOTE: double underscores!
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.test_score = None

    def prepare_data(self, df, lookback: int = 30):
        if df is None or len(df) < lookback + 1:
            return None, None
        close = df["Close"].values
        X = np.array([close[i - lookback:i] for i in range(lookback, len(close))])
        y = close[lookback:]
        return X, y

    def train_model(self, df, lookback: int = 30) -> bool:
        X, y = self.prepare_data(df, lookback)
        if X is None or len(X) < 20:
            return False
        split = int(0.8 * len(X))             # time-ordered split (no shuffling)
        self.model.fit(X[:split], y[:split])
        self.test_score = self.model.score(X[split:], y[split:])
        return True

    def predict_next_days(self, df, days: int = 7, lookback: int = 30):
        if df is None or len(df) < lookback + 20 or not self.train_model(df, lookback):
            return None
        window = df["Close"].values[-lookback:].copy()
        preds = []
        for _ in range(days):                  # feed each prediction back in
            p = float(self.model.predict(window.reshape(1, -1))[0])
            preds.append(p)
            window = np.append(window[1:], p)
        current = float(df["Close"].iloc[-1])
        return {
            "dates": _next_business_days(df.index[-1], days),
            "predictions": preds,
            "current_price": current,
            "predicted_change": (preds[-1] - current) / current * 100,
        }

    def get_prediction_confidence(self, df) -> int:
        """Rough confidence from volatility: calmer stock -> higher number."""
        if df is None or len(df) < 50:
            return 0
        vol = df["Close"].pct_change().dropna().std()
        return 85 if vol < 0.02 else 70 if vol < 0.03 else 55 if vol < 0.05 else 40


def simple_linear_prediction(df, days: int = 7):
    if df is None or len(df) < 30:
        return None
    recent = df.tail(60)
    X = np.arange(len(recent)).reshape(-1, 1)
    model = LinearRegression().fit(X, recent["Close"].values)
    preds = model.predict(np.arange(len(recent), len(recent) + days).reshape(-1, 1))
    current = float(df["Close"].iloc[-1])
    return {
        "dates": _next_business_days(df.index[-1], days),
        "predictions": preds.tolist(),
        "current_price": current,
        "predicted_change": (preds[-1] - current) / current * 100,
    }


def calculate_support_resistance(df):
    if df is None or len(df) < 20:
        return None
    recent = df.tail(50)
    support, resistance = float(recent["Low"].min()), float(recent["High"].max())
    price = float(df["Close"].iloc[-1])
    return {
        "support": support,
        "resistance": resistance,
        "current": price,
        "distance_to_support": (price - support) / price * 100,
        "distance_to_resistance": (resistance - price) / price * 100,
    }
