
import streamlit as st
import pandas as pd
import numpy as np
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.timeseries import TimeSeries
import plotly.graph_objects as go
from datetime import datetime
import time

# ==============================================================================
# CONFIG
# ==============================================================================
ALPHA_VANTAGE_API_KEY = "0WY8DEB53DIR61X8"

st.set_page_config(
    page_title="Professional Fundamental Analysis",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.main-header {font-size:2.5rem;font-weight:bold;text-align:center;color:#1f77b4}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FIELD MAP (Yahoo → Alpha Vantage)
# ==============================================================================
FIELD_MAP = {
    "marketCap": "MarketCapitalization",
    "trailingPE": "PERatio",
    "profitMargins": "ProfitMargin",
    "returnOnEquity": "ReturnOnEquityTTM",
    "revenueGrowth": "QuarterlyRevenueGrowthYOY",
    "earningsGrowth": "QuarterlyEarningsGrowthYOY",
    "beta": "Beta",
    "dividendYield": "DividendYield",
    "currentRatio": "CurrentRatio",
    "debtToEquity": "DebtToEquity",
    "freeCashflow": "FreeCashFlowTTM",
}

# ==============================================================================
# BENCHMARK ENGINE
# ==============================================================================
class BenchmarkEngine:
    DEFAULT = {
        "pe": 20,
        "margin": 0.10,
        "roe": 0.12
    }

    @staticmethod
    def get_benchmark(sector):
        return BenchmarkEngine.DEFAULT

# ==============================================================================
# FUNDAMENTAL ANALYST (ALPHA VANTAGE)
# ==============================================================================
class FundamentalAnalyst:
    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.fd = FundamentalData(ALPHA_VANTAGE_API_KEY, output_format="pandas")
        self.ts = TimeSeries(ALPHA_VANTAGE_API_KEY, output_format="pandas")
        self.info = {}
        self.financials = None
        self.balance = None
        self.cashflow = None
        self.history = None
        self.benchmark = {}

    def load_all_data(self):
        overview, _ = self.fd.get_company_overview(self.ticker)
        if overview.empty:
            raise ValueError("Ticker no encontrado")

        self.info = overview.iloc[0].to_dict()

        time.sleep(12)
        income, _ = self.fd.get_income_statement_annual(self.ticker)
        time.sleep(12)
        balance, _ = self.fd.get_balance_sheet_annual(self.ticker)
        time.sleep(12)
        cashflow, _ = self.fd.get_cash_flow_annual(self.ticker)

        self.financials = income.set_index("fiscalDateEnding").T
        self.balance = balance.set_index("fiscalDateEnding").T
        self.cashflow = cashflow.set_index("fiscalDateEnding").T

        time.sleep(12)
        prices, _ = self.ts.get_daily_adjusted(self.ticker, outputsize="full")
        prices.index = pd.to_datetime(prices.index)
        self.history = prices.sort_index().last("5Y")

        self.benchmark = BenchmarkEngine.get_benchmark(self.info.get("Sector"))

    def get(self, key, default=0.0):
        av_key = FIELD_MAP.get(key, key)
        val = self.info.get(av_key)
        try:
            return float(val)
        except:
            return default

    def calculate_score(self):
        score = 0

        pe = self.get("trailingPE")
        if 0 < pe < self.benchmark["pe"]:
            score += 20

        if self.get("profitMargins") > self.benchmark["margin"]:
            score += 15

        if self.get("returnOnEquity") > self.benchmark["roe"]:
            score += 15

        if self.get("revenueGrowth") > 0.05:
            score += 10

        if self.get("earningsGrowth") > 0.05:
            score += 10

        if self.get("currentRatio") > 1.5:
            score += 10

        if self.get("debtToEquity") < 1:
            score += 10

        if self.get("freeCashflow") > 0:
            score += 10

        return min(score, 100)

# ==============================================================================
# STREAMLIT APP
# ==============================================================================
def main():
    st.markdown('<div class="main-header">📊 Professional Fundamental Analysis</div>', unsafe_allow_html=True)

    with st.sidebar:
        ticker = st.text_input("Ticker", "AAPL")
        run = st.button("🚀 Run Analysis")

    if not run:
        st.info("👈 Introduce un ticker y pulsa Run Analysis")
        return

    with st.spinner("Cargando datos (Alpha Vantage)..."):
        analyst = FundamentalAnalyst(ticker)
        analyst.load_all_data()

    # ==============================================================================
    # OVERVIEW
    # ==============================================================================
    st.header("Company Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Ticker", ticker)
        st.metric("Sector", analyst.info.get("Sector", "N/A"))

    with col2:
        st.metric("Market Cap", f"${analyst.get('marketCap')/1e9:.2f}B")
        st.metric("Beta", analyst.get("beta"))

    with col3:
        st.metric("P/E", analyst.get("trailingPE"))
        st.metric("ROE", f"{analyst.get('returnOnEquity')*100:.2f}%")

    # ==============================================================================
    # PRICE CHART
    # ==============================================================================
    st.header("Price History (5Y)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=analyst.history.index,
        y=analyst.history["5. adjusted close"],
        mode="lines",
        name="Price"
    ))
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

    # ==============================================================================
    # SCORE
    # ==============================================================================
    score = analyst.calculate_score()

    st.header("Investment Score")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        gauge={"axis": {"range": [0, 100]}}
    ))
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    if score >= 70:
        st.success("STRONG BUY")
    elif score >= 50:
        st.warning("HOLD")
    else:
        st.error("SELL")

    st.caption("⚠️ Solo con fines educativos. No es asesoramiento financiero.")

if __name__ == "__main__":
    main()
