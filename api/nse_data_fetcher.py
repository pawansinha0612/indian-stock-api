import pandas as pd
import requests
from io import StringIO
from typing import List, Optional

def get_nifty_50_symbols() -> Optional[List[str]]:
    """
    Downloads the current Nifty 50 constituents list from the NSE website
    and returns a list of stock symbols.

    Returns:
        Optional[List[str]]: A list of Nifty 50 ticker symbols, or None if the download fails.
    """
    # 1. URL for the Nifty 50 constituents list
    NIFTY_50_URL = 'https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv'

    # 2. Define headers to mimic a web browser (required by NSE)
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br'
    }

    print("Attempting to fetch Nifty 50 symbols from NSE...")
    try:
        # Use a session for more robust connection handling
        with requests.Session() as session:
            session.headers.update(HEADERS)

            # Warm-up request to establish necessary cookies/session
            session.get("https://www.nseindia.com", timeout=10)

            # Fetch the CSV data
            response = session.get(NIFTY_50_URL, timeout=10)

        # Check for HTTP errors (404, 500, etc.)
        response.raise_for_status()

        # Read the raw content and create a file-like buffer for pandas
        csv_content = StringIO(response.content.decode('utf-8'))

        # Read the CSV into a DataFrame
        df = pd.read_csv(csv_content)

        # Extract the 'Symbol' column and convert it to a standard Python list
        symbol_list = df['Symbol'].tolist()

        print(f"✅ Successfully retrieved {len(symbol_list)} Nifty 50 symbols.")
        return symbol_list

    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading data: A network or HTTP error occurred: {e}")
        return None
    except KeyError:
        print("❌ Error: The 'Symbol' column was not found in the downloaded CSV. The file format may have changed.")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return None

# ----------------------------------------------------------------------
# Example of how to use this function in your MAIN PROJECT CODE
# ----------------------------------------------------------------------

# 1. Call the function to get the symbols
nifty_symbols_list = get_nifty_50_symbols()

# 2. Use the symbols in your main project logic
if nifty_symbols_list:
    print("\nStarting main project analysis with the symbol list...")
    # Example: Print the first 5 symbols
    print(f"First 5 symbols: {nifty_symbols_list[:5]}")

    # YOUR PROJECT LOGIC GOES HERE:
    # for symbol in nifty_symbols_list:
    #     fetch_historical_data(symbol)
    #     run_screener(symbol)
    #     ...
else:
    print("\n🛑 Cannot proceed with analysis because the Nifty 50 symbol list could not be retrieved.")