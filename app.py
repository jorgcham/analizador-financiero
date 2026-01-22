import streamlit as st
import pandas as pd
import numpy as np
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.timeseries import TimeSeries
import plotly.graph_objects as go
import time

# ==============================================================================
# CONFIGURACION
# ==============================================================================
ALPHA_VANTAGE_API_KEY = "0WY8DEB53DIR61X8"

st.set_page_config(
    page_title="Professional Fundamental Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main-header {font-size:2.5rem;font-weight:bold;text-align:center;color:#1f77b4;}
.metric-card {background-color:#f0f2f6;padding:1rem;border-radius:0.5rem;border-left:4px solid #1f77b4;}
.positive {color:#28a745;font-weight:bold;}
.negative {color:#dc3545;font-weight:bold;}
.neutral {color:#ffc107;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# MAPEOS Yahoo → Alpha Vantage
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
    DEFAULT = {"pe": 20, "margin": 0.10, "roe": 0.12}
    @staticmethod
    def get_benchmark(sector):
        return BenchmarkEngine.DEFAULT

# ==============================================================================
# WRAPPER DE LLAMADAS CON REINTENTOS
# ==============================================================================
def alpha_call_with_retry(func, *args, retries=5, delay=15, **kwargs):
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            if "Information" in str(e) or "call frequency" in str(e):
                time.sleep(delay)
            else:
                raise
    raise ValueError("Max retries reached for Alpha Vantage API")

# ==============================================================================
# FUNDAMENTAL ANALYST
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
        # ==========================
        # Company Overview
        # ==========================
        overview, _ = alpha_call_with_retry(self.fd.get_company_overview, self.ticker)
        if overview.empty:
            raise ValueError("Ticker no encontrado")
        self.info = overview.iloc[0].to_dict()

        # ==========================
        # Financial Statements
        # ==========================
        income, _ = alpha_call_with_retry(self.fd.get_income_statement_annual, self.ticker)
        balance, _ = alpha_call_with_retry(self.fd.get_balance_sheet_annual, self.ticker)
        cashflow, _ = alpha_call_with_retry(self.fd.get_cash_flow_annual, self.ticker)
        self.financials = income.set_index("fiscalDateEnding").T
        self.balance = balance.set_index("fiscalDateEnding").T
        self.cashflow = cashflow.set_index("fiscalDateEnding").T

        # ==========================
        # Price History (compact para no superar limite)
        # ==========================
        prices, _ = alpha_call_with_retry(self.ts.get_daily_adjusted, self.ticker, outputsize="compact")
        prices.index = pd.to_datetime(prices.index)
        self.history = prices.sort_index()

        # ==========================
        # Benchmark
        # ==========================
        sector = self.info.get("Sector", "Unknown")
        self.benchmark = BenchmarkEngine.get_benchmark(sector)

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
        if 0 < pe < self.benchmark["pe"]: score += 20
        if self.get("profitMargins") > self.benchmark["margin"]: score += 15
        if self.get("returnOnEquity") > self.benchmark["roe"]: score += 15
        if self.get("revenueGrowth") > 0.05: score += 10
        if self.get("earningsGrowth") > 0.05: score += 10
        if self.get("currentRatio") > 1.5: score += 10
        if self.get("debtToEquity") < 1: score += 10
        if self.get("freeCashflow") > 0: score += 10
        return min(score, 100)

# ==============================================================================
# STREAMLIT APP
# ==============================================================================
@st.cache_data(ttl=3600)
def load_analyst(ticker):
    analyst = FundamentalAnalyst(ticker)
    analyst.load_all_data()
    return analyst

def main():
    st.markdown('<div class="main-header">📊 Professional Fundamental Analysis Engine</div>', unsafe_allow_html=True)

    with st.sidebar:
        ticker_input = st.text_input("Enter Ticker Symbol", "AAPL")
        analyze_button = st.button("🚀 Run Analysis")

    if analyze_button and ticker_input:
        with st.spinner(f"Cargando datos de {ticker_input}..."):
            try:
                analyst = load_analyst(ticker_input)

                # ==========================
                # Overview
                # ==========================
                st.header("1️⃣ Company Overview")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Ticker", analyst.ticker)
                    st.metric("Sector", analyst.info.get("Sector", "N/A"))
                with col2:
                    st.metric("Market Cap", f"${analyst.get('marketCap')/1e9:.2f}B")
                    st.metric("Beta", analyst.get("beta"))
                with col3:
                    st.metric("P/E", analyst.get("trailingPE"))
                    st.metric("ROE", f"{analyst.get('returnOnEquity')*100:.2f}%")

                # ==========================
                # Price History
                # ==========================
                st.header("Price History")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=analyst.history.index,
                    y=analyst.history["5. adjusted close"],
                    mode="lines",
                    name="Price"
                ))
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

                # ==========================
                # Investment Score
                # ==========================
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

                st.caption("⚠️ Esta información es solo educativa. No constituye asesoramiento financiero.")

            except Exception as e:
                st.error(f"Error analizando {ticker_input}: {str(e)}")
    else:
        st.info("👈 Introduce un ticker y pulsa 'Run Analysis'")

if __name__ == "__main__":
    main()
