import pandas as pd
import requests
from io import StringIO
from typing import List, Optional
import streamlit as st # Import Streamlit

# --- Configuration to suppress the urllib3 warning (Optional but cleaner) ---
import warnings
warnings.filterwarnings("ignore", module="urllib3")
# --------------------------------------------------------------------------

@st.cache_data(ttl=3600) # Cache the result for 1 hour to prevent excessive requests
def get_nifty_50_constituents() -> Optional[pd.DataFrame]:
    """
    Downloads the current Nifty 50 constituents list from the NSE archives
    and returns a pandas DataFrame. Returns None if the download fails.
    """
    NIFTY_50_URL = 'https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br'
    }

    st.info("Attempting to fetch Nifty 50 constituents data from NSE...")
    try:
        with requests.Session() as session:
            session.headers.update(HEADERS)
            session.get("https://www.nseindia.com", timeout=10) # Warm-up
            response = session.get(NIFTY_50_URL, timeout=10)

        response.raise_for_status()

        # Read the raw content and create a file-like buffer for pandas
        csv_content = StringIO(response.content.decode('utf-8'))

        # Read the CSV into a DataFrame
        df = pd.read_csv(csv_content)

        st.success(f"✅ Success! Retrieved {len(df)} Nifty 50 companies.")
        return df

    except requests.exceptions.RequestException as e:
        st.error(f"❌ ERROR: A network or HTTP error occurred during download: {e}")
        return None
    except KeyError:
        st.error("❌ ERROR: Required column not found in the downloaded CSV.")
        return None
    except Exception as e:
        st.error(f"❌ AN UNEXPECTED ERROR OCCURRED: {e}")
        return None

# ======================================================================
#             STREAMLIT FRONTEND UI DEFINITION
# ======================================================================

def main():
    """Defines the Streamlit app layout."""
    st.set_page_config(
        page_title="Nifty 50 Dashboard",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 1. Title and Header
    st.title("🇮🇳 Nifty 50 Constituents Dashboard")
    st.subheader("Live-fetched list of India's top 50 companies on the NSE.")

    # 2. Get the data
    nifty_df = get_nifty_50_constituents()

    # 3. Display the data if successful
    if nifty_df is not None:

        st.markdown("---")

        # Display key metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Stocks", len(nifty_df))

        # Calculate the number of unique industries
        unique_industries = nifty_df['Industry'].nunique()
        col2.metric("Unique Industries", unique_industries)

        # Find the most common industry
        most_common_industry = nifty_df['Industry'].mode()[0]
        col3.metric("Largest Sector", most_common_industry)

        st.markdown("---")

        # Display the data in a beautiful, interactive table
        st.header("Interactive List of Constituents")
        st.dataframe(
            nifty_df,
            use_container_width=True,
            hide_index=True
        )

        # Allow user to download the data
        csv = nifty_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name='nifty_50_constituents.csv',
            mime='text/csv',
        )

# Run the main Streamlit function
if __name__ == "__main__":
    main()