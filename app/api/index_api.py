# --- app/api/index_api.py ---

import os
import traceback
from datetime import date
from typing import List, Optional, Dict, Any
from io import StringIO

import pandas as pd
import requests
from flask import Flask, jsonify, render_template
import yfinance as yf

# ======================================================================
# 🛑 CORE FLASK INITIALIZATION (One and only one instance)
# 🛑 VERCEL FIX: Use absolute path to templates/static folders
# ======================================================================

# This is the standard root path for serverless functions on Vercel
ABSOLUTE_PROJECT_ROOT = "/var/task"

app = Flask(
    __name__,
    template_folder=os.path.join(ABSOLUTE_PROJECT_ROOT, 'app', 'templates'),
    static_folder=os.path.join(ABSOLUTE_PROJECT_ROOT, 'app', 'static')
)

# Constants
NSE_SUFFIX = ".NS"

# ======================================================================
# 🛑 ERROR HANDLER
# ======================================================================

@app.errorhandler(Exception)
def handle_uncaught_exception(e):
    # Log the traceback to the Vercel logs
    app.logger.error(traceback.format_exc())
    # Return a 500 response with the traceback in the body
    return jsonify({
        "error": "Internal Server Error (DEBUG MODE - PLEASE SHARE THIS TRACEBACK)",
        "message": str(e),
        "traceback": traceback.format_exc().splitlines()
    }), 500

# ======================================================================
# 1. INDEX SYMBOL FETCH FUNCTIONS
# ======================================================================

def get_sensex_30_symbols() -> List[str]:
    """
    Returns a reliable hardcoded list of BSE SENSEX 30 constituents.
    """
    SENSEX_30_LIST = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "TCS", "KOTAKBANK",
        "AXISBANK", "SBIN", "LT", "ASIANPAINT", "MARUTI", "BAJFINANCE", "HCLTECH",
        "TITAN", "SUNPHARMA", "NESTLEIND", "ITC", "TATASTEEL", "POWERGRID",
        "INDUSINDBK", "ULTRACEMCO", "TECHM", "M&M", "TATASTEEL", "BAJAJFINSV",
        "HINDALCO", "WIPRO", "BHARTIARTL", "DRREDDY"
    ]
    return SENSEX_30_LIST

def get_nifty_50_symbols() -> List[str]:
    """
    Downloads the current Nifty 50 constituents list from the NSE archives,
    with a robust fallback if the network request fails.
    """
    NIFTY_50_URL = 'https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br'
    }

    symbol_list = ["RELIANCE", "HDFCBANK", "TCS", "ICICIBANK", "INFY", "KOTAKBANK", "HINDUNILVR"] # Fallback

    try:
        with requests.Session() as session:
            session.headers.update(HEADERS)
            session.get("https://www.nseindia.com", timeout=10) # Get a session cookie

            response = session.get(NIFTY_50_URL, timeout=10)
            response.raise_for_status()

        csv_content = StringIO(response.content.decode('utf-8'))
        df = pd.read_csv(csv_content)
        symbol_list = df['Symbol'].tolist()

    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading data from NSE: {e}. Using fallback list.")
    except KeyError:
        print("❌ Error: 'Symbol' column not found. File format changed. Using fallback list.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}. Using fallback list.")

    return symbol_list

# ======================================================================
# 2. CORE DATA FETCH FUNCTION FOR A SINGLE STOCK
# ======================================================================

def fetch_single_stock_metrics(symbol: str) -> Dict[str, Any]:
    """
    Fetches required metrics (Last Price, 52W High/Low, Events) for a single stock.
    """
    ticker_symbol = f"{symbol}{NSE_SUFFIX}"
    today = date.today()
    NSE_DETAIL_URL = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        last_price = info.get('previousClose', info.get('regularMarketPreviousClose'))
        if last_price is None:
            history = ticker.history(period="1d", interval="1d", timeout=15)
            last_price = history['Close'].iloc[-1] if not history.empty else None

        price = last_price
        high_52w = info.get('fiftyTwoWeekHigh')
        low_52w = info.get('fiftyTwoWeekLow')
        low_nearness_percent = None

        if price and low_52w and high_52w and price >= low_52w:
            price_range = high_52w - low_52w
            if price_range > 0:
                low_nearness_percent = round(((price - low_52w) / price_range) * 100, 2)
            else:
                low_nearness_percent = 0.0

            print(f"DEBUG: {symbol} - Low Nearness %: {low_nearness_percent}")

        # NOTE: Your original logic for 'actions' (upcoming events) was incomplete/empty.
        # Keeping it as an empty list to prevent errors.
        actions = []

        return {
            "symbol": symbol,
            "name": info.get('longName', symbol),
            "lastPrice": round(float(price), 2) if price else None,
            "high52Week": high_52w,
            "low52Week": low_52w,
            "lowNearnessPercentage": low_nearness_percent,
            "upcomingEvents": actions,
            "detailLink": NSE_DETAIL_URL
        }

    except Exception:
        # Returning structured error data
        return {
            "symbol": symbol,
            "name": f"Error/No Data for {symbol}",
            "lastPrice": None,
            "high52Week": None,
            "low52Week": None,
            "lowNearnessPercentage": None,
            "upcomingEvents": [],
            "detailLink": NSE_DETAIL_URL
        }

# ======================================================================
# 3. UI/API ENDPOINTS
# ======================================================================

@app.route('/', methods=['GET'])
def render_nifty_ui():
    """Renders the main NIFTY50 HTML template."""
    return render_template('index.html')

@app.route('/sensex', methods=['GET'])
def render_sensex_ui():
    """Renders the SENSEX HTML template."""
    return render_template('sensex.html')

@app.route('/api/historical/NIFTY50', methods=['GET'])
def get_nifty50_data():
    """Endpoint to fetch key metrics for all stocks in NIFTY 50 dynamically."""
    symbols_to_fetch = get_nifty_50_symbols()
    results = []

    # Note: Removed the warning check for fallback list, as the function handles it internally.
    # The status will still be 'success' even if a fallback is used.

    for symbol in symbols_to_fetch:
        data = fetch_single_stock_metrics(symbol)
        if data['lastPrice'] is not None:
            results.append(data)

    return jsonify({
        "status": "success",
        "index": "NIFTY50",
        "total_constituents": len(symbols_to_fetch),
        "total_stocks_fetched": len(results),
        "data": results
    })

@app.route('/api/historical/SENSEX', methods=['GET'])
def get_sensex_data():
    """Endpoint to fetch key metrics for all stocks in SENSEX 30."""
    symbols_to_fetch = get_sensex_30_symbols()
    results = []

    for symbol in symbols_to_fetch:
        data = fetch_single_stock_metrics(symbol)
        if data['lastPrice'] is not None:
            results.append(data)

    return jsonify({
        "status": "success",
        "index": "SENSEX",
        "total_constituents": len(symbols_to_fetch),
        "total_stocks_fetched": len(results),
        "data": results
    })

# ======================================================================
# 4. LOCAL RUNNER
# ======================================================================

if __name__ == '__main__':
    # NOTE: When running locally, the absolute Vercel path will NOT work.
    # The local Flask app defaults to looking in the 'templates' folder next to the script.
    # To run locally with this code, you may need to temporarily revert the 'app = Flask(...)'
    # to the simple form: app = Flask(__name__, template_folder='../templates', static_folder='../static')
    print("Starting Flask Index API server on http://127.0.0.1:3000/")
    app.run(debug=True, port=3000)