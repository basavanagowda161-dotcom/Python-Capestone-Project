"""
app.py - Streamlit dashboard (run with:  streamlit run app.py)
Pages: Dashboard · Live Data · AI Chatbot · Predictions · Technical Analysis · About
"""
from datetime import datetime

import plotly.graph_objects as go
import pandas as pd
import pytz
import streamlit as st

from chatbot import StockChatbot
from stock_predictor import (StockPredictor, calculate_support_resistance,
                             simple_linear_prediction)
from utils import (INDIAN_STOCKS, US_STOCKS, calculate_technical_indicators,
                   currency_symbol, fetch_global_quote, fetch_stock_data,
                   fetch_stock_data_hybrid, get_market_overview,
                   get_stock_recommendation)

# ----------------------------------------------------------------------------
# Page config + styling
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Stock Exchange Dashboard", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.stApp {background: linear-gradient(135deg,#1a237e 0%,#283593 30%,#3949ab 65%,#5c6bc0 100%); color:#fff;}
h1,h2,h3,h4,.stMarkdown {color:#fff !important;}
.page-header {font-size:40px; font-weight:900; text-align:center; margin:10px 0 25px;
  background:linear-gradient(90deg,#ffd700,#ffed4e,#ffd700); -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;}
.navbar {background:linear-gradient(135deg,#ff6f00,#ff9800); padding:22px 30px; border-radius:18px;
  margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;
  box-shadow:0 8px 30px rgba(255,111,0,.5);}
.navbar h1 {margin:0; font-size:34px; color:#fff !important;}
.navbar .pill {background:rgba(255,255,255,.2); padding:10px 18px; border-radius:12px;
  font-weight:700; margin-left:12px; display:inline-block;}
.stButton > button {border-radius:12px; font-weight:700;}
[data-testid="stMetricValue"] {color:#ffd700 !important; font-weight:900;}
[data-testid="stMetricLabel"] {color:#fff !important;}
.stAlert {border-radius:12px;}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Market status (NSE hours: Mon-Fri, 9:15-15:30 IST)
# ----------------------------------------------------------------------------
now_ist = datetime.now(pytz.timezone("Asia/Kolkata"))
minutes = now_ist.hour * 60 + now_ist.minute
is_open = now_ist.weekday() < 5 and (9 * 60 + 15) <= minutes <= (15 * 60 + 30)

st.markdown(f"""
<div class="navbar">
  <div><h1>📈 Stock Exchange Dashboard</h1>
       <div style="font-weight:600">⚡ Real-time market analysis &amp; AI predictions</div></div>
  <div><span class="pill">{'🟢 Market Open' if is_open else '🔴 Market Closed'}</span>
       <span class="pill">🕐 {now_ist.strftime('%I:%M %p IST')}</span></div>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("page", "Dashboard")
ss.setdefault("chatbot", StockChatbot())
ss.setdefault("chat_history", [])

PAGES = {"🏠 Dashboard": "Dashboard", "📡 Live Data": "Live Data", "🤖 AI Chatbot": "AI Chatbot",
         "🔮 Predictions": "Predictions", "📊 Analysis": "Technical Analysis", "ℹ️ About": "About"}

for col, (label, name) in zip(st.columns(len(PAGES)), PAGES.items()):
    if col.button(label, use_container_width=True,
                  type="primary" if ss.page == name else "secondary"):
        ss.page = name
        st.rerun()

with st.expander("⚙️ Settings"):
    c1, c2 = st.columns(2)
    market = c1.selectbox("Market", ["NSE (India)", "BSE (India)", "US Markets"])
    use_av = c2.radio("Data source", ["Yahoo Finance", "Alpha Vantage"], horizontal=True) == "Alpha Vantage"

STOCKS = (INDIAN_STOCKS["NSE"] if market.startswith("NSE") else
          INDIAN_STOCKS["BSE"] if market.startswith("BSE") else US_STOCKS)


# ----------------------------------------------------------------------------
# Cached data helpers (avoid hitting the APIs on every click)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_history(symbol, use_alpha):
    return fetch_stock_data_hybrid(symbol, True) if use_alpha else fetch_stock_data(symbol)


@st.cache_data(ttl=120, show_spinner=False)
def load_quote(symbol, use_alpha):
    return fetch_global_quote(symbol, use_alpha_vantage=use_alpha)


@st.cache_data(ttl=120, show_spinner=False)
def load_overview():
    return get_market_overview()


def stock_picker(key, label="Stock"):
    return st.selectbox(label, list(STOCKS), key=key,
                        format_func=lambda s: f"{s} - {STOCKS[s]}")


def header(text):
    st.markdown(f'<h1 class="page-header">{text}</h1>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# PAGES
# ----------------------------------------------------------------------------
def page_dashboard():
    header("📊 Live Market Dashboard")
    c1, c2, c3 = st.columns([3, 1.5, 1])
    symbol = stock_picker("dash_stock", "🔍 Select stock")
    days = {"1 Month": 22, "3 Months": 66, "6 Months": 130}[c2.selectbox("📅 Range", ["1 Month", "3 Months", "6 Months"], index=1)]
    if c3.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    with st.spinner(f"Loading {symbol}..."):
        quote, df = load_quote(symbol, use_av), load_history(symbol, use_av)
    if not quote or df is None:
        st.error("No data returned. Check the symbol / your internet / API limits.")
        return

    cur = currency_symbol(symbol)
    m = st.columns(5)
    m[0].metric("💰 Price", f"{cur}{float(quote['05. price']):,.2f}", quote["09. change"])
    m[1].metric("📊 Change", quote["10. change percent"])
    m[2].metric("📈 High", f"{cur}{quote['03. high']}")
    m[3].metric("📉 Low", f"{cur}{quote['04. low']}")
    m[4].metric("📦 Volume", f"{float(quote['06. volume'])/1e6:.2f}M")

    if len(df) < 50:
        st.warning(f"Only {len(df)} days of data came back for {symbol} - indicators need 50+. "
                   "Try another stock, click Refresh, or switch the data source in Settings.")
    df = calculate_technical_indicators(df)
    st.markdown(f"### 🎯 Signal: {get_stock_recommendation(df)}")
    rsi = df["RSI"].iloc[-1]
    if pd.notna(rsi):
        (st.error if rsi > 70 else st.success if rsi < 30 else st.info)(
            f"RSI {rsi:.1f} - " + ("Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"))

    view = df.tail(days)
    fig = go.Figure(go.Candlestick(x=view.index, open=view["Open"], high=view["High"],
                                   low=view["Low"], close=view["Close"], name="OHLC"))
    for col, color in (("SMA_20", "orange"), ("SMA_50", "red")):
        fig.add_trace(go.Scatter(x=view.index, y=view[col], name=col, line=dict(color=color)))
    fig.update_layout(title=f"{STOCKS[symbol]} price", height=550, template="plotly_white",
                      xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)


def page_live():
    header("📡 Live Market Feed")
    st.subheader("Major indices")
    overview = load_overview()
    if overview:
        for col, (name, d) in zip(st.columns(len(overview)), overview.items()):
            col.metric(name, f"{d['price']:,.2f}", f"{d['change_percent']:+.2f}%")
    else:
        st.warning("Couldn't load index data.")

    st.subheader(f"Watchlist - {market}")
    if st.button("🔄 Load live prices", type="primary"):
        rows, bar = [], st.progress(0.0)
        symbols = list(STOCKS)[:12]
        for i, s in enumerate(symbols):
            q = load_quote(s, False)
            if q:
                rows.append({"Symbol": s, "Company": STOCKS[s], "Price": float(q["05. price"]),
                             "Change %": float(q["10. change percent"].strip("%")),
                             "Volume": int(q["06. volume"])})
            bar.progress((i + 1) / len(symbols))
        bar.empty()
        if rows:
            st.dataframe(pd.DataFrame(rows).sort_values("Change %", ascending=False),
                         use_container_width=True, hide_index=True)


def page_chatbot():
    header("🤖 AI Stock Assistant")
    for role, text in ss.chat_history:
        with st.chat_message(role):
            st.markdown(text)

    quick = st.columns(5)
    shortcuts = {"💰 RELIANCE price": "price of RELIANCE.NS", "📊 Analyze TCS": "analyze TCS",
                 "🎯 Buy INFY?": "should I buy INFY", "📈 AAPL price": "price of AAPL"}
    prompt = None
    for col, (label, text) in zip(quick, shortcuts.items()):
        if col.button(label, use_container_width=True):
            prompt = text
    if quick[4].button("🗑️ Clear", use_container_width=True):
        ss.chat_history = []
        st.rerun()

    prompt = st.chat_input("Ask about a stock... (type 'help')") or prompt
    if prompt:
        ss.chat_history.append(("user", prompt))
        with st.spinner("Thinking..."):
            ss.chat_history.append(("assistant", ss.chatbot.process_query(prompt)))
        st.rerun()


def page_predictions():
    header("🔮 AI Price Predictions")
    st.warning("⚠️ Educational purposes only. Not financial advice!")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        symbol = stock_picker("pred_stock")
    days = c2.slider("Forecast days", 1, 14, 7)
    model = c3.selectbox("Model", ["Linear Regression", "Random Forest"])

    if st.button("🔮 Predict", type="primary"):
        df = fetch_stock_data(symbol, period="1y")
        if df is None or len(df) < 60:
            st.error("Not enough history for this stock.")
            return
        predictor = StockPredictor()
        pred = (simple_linear_prediction(df, days) if model == "Linear Regression"
                else predictor.predict_next_days(df, days))
        if not pred:
            st.error("Prediction failed - not enough data.")
            return

        cur = currency_symbol(symbol)
        m = st.columns(4)
        m[0].metric("Current", f"{cur}{pred['current_price']:,.2f}")
        m[1].metric(f"In {days} days", f"{cur}{pred['predictions'][-1]:,.2f}")
        m[2].metric("Change", f"{pred['predicted_change']:+.2f}%")
        m[3].metric("Confidence (rough)", f"{predictor.get_prediction_confidence(df)}%")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index[-60:], y=df["Close"][-60:], name="Historical"))
        fig.add_trace(go.Scatter(x=pred["dates"], y=pred["predictions"], name="Forecast",
                                 line=dict(color="red", dash="dash")))
        fig.update_layout(title="Price forecast", height=500, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

        sr = calculate_support_resistance(df)
        if sr:
            st.info(f"Support {cur}{sr['support']:,.2f} ({sr['distance_to_support']:.1f}% below) · "
                    f"Resistance {cur}{sr['resistance']:,.2f} ({sr['distance_to_resistance']:.1f}% above)")


def page_analysis():
    header("📊 Technical Analysis")
    symbol = stock_picker("ta_stock")
    if st.button("📊 Analyze", type="primary"):
        df = fetch_stock_data(symbol, period="1y")
        if df is None or len(df) < 50:
            st.error("Not enough data.")
            return
        df = calculate_technical_indicators(df)
        t1, t2, t3, t4 = st.tabs(["RSI", "MACD", "Bollinger Bands", "Summary"])

        with t1:
            fig = go.Figure(go.Scatter(x=df.index, y=df["RSI"], name="RSI"))
            fig.add_hline(y=70, line_dash="dash", line_color="red")
            fig.add_hline(y=30, line_dash="dash", line_color="green")
            fig.update_layout(height=400, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        with t2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD"))
            fig.add_trace(go.Scatter(x=df.index, y=df["Signal_Line"], name="Signal"))
            fig.update_layout(height=400, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        with t3:
            fig = go.Figure()
            for col in ("Close", "BB_Upper", "BB_Middle", "BB_Lower"):
                fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col))
            fig.update_layout(height=400, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        with t4:
            last = df.iloc[-1]
            c = st.columns(4)
            c[0].metric("RSI", f"{last['RSI']:.1f}")
            c[1].metric("MACD", f"{last['MACD']:.2f}")
            c[2].metric("SMA 20", f"{last['SMA_20']:.2f}")
            c[3].metric("SMA 50", f"{last['SMA_50']:.2f}")
            st.markdown(f"### Signal: {get_stock_recommendation(df)}")


def page_about():
    header("ℹ️ About This Project")
    st.markdown("""
**Stock Exchange Prediction Dashboard** - a Streamlit app for NSE, BSE and US stocks.

- 📊 Live prices & candlestick charts (Yahoo Finance, optional Alpha Vantage)
- 📐 Indicators: SMA, EMA, RSI, MACD, Bollinger Bands
- 🔮 Forecasts: Linear Regression & Random Forest
- 🤖 Rule-based chatbot for prices, analysis and comparisons

**Tech:** Python · Streamlit · pandas · NumPy · scikit-learn · Plotly · yfinance

⚠️ *Predictions are for learning only. Never trade real money based on this app.*
""")


{"Dashboard": page_dashboard, "Live Data": page_live, "AI Chatbot": page_chatbot,
 "Predictions": page_predictions, "Technical Analysis": page_analysis,
 "About": page_about}[ss.page]()

st.markdown("---")
st.caption("📈 Stock Exchange Prediction Dashboard · Educational use only")