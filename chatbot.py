"""
chatbot.py - rule-based stock chatbot (keyword matching + live data).
No external AI/LLM is used; it routes the question to a handler by keywords.
"""
import re
from datetime import datetime

from utils import (calculate_technical_indicators, currency_symbol,
                   fetch_global_quote, fetch_stock_data, get_stock_info,
                   get_stock_recommendation)

# name / ticker typed by the user  ->  Yahoo Finance symbol
SYMBOLS = {
    "APPLE": "AAPL", "AAPL": "AAPL", "MICROSOFT": "MSFT", "MSFT": "MSFT",
    "GOOGLE": "GOOGL", "GOOGL": "GOOGL", "AMAZON": "AMZN", "AMZN": "AMZN",
    "TESLA": "TSLA", "TSLA": "TSLA", "META": "META", "FACEBOOK": "META",
    "NVIDIA": "NVDA", "NVDA": "NVDA", "NETFLIX": "NFLX", "NFLX": "NFLX",
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFOSYS": "INFY.NS",
    "INFY": "INFY.NS", "HDFC": "HDFCBANK.NS", "HDFCBANK": "HDFCBANK.NS",
    "ICICI": "ICICIBANK.NS", "ICICIBANK": "ICICIBANK.NS", "WIPRO": "WIPRO.NS",
    "ITC": "ITC.NS", "SBI": "SBIN.NS", "SBIN": "SBIN.NS",
}
DISCLAIMER = "⚠️ *Educational purposes only - not financial advice.*"


