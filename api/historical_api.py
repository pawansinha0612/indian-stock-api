import pandas as pd
from flask import Flask, jsonify
from datetime import date
import yfinance as yf # The stable source for all data

app = Flask(__name__)

# --- Configuration ---
END_DATE = date.today()
# Fetching slightly more than 1 year to ensure 52-week metrics are robust
START_DATE = date(END_DATE.year - 2, END_DATE.month, END_DATE.day)

# Base suffix for Indian National Stock Exchange (NSE) stocks on Yahoo Finance
NSE_SUFFIX = ".NS"

# ======================================================================
# 1. UNIFIED DATA FETCH FUNCTION
# ======================================================================

def fetch_stock_data(symbol: str) -> dict:
    """Fetches EOD, Corporate Actions, and 52-Week data using yfinance."""

    ticker_symbol = f"{symbol}{NSE_SUFFIX}"
    ticker = yf.Ticker(ticker_symbol)

    # --- 52-Week High/Low (from ticker info) ---
    info = ticker.info
    metrics = {
        "low52Week": info.get('fiftyTwoWeekLow'),
        "high52Week": info.get('fiftyTwoWeekHigh')
    }

    # --- EOD Prices (Historical Data) ---
    df_history = ticker.history(start=START_DATE, end=END_DATE)

    if df_history.empty:
        return {"error": f"No historical data found for {symbol} on Yahoo Finance."}

    # Convert DataFrame to JSON list for EOD prices
    eod_list = []
    for index, row in df_history.iterrows():
        eod_list.append({
            'date': index.strftime('%Y-%m-%d'),
            'open': round(row['Open'], 2),
            'high': round(row['High'], 2),
            'low': round(row['Low'], 2),
            'close': round(row['Close'], 2),
            'volume': int(row['Volume'])
        })

    # --- Corporate Actions (Dividends and Splits) ---
    corporate_actions = []

    # 1. Dividends
    df_dividends = ticker.dividends.reset_index()
    for _, row in df_dividends.iterrows():
        corporate_actions.append({
            "date": row['Date'].strftime('%Y-%m-%d'),
            "type": "Dividend",
            "value": round(row['Dividends'], 2)
        })

    # 2. Splits
    df_splits = ticker.splits.reset_index()
    for _, row in df_splits.iterrows():
        # Splits are returned as a ratio (e.g., 2.0 for 2:1 split)
        corporate_actions.append({
            "date": row['Date'].strftime('%Y-%m-%d'),
            "type": "Split",
            "value": f"1:{round(1/row['Stock Splits'])}" # Format as X:1
        })

    return {
        "metrics": metrics,
        "historicalData": eod_list,
        "corporateActions": corporate_actions
    }

# ======================================================================
# 2. API ENDPOINT DEFINITION
# ======================================================================

@app.route('/api/historical/<symbol>', methods=['GET'])
def get_historical_stock_data(symbol: str):
    """
    Endpoint to fetch historical EOD, Corporate Actions, and 52-Week data.
    Example: /api/historical/SBIN
    """
    ticker = symbol.upper()

    data = fetch_stock_data(ticker)

    if "error" in data:
        return jsonify({
            "status": "error",
            "message": data["error"]
        }), 404

    # Compile Final Response
    return jsonify({
        "status": "success",
        "symbol": ticker,
        "data_source": "Yahoo Finance (via yfinance)",
        "date_range": f"{START_DATE} to {END_DATE}",
        "metrics": data['metrics'],
        "historicalData": data['historicalData'],
        "corporateActions": data['corporateActions']
    })

# ======================================================================
# 3. MAIN RUN BLOCK
# ======================================================================

if __name__ == '__main__':
    print(f"Starting Flask Historical API server on http://127.0.0.1:3000/")
    print(f"Data range: {START_DATE} to {END_DATE}")
    app.run(debug=True, port=3000)