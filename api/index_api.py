import pandas as pd
import requests
from io import StringIO
from typing import List, Optional, Dict, Any
from flask import Flask, jsonify
import yfinance as yf
from flask import Flask, jsonify, render_template # Add render_template here

import pandas as pd
# ... (other imports) ...
from datetime import date, datetime # <--- Added datetime for comparison
from typing import Dict, Any, List

# ... (Constants and get_nifty_50_symbols function remain the same) ...

NSE_SUFFIX = ".NS"

# --- Add this new function to index_api.py ---

def get_sensex_30_symbols() -> List[str]:
    """
    Returns the current or a reliable hardcoded list of BSE SENSEX 30 constituents.
    (NSE/BSE symbol lists are hard to reliably scrape for free, so we use a robust list).
    """
    # A widely accepted hardcoded list for the SENSEX 30 (use as primary and fallback)
    SENSEX_30_LIST = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "TCS", "KOTAKBANK",
        "AXISBANK", "SBIN", "LT", "ASIANPAINT", "MARUTI", "BAJFINANCE", "HCLTECH",
        "TITAN", "SUNPHARMA", "NESTLEIND", "ITC", "TATASTEEL", "POWERGRID",
        "INDUSINDBK", "ULTRACEMCO", "TECHM", "M&M", "TATASTEEL", "BAJAJFINSV",
        "HINDALCO", "WIPRO", "BHARTIARTL", "DRREDDY"
    ]

    # Note: If you have a reliable way to scrape the BSE website for an official list,
    # you would put that scraping logic here with SENSEX_30_LIST as the fallback.

    return SENSEX_30_LIST

# Note: The existing fetch_single_stock_metrics() function works fine for Sensex
# as it uses yfinance with the .NS suffix, which covers most BSE-listed stocks as well.

# ======================================================================
# 1. DYNAMIC INDEX SYMBOL FETCH FUNCTION (YOUR CODE)
# ======================================================================

# --- index_api.py: Corrected get_nifty_50_symbols function ---

# --- index_api.py: Corrected get_nifty_50_symbols function ---

# --- index_api.py: Corrected get_nifty_50_symbols function ---

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

    # Initialize with the fallback list
    symbol_list = ["RELIANCE", "HDFCBANK", "TCS", "ICICIBANK", "INFY", "KOTAKBANK", "HINDUNILVR"]

    try:
        with requests.Session() as session:
            session.headers.update(HEADERS)
            session.get("https://www.nseindia.com", timeout=10)

            response = session.get(NIFTY_50_URL, timeout=10)
            response.raise_for_status()

        csv_content = StringIO(response.content.decode('utf-8'))
        df = pd.read_csv(csv_content)

        # If successful, overwrite the fallback list
        symbol_list = df['Symbol'].tolist()

    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading data from NSE: {e}. Using fallback list.")
        # If an exception occurs, the function skips to the end, retaining the fallback list.

    except KeyError:
        print("❌ Error: 'Symbol' column not found. File format changed. Using fallback list.")

    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}. Using fallback list.")

    # Return the list, which is guaranteed to be the NSE list or the fallback list.
    return symbol_list

# ======================================================================
# 2. CORE DATA FETCH FUNCTION FOR A SINGLE STOCK (UNCHANGED)
# ======================================================================

# Define your main application and constants
app = Flask(__name__)

