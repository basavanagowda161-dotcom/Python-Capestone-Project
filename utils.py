"""
utils.py - data fetching + technical indicators.

Yahoo Finance (yfinance) is the main source. Alpha Vantage is optional
(free tier: 5 calls/min, 500/day) and falls back to Yahoo on failure.
"""
import os
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf

# --------------------------------------------------------------------------
# Config - the key is read from the environment / Streamlit secrets,
# NEVER hard-code it in source files.
# --------------------------------------------------------------------------
def _get_av_key() -> str:
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("ALPHA_VANTAGE_API_KEY", "")
    except Exception:
        return ""


ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
OHLCV = ["Open", "High", "Low", "Close", "Volume"]

# --------------------------------------------------------------------------
# Stock lists
# --------------------------------------------------------------------------
_NSE = {
    "RELIANCE.NS": "Reliance Industries", "TCS.NS": "Tata Consultancy Services",
    "HDFCBANK.NS": "HDFC Bank", "INFY.NS": "Infosys", "ICICIBANK.NS": "ICICI Bank",
    "HINDUNILVR.NS": "Hindustan Unilever", "ITC.NS": "ITC Ltd",
    "SBIN.NS": "State Bank of India", "BHARTIARTL.NS": "Bharti Airtel",
    "KOTAKBANK.NS": "Kotak Mahindra Bank", "LT.NS": "Larsen & Toubro",
    "AXISBANK.NS": "Axis Bank", "MARUTI.NS": "Maruti Suzuki", "TITAN.NS": "Titan Company",
    "WIPRO.NS": "Wipro", "BAJFINANCE.NS": "Bajaj Finance", "ASIANPAINT.NS": "Asian Paints",
    "HCLTECH.NS": "HCL Technologies", "SUNPHARMA.NS": "Sun Pharma",
    "TATAMOTORS.NS": "Tata Motors", "TATASTEEL.NS": "Tata Steel", "ONGC.NS": "ONGC",
    "NTPC.NS": "NTPC", "TECHM.NS": "Tech Mahindra", "M&M.NS": "Mahindra & Mahindra",
}
INDIAN_STOCKS = {
    "NSE": _NSE,
    "BSE": {k.replace(".NS", ".BO"): v for k, v in _NSE.items()},  # same companies, BSE suffix
}

US_STOCKS = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon",
    "TSLA": "Tesla", "META": "Meta Platforms", "NVDA": "NVIDIA", "JPM": "JPMorgan Chase",
    "V": "Visa", "WMT": "Walmart", "NFLX": "Netflix", "DIS": "Disney", "AMD": "AMD",
    "INTC": "Intel", "ORCL": "Oracle", "KO": "Coca-Cola", "PEP": "PepsiCo",
}

MARKET_INDICES = {
    "^NSEI": "NIFTY 50", "^BSESN": "SENSEX", "^GSPC": "S&P 500",
    "^DJI": "Dow Jones", "^IXIC": "NASDAQ",
}


def currency_symbol(symbol: str) -> str:
    return "₹" if symbol.endswith((".NS", ".BO")) or symbol.startswith("^NSEI") or symbol.startswith("^BSESN") else "$"


# --------------------------------------------------------------------------
# Yahoo Finance
# --------------------------------------------------------------------------
def fetch_stock_data(symbol: str, period: str = "6mo") -> pd.DataFrame | None:
    """Daily OHLCV history from Yahoo Finance (None if nothing came back)."""
    try:
        df = yf.Ticker(symbol).history(period=period, interval="1d")
        if df is None or df.empty:
            return None
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df[OHLCV]
    except Exception as e:
        print(f"[fetch_stock_data] {symbol}: {e}")
        return None


def fetch_intraday_data(symbol: str, interval: str = "5m") -> pd.DataFrame | None:
    try:
        df = yf.Ticker(symbol).history(period="1d", interval=interval)
        return None if df is None or df.empty else df[OHLCV]
    except Exception as e:
        print(f"[fetch_intraday_data] {symbol}: {e}")
        return None


def fetch_global_quote(symbol: str, use_alpha_vantage: bool = False) -> dict | None:
    """
    Latest quote in Alpha-Vantage key format
    ('05. price', '09. change', ...) so the UI works with either source.
    """
    if use_alpha_vantage:
        q = fetch_alpha_vantage_quote(symbol)
        if q:
            return q
        print(f"Alpha Vantage failed for {symbol}, using Yahoo Finance")

    df = fetch_stock_data(symbol, period="5d")
    if df is None or len(df) < 1:
        return None
    last = df.iloc[-1]
    prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else float(last["Open"])
    price = float(last["Close"])
    change = price - prev_close
    pct = (change / prev_close * 100) if prev_close else 0.0
    return {
        "01. symbol": symbol,
        "02. open": f"{last['Open']:.2f}",
        "03. high": f"{last['High']:.2f}",
        "04. low": f"{last['Low']:.2f}",
        "05. price": f"{price:.2f}",
        "06. volume": str(int(last["Volume"])),
        "07. latest trading day": df.index[-1].strftime("%Y-%m-%d"),
        "08. previous close": f"{prev_close:.2f}",
        "09. change": f"{change:.2f}",
        "10. change percent": f"{pct:.2f}%",
    }


