"""Check that Yahoo Finance returns data for NSE and US stocks."""
import yfinance as yf

NSE = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]
US = ["AAPL", "MSFT", "GOOGL"]

for group, symbols in (("NSE", NSE), ("US", US)):
    print(f"\n=== {group} ===")
    for s in symbols:
        try:
            data = yf.Ticker(s).history(period="5d")
            print(f"✅ {s}: {data['Close'].iloc[-1]:.2f}" if len(data) else f"❌ {s}: no data")
        except Exception as e:
            print(f"❌ {s}: {str(e)[:60]}")
