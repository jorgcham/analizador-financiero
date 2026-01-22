import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# ==============================================================================
# CONFIG
# ==============================================================================
st.set_page_config(
    page_title="Professional Fundamental Analysis (FMP)",
    page_icon="📊",
    layout="wide"
)

API_KEY = st.secrets["FMP_API_KEY"]
BASE_URL = "https://financialmodelingprep.com/stable"

# ==============================================================================
# FMP DATA LAYER (CACHEADO)
# ==============================================================================

@st.cache_data(ttl=3600)
def fmp_get(endpoint: str, params: dict):
    params["apikey"] = API_KEY
    url = f"{BASE_URL}/{endpoint}"
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600)
def get_company_profile(symbol):
    data = fmp_get("profile", {"symbol": symbol})
    return data[0] if data else {}

@st.cache_data(ttl=3600)
def get_quote(symbol):
    data = fmp_get("quote", {"symbol": symbol})
    return data[0] if data else {}

@st.cache_data(ttl=3600)
def get_income_statement(symbol):
    return fmp_get("income-statement", {"symbol": symbol, "limit": 5})

@st.cache_data(ttl=3600)
def get_balance_sheet(symbol):
    return fmp_get("balance-sheet-statement", {"symbol": symbol, "limit": 5})

@st.cache_data(ttl=3600)
def get_cashflow(symbol):
    return fmp_get("cash-flow-statement", {"symbol": symbol, "limit": 5})

@st.cache_data(ttl=3600)
def get_historical_prices(symbol):
    return fmp_get("historical-price-eod/full", {"symbol": symbol})["historical"]

# ==============================================================================
# BENCHMARK ENGINE (ETFs REALES)
# ==============================================================================
class BenchmarkEngine:

    SECTOR_ETF_MAP = {
        "Technology": "XLK",
        "Financial Services": "XLF",
        "Healthcare": "XLV",
        "Consumer Cyclical": "XLY",
        "Energy": "XLE",
        "Industrials": "XLI",
        "Consumer Defensive": "XLP",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Communication Services": "XLC",
        "Basic Materials": "XLB"
    }

    @staticmethod
    def get_benchmark(sector):
        etf = BenchmarkEngine.SECTOR_ETF_MAP.get(sector, "SPY")
        profile = get_company_profile(etf)
        return {
            "ticker": etf,
            "pe": profile.get("pe", 20),
            "pb": profile.get("priceToBookRatio", 3),
            "ps": profile.get("priceToSalesRatio", 2),
            "roe": profile.get("returnOnEquityTTM", 0.12),
            "margin": profile.get("netProfitMarginTTM", 0.1),
        }

# ==============================================================================
# FUNDAMENTAL ANALYST
# ==============================================================================
class FundamentalAnalyst:

    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.profile = {}
        self.quote = {}
        self.income = []
        self.balance = []
        self.cashflow = []
        self.history = []
        self.benchmark = {}

    def load(self):
        self.profile = get_company_profile(self.ticker)
        self.quote = get_quote(self.ticker)

        if not self.profile:
            raise ValueError("Ticker inválido o sin datos")

        self.income = get_income_statement(self.ticker)
        self.balance = get_balance_sheet(self.ticker)
        self.cashflow = get_cashflow(self.ticker)
        self.history = get_historical_prices(self.ticker)

        sector = self.profile.get("sector", "Unknown")
        self.benchmark = BenchmarkEngine.get_benchmark(sector)

    def calculate_score(self):
        score = 0

        pe = self.profile.get("pe", 0)
        bench_pe = self.benchmark["pe"]

        if pe and bench_pe:
            if pe < bench_pe * 0.8:
                score += 20
            elif pe < bench_pe * 1.2:
                score += 10

        if self.profile.get("returnOnEquityTTM", 0) > self.benchmark["roe"]:
            score += 15

        if self.profile.get("netProfitMarginTTM", 0) > self.benchmark["margin"]:
            score += 15

        if self.profile.get("debtToEquity", 2) < 1:
            score += 10

        if self.profile.get("priceEarningsGrowthRatio", 2) < 1.5:
            score += 10

        if self.quote.get("eps", 0) > 0:
            score += 10

        return min(score, 100)

# ==============================================================================
# STREAMLIT UI
# ==============================================================================
def main():

    st.markdown("## 📊 Professional Fundamental Analysis Engine")
    st.caption("Powered by Financial Modeling Prep (Official API)")

    with st.sidebar:
        with st.form("form"):
            ticker = st.text_input("Ticker", value="AAPL")
            run = st.form_submit_button("🚀 Run Analysis")

    if not run:
        st.info("Introduce un ticker y ejecuta el análisis")
        return

    with st.spinner("Cargando datos..."):
        try:
            analyst = FundamentalAnalyst(ticker)
            analyst.load()

            st.metric("Empresa", analyst.profile.get("companyName"))
            st.metric("Precio", f"${analyst.quote.get('price')}")
            st.metric("Sector", analyst.profile.get("sector"))

            st.markdown("### 📐 Valuación vs Sector")
            st.metric(
                "P/E",
                f"{analyst.profile.get('pe')}",
                f"{((analyst.profile.get('pe') - analyst.benchmark['pe']) / analyst.benchmark['pe'] * 100):+.1f}%"
            )

            score = analyst.calculate_score()

            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                title={"text": "Fundamental Score"},
                gauge={"axis": {"range": [0, 100]}}
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

if __name__ == "__main__":
    main()