def fetch_single_stock_metrics(symbol: str) -> Dict[str, Any]:
    # ... (initial variable setup remains the same) ...
    """
    Fetches required metrics (Last Price, 52W High/Low, Events) for a single stock.
    """
    # 🛑 CRITICAL: This line defines ticker_symbol
    ticker_symbol = f"{symbol}{NSE_SUFFIX}"
    today = date.today()

    NSE_DETAIL_URL = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        last_price = info.get('previousClose', info.get('regularMarketPreviousClose'))
        if last_price is None:
            history = ticker.history(period="1d", interval="1d", timeout=5) # 5 seconds max
            last_price = history['Close'].iloc[-1] if not history.empty else None

        # --- New Variables for Calculation ---
        price = last_price
        high_52w = info.get('fiftyTwoWeekHigh')
        low_52w = info.get('fiftyTwoWeekLow')
        low_nearness_percent = None # Initialize to None

        if price and low_52w and high_52w and price >= low_52w:
            # Calculate how far the current price is from the 52W Low, as a percentage of the *range*.
            price_range = high_52w - low_52w

            if price_range > 0:
                # The nearness is calculated as: (current position in range / total range) * 100
                # A value of 0% means the price is exactly at the 52W Low.
                # A value of 100% means the price is exactly at the 52W High.
                low_nearness_percent = round(((price - low_52w) / price_range) * 100, 2)
            else:
                low_nearness_percent = 0.0 # Price = Low = High, so it is at the low.

            print(f"DEBUG: {symbol} - Low Nearness %: {low_nearness_percent}")


            # ... (Upcoming Events logic remains the same) ...
        actions = []
        # ... (Existing logic for actions) ...

        return {
            "symbol": symbol,
            "name": info.get('longName', symbol),
            "lastPrice": round(float(price), 2) if price else None,
            "high52Week": high_52w,
            "low52Week": low_52w,
            # --- NEW FIELD ---
            "lowNearnessPercentage": low_nearness_percent,
            # -----------------
            "upcomingEvents": actions,
            "detailLink": NSE_DETAIL_URL
        }

    except Exception:
        # Include the new field in the error return as well
        return {
            "symbol": symbol,
            "name": f"Error/No Data for {symbol}",
            "lastPrice": None,
            "high52Week": None,
            "low52Week": None,
            "lowNearnessPercentage": None, # Error return
            "upcomingEvents": [],
            "detailLink": NSE_DETAIL_URL
        }

# ======================================================================
# 3. API ENDPOINT DEFINITION (UPDATED FOR DYNAMIC CALL)
# ======================================================================

@app.route('/', methods=['GET'])
def render_nifty_ui():
    """Renders the main HTML template."""
    # Flask looks for templates/index.html
    return render_template('index.html')

@app.route('/api/historical/NIFTY50', methods=['GET'])
def get_nifty50_data():
    """Endpoint to fetch key metrics for all stocks in NIFTY 50 dynamically."""

    # DYNAMIC STEP: Get the list of symbols using the robust function
    symbols_to_fetch = get_nifty_50_symbols()

    if not symbols_to_fetch or symbols_to_fetch == ["RELIANCE", "HDFCBANK", "TCS", "ICICIBANK", "INFY", "KOTAKBANK", "HINDUNILVR"]:
        # If it falls back to a small list, indicate a temporary issue
        return jsonify({
            "status": "warning",
            "message": "NSE data download failed. Using a small, cached list for demonstration/fallback.",
            "data": [fetch_single_stock_metrics(symbol) for symbol in symbols_to_fetch if fetch_single_stock_metrics(symbol)['lastPrice'] is not None]
        }), 200

    results = []

    # Fetch data for all stocks in the dynamic list
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
# --- Add this new UI route to index_api.py ---

@app.route('/sensex', methods=['GET'])
def render_sensex_ui():
    """Renders the SENSEX HTML template."""
    # Flask will look for templates/sensex.html
    return render_template('sensex.html')

# --- Add this new API endpoint to index_api.py ---

@app.route('/api/historical/SENSEX', methods=['GET'])
def get_sensex_data():
    """Endpoint to fetch key metrics for all stocks in SENSEX 30."""

    # DYNAMIC STEP: Get the list of Sensex symbols
    symbols_to_fetch = get_sensex_30_symbols() # Use the new function

    results = []

    # Fetch data for all Sensex stocks
    for symbol in symbols_to_fetch:
        data = fetch_single_stock_metrics(symbol) # Use the existing fetch function
        if data['lastPrice'] is not None:
            results.append(data)

    return jsonify({
        "status": "success",
        "index": "SENSEX",
        "total_constituents": len(symbols_to_fetch),
        "total_stocks_fetched": len(results),
        "data": results
    })

if __name__ == '__main__':
    # When running the app, it is now serving the HTML too!
    print("Starting Flask Index API server on http://127.0.0.1:3000/")
    app.run(debug=True, port=3000)