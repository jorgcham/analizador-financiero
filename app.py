import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import time

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
# GLOBAL CACHE FUNCTIONS (🔥 CRÍTICO)
# ==============================================================================

@st.cache_data(ttl=3600)
def get_ticker_data(ticker: str):
    stock = yf.Ticker(ticker)
    return {
        "info": stock.info,
        "financials": stock.financials,
        "balance": stock.balance_sheet,
        "cashflow": stock.cashflow,
        "history": stock.history(period="5y")
    }

@st.cache_data(ttl=3600)
def get_benchmark_data(etf_ticker: str):
    etf = yf.Ticker(etf_ticker)
    info = etf.info
    return {
        'ticker': etf_ticker,
        'pe': info.get('trailingPE', 20.0),
        'pb': info.get('priceToBook', 3.0),
        'ps': info.get('priceToSalesTrailing12Months', 2.0),
        'margin': info.get('profitMargins', 0.10),
        'roe': info.get('returnOnEquity', 0.12),
        'roa': info.get('returnOnAssets', 0.05),
    }

# ==============================================================================
# BENCHMARK ENGINE (Yahoo Finance REAL DATA)
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
    def get_benchmark(sector: str):
        etf = BenchmarkEngine.SECTOR_ETF_MAP.get(sector, 'SPY')
        try:
            return get_benchmark_data(etf)
        except:
            return {
                'ticker': 'SPY',
                'pe': 20.0,
                'pb': 3.0,
                'ps': 2.0,
                'margin': 0.10,
                'roe': 0.12,
                'roa': 0.05,
            }

# ==============================================================================
# FUNDAMENTAL ANALYST
# ==============================================================================
class FundamentalAnalyst:

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.info = {}
        self.financials = None
        self.balance = None
        self.cashflow = None
        self.history = None
        self.benchmark = {}

    def load_all_data(self):
        data = get_ticker_data(self.ticker)
        self.info = data["info"]

        if not self.info or not (
            self.info.get("currentPrice") or self.info.get("regularMarketPrice")
        ):
            raise ValueError("Ticker inválido o sin datos disponibles")

        self.financials = data["financials"]
        self.balance = data["balance"]
        self.cashflow = data["cashflow"]
        self.history = data["history"]

        sector = self.info.get("sector", "Unknown")
        self.benchmark = BenchmarkEngine.get_benchmark(sector)

    def get(self, key, default=0.0):
        val = self.info.get(key)
        try:
            return float(val)
        except:
            return default

    def calculate_score(self):
        score = 0

        pe = self.get('trailingPE')
        if pe > 0 and self.benchmark['pe'] > 0:
            if pe < self.benchmark['pe'] * 0.8:
                score += 20
            elif pe < self.benchmark['pe'] * 1.2:
                score += 10

        if self.get('profitMargins') > self.benchmark['margin']:
            score += 10

        if self.get('returnOnEquity') > self.benchmark['roe']:
            score += 10

        if self.get('revenueGrowth') > 0.05:
            score += 10

        if self.get('earningsGrowth') > 0.05:
            score += 10

        if self.get('currentRatio') > 1.5:
            score += 10

        de = self.get('debtToEquity')
        de = de / 100 if de > 10 else de
        if de < 1:
            score += 10

        if self.get('trailingEps') > 0:
            score += 5

        if self.get('freeCashflow') > 0:
            score += 5

        return min(score, 100)

# ==============================================================================
# STREAMLIT APP
# ==============================================================================
def main():

    st.markdown("## 📊 Professional Fundamental Analysis Engine")
    st.caption("Real Yahoo Finance Data · Cached · Production-Ready")

    with st.sidebar:
        st.header("🔍 Analysis Settings")

        with st.form("analysis_form"):
            ticker_input = st.text_input("Ticker", value="AAPL")
            analyze_button = st.form_submit_button("🚀 Run Analysis")

        st.info("Benchmarks y datos extraídos **directamente de Yahoo Finance**")

    if not analyze_button:
        st.info("👈 Ingresa un ticker y ejecuta el análisis")
        return

    with st.spinner(f"Cargando datos de {ticker_input.upper()}..."):
        try:
            analyst = FundamentalAnalyst(ticker_input)
            analyst.load_all_data()

            price = analyst.get("currentPrice") or analyst.get("regularMarketPrice")

            col1, col2, col3 = st.columns(3)
            col1.metric("Ticker", analyst.ticker)
            col2.metric("Sector", analyst.info.get("sector", "N/A"))
            col3.metric("Precio", f"${price:.2f}")

            st.markdown("### 📐 Valuation vs Sector")
            pe = analyst.get("trailingPE")
            bench_pe = analyst.benchmark["pe"]

            st.metric(
                "P/E Ratio",
                f"{pe:.2f}",
                f"{((pe - bench_pe) / bench_pe * 100):+.1f}% vs sector"
            )

            st.markdown("### 🧠 Fundamental Score")
            score = analyst.calculate_score()

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                title={'text': "Fundamental Score"},
                gauge={'axis': {'range': [0, 100]}}
            ))
            st.plotly_chart(fig, use_container_width=True)

            if score >= 80:
                st.success("STRONG BUY")
            elif score >= 60:
                st.success("BUY")
            elif score >= 40:
                st.warning("HOLD")
            else:
                st.error("SELL")

        except Exception as e:
            st.error(str(e))
            st.warning("Posible rate limit temporal. Espera unos minutos.")

if __name__ == "__main__":
    main()