def get_stock_info(symbol: str) -> dict | None:
    try:
        info = yf.Ticker(symbol).info
        return {
            "name": info.get("longName", symbol),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "52_week_high": info.get("fiftyTwoWeekHigh", 0),
            "52_week_low": info.get("fiftyTwoWeekLow", 0),
        }
    except Exception:
        return None


def get_market_overview() -> dict:
    out = {}
    for sym, name in MARKET_INDICES.items():
        df = fetch_stock_data(sym, period="5d")
        if df is None or len(df) < 2:
            continue
        price, prev = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
        out[name] = {"symbol": sym, "price": price, "change": price - prev,
                     "change_percent": (price - prev) / prev * 100 if prev else 0}
    return out


# --------------------------------------------------------------------------
# Alpha Vantage (optional)
# --------------------------------------------------------------------------
def _av_symbol(symbol: str) -> str:
    # Alpha Vantage uses e.g. RELIANCE.BSE instead of RELIANCE.NS / .BO
    return symbol.replace(".NS", ".BSE").replace(".BO", ".BSE")


def _av_get(params: dict) -> dict | None:
    key = _get_av_key()
    if not key:
        print("Alpha Vantage key not set - skipping")
        return None
    try:
        r = requests.get(ALPHA_VANTAGE_BASE_URL, params={**params, "apikey": key}, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Alpha Vantage error: {e}")
        return None


def fetch_alpha_vantage_quote(symbol: str) -> dict | None:
    data = _av_get({"function": "GLOBAL_QUOTE", "symbol": _av_symbol(symbol)})
    return data.get("Global Quote") or None if data else None


def fetch_alpha_vantage_daily(symbol: str, outputsize: str = "compact") -> pd.DataFrame | None:
    data = _av_get({"function": "TIME_SERIES_DAILY", "symbol": _av_symbol(symbol),
                    "outputsize": outputsize})
    if not data or "Time Series (Daily)" not in data:
        return None
    df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.rename(columns={"1. open": "Open", "2. high": "High", "3. low": "Low",
                            "4. close": "Close", "5. volume": "Volume"}).astype(float)
    return df.sort_index()[OHLCV]


def fetch_alpha_vantage_company_overview(symbol: str) -> dict | None:
    data = _av_get({"function": "OVERVIEW", "symbol": _av_symbol(symbol)})
    return data if data and "Symbol" in data else None


def fetch_stock_data_hybrid(symbol: str, prefer_alpha_vantage: bool = True) -> pd.DataFrame | None:
    """Alpha Vantage first, Yahoo Finance as fallback."""
    if prefer_alpha_vantage:
        df = fetch_alpha_vantage_daily(symbol)
        if df is not None and len(df) > 0:
            return df
    return fetch_stock_data(symbol)


# --------------------------------------------------------------------------
# Technical indicators
# --------------------------------------------------------------------------
def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return df
    df = df.copy()          # always add the columns (NaN when history is short)
    close = df["Close"]

    df["SMA_20"] = close.rolling(20).mean()
    df["SMA_50"] = close.rolling(50).mean()
    df["EMA_12"] = close.ewm(span=12, adjust=False).mean()
    df["EMA_26"] = close.ewm(span=26, adjust=False).mean()

    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["Signal_Line"] = df["MACD"].ewm(span=9, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))

    std = close.rolling(20).std()
    df["BB_Middle"] = df["SMA_20"]
    df["BB_Upper"] = df["BB_Middle"] + 2 * std
    df["BB_Lower"] = df["BB_Middle"] - 2 * std
    return df


def get_stock_recommendation(df: pd.DataFrame) -> str:
    """Rule-based score from RSI, MACD, SMA-20 and Bollinger Bands."""
    if df is None or len(df) < 50 or "RSI" not in df:
        return "Insufficient Data"
    latest = df.iloc[-1]
    if latest[["RSI", "MACD", "Signal_Line", "SMA_20", "BB_Lower", "BB_Upper"]].isna().any():
        return "Insufficient Data"

    score = 0
    score += 2 if latest["RSI"] < 30 else -2 if latest["RSI"] > 70 else 0
    score += 1 if latest["MACD"] > latest["Signal_Line"] else -1
    score += 1 if latest["Close"] > latest["SMA_20"] else -1
    score += 1 if latest["Close"] < latest["BB_Lower"] else -1 if latest["Close"] > latest["BB_Upper"] else 0

    if score >= 3:
        return "🟢 STRONG BUY"
    if score >= 1:
        return "🟢 BUY"
    if score <= -3:
        return "🔴 STRONG SELL"
    if score <= -1:
        return "🔴 SELL"
    return "🟡 HOLD"