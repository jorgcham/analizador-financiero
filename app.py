import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# ==============================================================================
# PAGE CONFIG
# ==============================================================================
st.set_page_config(
    page_title="Professional Fundamental Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# CUSTOM CSS
# ==============================================================================
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    padding: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# YAHOO FINANCE AUTOCOMPLETE
# ==============================================================================
@st.cache_data(ttl=3600)
def yahoo_search(query: str):
    if not query or len(query) < 2:
        return []

    url = "https://query1.finance.yahoo.com/v1/finance/search"
    params = {
        "q": query,
        "quotesCount": 10,
        "newsCount": 0,
        "enableFuzzyQuery": True
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        data = r.json()
    except Exception:
        return []

    results = []
    for item in data.get("quotes", []):
        symbol = item.get("symbol")
        name = item.get("shortname") or item.get("longname")
        exchange = item.get("exchange", "")
        if symbol and name:
            results.append(f"{symbol} | {name} ({exchange})")

    return results

# ==============================================================================
# BENCHMARK ENGINE
# ==============================================================================
class BenchmarkEngine:
    SECTOR_ETF_MAP = {
        'Technology': 'XLK',
        'Financial Services': 'XLF',
        'Healthcare': 'XLV',
        'Consumer Cyclical': 'XLY',
        'Energy': 'XLE',
        'Industrials': 'XLI',
        'Consumer Defensive': 'XLP',
        'Utilities': 'XLU',
        'Real Estate': 'XLRE',
        'Communication Services': 'XLC',
        'Basic Materials': 'XLB'
    }

    @staticmethod
    def get_benchmark(sector):
        etf_ticker = BenchmarkEngine.SECTOR_ETF_MAP.get(sector, 'SPY')
        try:
            info = yf.Ticker(etf_ticker).info
            return {
                'ticker': etf_ticker,
                'pe': info.get('trailingPE', 20) or 20,
                'pb': info.get('priceToBook', 3) or 3,
                'ps': info.get('priceToSalesTrailing12Months', 2) or 2,
                'margin': info.get('profitMargins', 0.1) or 0.1,
                'roe': info.get('returnOnEquity', 0.12) or 0.12,
                'roa': info.get('returnOnAssets', 0.05) or 0.05,
            }
        except:
            return {'pe': 20, 'pb': 3, 'ps': 2, 'margin': 0.1, 'roe': 0.12, 'roa': 0.05}

# ==============================================================================
# FUNDAMENTAL ANALYST
# ==============================================================================
class FundamentalAnalyst:
    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = {}
        self.financials = None
        self.benchmark = {}

    def load_all_data(self):
        self.info = self.stock.info
        if not self.info.get('currentPrice') and not self.info.get('regularMarketPrice'):
            raise ValueError("Invalid ticker")

        self.financials = self.stock.financials
        sector = self.info.get('sector', 'Unknown')
        self.benchmark = BenchmarkEngine.get_benchmark(sector)

    def get(self, key, default=0.0):
        val = self.info.get(key)
        return float(val) if val is not None else default

    def calculate_score(self):
        score = 0
        if self.get('trailingPE') < self.benchmark['pe']:
            score += 20
        if self.get('profitMargins') > self.benchmark['margin']:
            score += 15
        if self.get('returnOnEquity') > self.benchmark['roe']:
            score += 15
        if self.get('revenueGrowth') > 0:
            score += 10
        if self.get('freeCashflow') > 0:
            score += 10
        if self.get('currentRatio') > 1.5:
            score += 10
        return min(score, 100)

# ==============================================================================
# STREAMLIT APP
# ==============================================================================
def main():
    st.markdown('<div class="main-header">📊 Professional Fundamental Analysis Engine</div>', unsafe_allow_html=True)

    # SIDEBAR
    with st.sidebar:
        st.header("🔍 Analysis Settings")

        query = st.text_input(
            "Enter ticker or company",
            value="AAPL",
            placeholder="Apple, MSFT, NVDA..."
        )

        suggestions = yahoo_search(query)

        if suggestions:
            selected = st.selectbox("Suggestions", suggestions)
            ticker_input = selected.split("|")[0].strip()
        else:
            ticker_input = query.upper().strip()

        analyze_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
        st.caption("Autocomplete powered by Yahoo Finance")

    # MAIN LOGIC
    if analyze_button and ticker_input:
        with st.spinner(f"Loading data for {ticker_input}..."):
            try:
                analyst = FundamentalAnalyst(ticker_input)
                analyst.load_all_data()

                st.header("Company Overview")
                col1, col2, col3 = st.columns(3)
                col1.metric("Ticker", analyst.ticker)
                col2.metric("Company", analyst.info.get("longName", "N/A"))
                col3.metric("Sector", analyst.info.get("sector", "N/A"))

                st.header("Valuation")
                pe = analyst.get("trailingPE")
                st.metric("P/E", f"{pe:.2f}" if pe > 0 else "N/A")

                st.header("Profitability")
                margin = analyst.get("profitMargins") * 100
                roe = analyst.get("returnOnEquity") * 100
                col1, col2 = st.columns(2)
                col1.metric("Net Margin", f"{margin:.2f}%")
                col2.metric("ROE", f"{roe:.2f}%")

                st.header("Investment Score")
                score = analyst.calculate_score()
                st.progress(score / 100)
                st.metric("Fundamental Score", score)

            except Exception as e:
                st.error(f"Error analyzing ticker: {e}")

    else:
        st.info("👈 Start typing a company or ticker to begin")

if __name__ == "__main__":
    main()