class StockChatbot:
    def __init__(self):                       # double underscores!
        self.history = []

    # ---------------------------------------------------------------- routing
    def process_query(self, text: str) -> str:
        q = text.lower()
        try:
            if any(w in q for w in ("help", "what can you")):
                return self._help()
            if "compare" in q or " vs " in q or "versus" in q:
                return self._compare(text)
            if any(w in q for w in ("buy", "sell", "invest")):
                return self._analysis(text) + "\n\n" + self._risk_note()
            if "analy" in q:
                return self._analysis(text)
            if any(w in q for w in ("price", "cost", "trading at")):
                return self._price(text)
            if "market" in q:
                return self._market()
            if "top" in q or "best" in q:
                return self._top(q)
            if "news" in q:
                return self._news()
            return self._default()
        except Exception as e:
            return f"⚠️ Something went wrong: {e}\n\nTry rephrasing, or type **help**."

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def extract_symbols(text: str) -> list[str]:
        found = []
        for word in re.findall(r"[A-Za-z0-9&\-\.\^]+", text.upper()):
            sym = word if word.endswith((".NS", ".BO")) else SYMBOLS.get(word)
            if sym and sym not in found:
                found.append(sym)
        return found

    def _one_symbol(self, text):
        syms = self.extract_symbols(text)
        return syms[0] if syms else None

    @staticmethod
    def _risk_note():
        return ("**Before investing:** do your own research, consider your risk tolerance, "
                "diversify, and talk to a licensed financial advisor.")

    # --------------------------------------------------------------- handlers
    def _price(self, text):
        sym = self._one_symbol(text)
        if not sym:
            return "💬 Which stock? Mention a symbol or name, e.g. **AAPL**, **TCS**, **RELIANCE.NS**."
        quote = fetch_global_quote(sym)
        if not quote:
            return f"❌ Couldn't fetch data for **{sym}**. Check the symbol and try again."
        cur = currency_symbol(sym)
        change = float(quote["09. change"])
        emoji = "🟢" if change >= 0 else "🔴"
        return (f"📊 **{sym}**\n\n"
                f"💰 Price: **{cur}{float(quote['05. price']):,.2f}**\n\n"
                f"{emoji} Change: {cur}{change:+.2f} ({quote['10. change percent']})\n\n"
                f"📈 High: {cur}{quote['03. high']} · 📉 Low: {cur}{quote['04. low']}\n\n"
                f"📦 Volume: {int(quote['06. volume']):,}\n\n"
                f"🕐 {datetime.now().strftime('%I:%M %p')}")

    def _analysis(self, text):
        sym = self._one_symbol(text)
        if not sym:
            return "💬 Which stock should I analyze? Give me a symbol or name."
        df = fetch_stock_data(sym)
        if df is None or len(df) < 50:
            return f"❌ Not enough data for **{sym}**."
        df = calculate_technical_indicators(df)
        last, cur = df.iloc[-1], currency_symbol(sym)
        rsi = last["RSI"]
        rsi_note = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
        trend = (df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1) * 100
        return (f"📊 **Analysis: {sym}**\n\n"
                f"💰 Price: {cur}{last['Close']:,.2f}\n\n"
                f"- SMA 20: {cur}{last['SMA_20']:,.2f}\n"
                f"- SMA 50: {cur}{last['SMA_50']:,.2f}\n"
                f"- RSI: {rsi:.1f} ({rsi_note})\n"
                f"- 20-day trend: {trend:+.2f}%\n\n"
                f"🎯 Signal: **{get_stock_recommendation(df)}**\n\n{DISCLAIMER}")

    def _compare(self, text):
        syms = self.extract_symbols(text)[:3]
        if len(syms) < 2:
            return ("💬 Give me at least 2 stocks, e.g. *Compare AAPL and MSFT* "
                    "or *TCS vs INFY*.")
        rows, best = [], None
        for s in syms:
            q = fetch_global_quote(s)
            info = get_stock_info(s) or {}
            if not q:
                continue
            pct = float(q["10. change percent"].replace("%", ""))
            cap = info.get("market_cap") or 0
            rows.append(f"**{s}** - {currency_symbol(s)}{float(q['05. price']):,.2f} "
                        f"({pct:+.2f}%) · Mkt cap {cap/1e9:,.1f}B · P/E {info.get('pe_ratio') or 'N/A'}")
            if best is None or pct > best[1]:
                best = (s, pct)
        if not rows:
            return "❌ Couldn't fetch data for those symbols."
        return "📊 **Comparison**\n\n" + "\n\n".join(rows) + f"\n\n🏆 Best today: **{best[0]}** ({best[1]:+.2f}%)"

    def _market(self):
        from utils import get_market_overview
        data = get_market_overview()
        if not data:
            return "❌ Couldn't load index data right now."
        lines = [f"{'🟢' if v['change'] >= 0 else '🔴'} **{n}**: {v['price']:,.2f} ({v['change_percent']:+.2f}%)"
                 for n, v in data.items()]
        return "📊 **Market Overview**\n\n" + "\n\n".join(lines)

    def _top(self, q):
        if any(w in q for w in ("india", "indian", "nse")):
            return ("📈 **Top Indian stocks to watch**\n\n- IT: TCS, INFY, WIPRO\n"
                    "- Banks: HDFCBANK, ICICIBANK, SBIN\n- Conglomerates: RELIANCE, LT\n"
                    "- FMCG: HINDUNILVR, ITC")
        return ("📈 **Top US stocks to watch**\n\n- Mega cap: AAPL, MSFT, GOOGL, AMZN\n"
                "- AI/Chips: NVDA, AMD\n- Innovation: TSLA, META")

    def _news(self):
        return ("📰 For news, check Economic Times, MoneyControl, NSE India, "
                "Bloomberg, CNBC or Yahoo Finance.")

    def _help(self):
        return ("🤖 **I can help with:**\n\n- Prices: *price of AAPL*\n- Analysis: *analyze TCS*\n"
                "- Signals: *should I buy INFY?*\n- Compare: *TCS vs INFY*\n"
                "- Market: *market overview*\n- Lists: *top Indian stocks*\n\n" + DISCLAIMER)

    def _default(self):
        return "💬 I didn't catch that. Type **help** to see what I can do."


if __name__ == "__main__":
    bot = StockChatbot()
    for q in ["price of AAPL", "analyze RELIANCE.NS", "compare MSFT and GOOGL", "help"]:
        print("👤", q, "\n🤖", bot.process_query(q)[:200], "\n" + "-" * 40)
