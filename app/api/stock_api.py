import pandas as pd
import requests
from io import StringIO
from typing import Optional, Dict, Any
from flask import Flask, jsonify, request
from nsetools import Nse # Keeping this only for is_valid_code, but quote fetching is removed

app = Flask(__name__)

# Initialize NSE toolkit outside the route for efficiency
# NOTE: We only use this for validation, not for quote fetching, as it's unreliable.
nse_tool = Nse()

# Base URLs for NSE data
NSE_BASE_URL = "https://www.nseindia.com/"
QUOTE_API_URL = "https://www.nseindia.com/api/quote-equity?symbol="

# Standard headers required by NSE to prevent blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br'
}

# Global session to handle required cookies
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ======================================================================
# 1. NIFTY 50 SYMBOL FETCH (Remains the same - uses a reliable CSV source)
# ======================================================================

def get_nifty_50_symbols() -> Optional[list]:
    """Downloads the current Nifty 50 symbols for validation."""
    NIFTY_50_URL = 'https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv'

    try:
        # Get a session cookie by visiting the main page first (crucial for NSE API)
        SESSION.get(NSE_BASE_URL, timeout=10)

        response = SESSION.get(NIFTY_50_URL, timeout=10)
        response.raise_for_status()
        csv_content = StringIO(response.content.decode('utf-8'))
        df = pd.read_csv(csv_content)
        return df['Symbol'].tolist()

    except Exception:
        # Fallback list if fetching fails
        return ['RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'INFY', 'SBIN']

    # Pre-fetch the list on app startup
NIFTY_SYMBOLS = get_nifty_50_symbols()
# ... (all imports and definitions remain the same) ...

# ======================================================================
# 2. NEW, RELIABLE DATA FETCH FUNCTION
# ======================================================================

def fetch_live_quote_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetches stock data using the stable NSE JSON API endpoint."""

    try:
        # The symbol needs to be URL-encoded, though simple tickers are fine
        url = f"{QUOTE_API_URL}{symbol}"

        # Ensure the session has the necessary cookies
        SESSION.get(NSE_BASE_URL, timeout=10)

        response = SESSION.get(url, timeout=10)
        response.raise_for_status()

        # === THE FIX IS HERE ===
        # Try to parse JSON. If it fails (market is closed), catch the error.
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            # This handles the "Expecting value" error when market is closed
            # The response is not JSON, so we treat it as no data available.
            print(f"INFO: JSON Decode failed for {symbol}. Market likely closed.")
            return None

            # Check for success indicators in the response structure
        if not data or 'info' not in data or data['info'].get('symbol') is None:
            return None

        # The key data is often under 'priceInfo' and 'securityInfo'
        quote = {
            "symbol": data['info']['symbol'],
            "companyName": data['info']['companyName'],
            "lastPrice": data['priceInfo']['lastPrice'],
            "change": data['priceInfo']['change'],
            "pChange": data['priceInfo']['pChange'],
            "high52Week": data['securityWisePCR']['high52Week'],
            "low52Week": data['securityWisePCR']['low52Week'],
            "marketCapital": data['securityInfo']['issuedCap'] * data['priceInfo']['lastPrice'], # Simple approx
            "industry": data['metadata']['industry']
        }
        return quote

    except Exception as e:
        print(f"Direct API fetch failed for {symbol}: {e}")
        return None

# ... (rest of the script remains the same) ...


# ======================================================================
# 3. API ENDPOINT DEFINITION
# ======================================================================

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_data(symbol: str) -> Dict[str, Any]:
    """
    Dynamic endpoint to fetch live stock data for a given symbol.
    Example: /api/stock/SBIN
    """
    ticker = symbol.upper()

    # Basic check against the Nifty 50 list (for better error messages)
    if ticker not in NIFTY_SYMBOLS and not nse_tool.is_valid_code(ticker):
        return jsonify({
            "status": "error",
            "message": f"Symbol '{ticker}' is not a recognized Nifty 50 or general NSE ticker. Try one of: {NIFTY_SYMBOLS[:5]}"
        }), 404

    # *** REPLACED nse_tool.get_quote() WITH DIRECT API FETCH ***
    data = fetch_live_quote_data(ticker)

    if not data:
        # This message is now more accurate, as it indicates a data fetching failure,
        # which will happen if the market is closed or the symbol is wrong.
        return jsonify({
            "status": "error",
            "message": f"Could not retrieve live quote for symbol: {ticker}. Data may be unavailable (e.g., market closed or bad ticker)."
        }), 404

    return jsonify({
        "status": "success",
        "data": data
    })

# ======================================================================
# 4. MAIN RUN BLOCK
# ======================================================================

if __name__ == '__main__':
    print(f"Pre-fetched Nifty Symbols: {NIFTY_SYMBOLS[:5]}...")
    print("Starting Flask API server on http://127.0.0.1:3000/")
    app.run(debug=True, port=3000)