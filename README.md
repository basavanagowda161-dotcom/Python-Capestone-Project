# 📈 Stock Exchange Prediction Dashboard

Streamlit app for NSE / BSE / US stocks: live prices, candlestick charts, technical
indicators, ML price forecasts and a rule-based chatbot.

## Project structure
```
stock-exchange-prediction/
├── app.py                  # Streamlit UI (all pages)
├── utils.py                # data fetching (Yahoo / Alpha Vantage) + indicators
├── chatbot.py              # StockChatbot class
├── stock_predictor.py      # Random Forest + Linear Regression forecasting
├── test_nse.py             # check Yahoo Finance connection
├── test_alpha_vantage.py   # check Alpha Vantage connection
├── requirements.txt
├── .gitignore
└── .streamlit/secrets.toml.example
```

## Run locally
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

## Optional: Alpha Vantage key
Get a free key at https://www.alphavantage.co/support/#api-key, then either
copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste it, or
set an environment variable `ALPHA_VANTAGE_API_KEY`. Without a key the app uses Yahoo Finance only.

## Deploy (Streamlit Community Cloud)
1. Push this folder to a GitHub repo (the `.gitignore` keeps secrets out).
2. Go to https://share.streamlit.io → New app → pick the repo, main file `app.py`.
3. In *Advanced settings → Secrets* paste `ALPHA_VANTAGE_API_KEY = "..."`.

⚠️ Educational use only - not financial advice.
