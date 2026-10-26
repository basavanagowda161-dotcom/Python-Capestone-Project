"""
Test the Alpha Vantage integration.
Set your key first:   export ALPHA_VANTAGE_API_KEY=xxxx   (Windows: set ALPHA_VANTAGE_API_KEY=xxxx)
Free tier = 5 calls/min, 500/day, so tests are kept small.
"""
from utils import (fetch_alpha_vantage_daily, fetch_alpha_vantage_quote,
                   fetch_stock_data_hybrid)


def test_quote():
    q = fetch_alpha_vantage_quote("AAPL")
    print("Quote AAPL:", "✅ " + q.get("05. price", "?") if q else "❌ failed (key set? rate limit?)")


def test_daily():
    df = fetch_alpha_vantage_daily("MSFT")
    print("Daily MSFT:", f"✅ {len(df)} rows" if df is not None else "❌ failed")


def test_hybrid():
    df = fetch_stock_data_hybrid("RELIANCE.NS")
    print("Hybrid RELIANCE.NS:", f"✅ {len(df)} rows" if df is not None else "❌ failed")


if __name__ == "__main__":
    test_quote()
    test_daily()
    test_hybrid()
