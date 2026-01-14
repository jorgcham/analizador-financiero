import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date

# =========================
# CONFIGURATION
# =========================
st.set_page_config(page_title="Portfolio Simulator", layout="wide")
st.title("📊 Portfolio Simulator (Kwanti-style)")
st.markdown("Educational portfolio backtesting tool")
st.markdown("---")

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Parameters")

tickers_input = st.sidebar.text_input(
    "Symbols (e.g. AAPL,MSFT,GOOGL)",
    value="AAPL,MSFT,GOOGL"
)

weights_input = st.sidebar.text_input(
    "Weights (e.g. 0.4,0.3,0.3)",
    value="0.34,0.33,0.33"
)

start_date = st.sidebar.date_input("From", date(2020, 1, 1))
end_date = st.sidebar.date_input("To", date.today())

initial_capital = st.sidebar.number_input(
    "Initial Capital (USD)", value=10000.0, step=500.0
)

benchmark_ticker = "SPY"

run = st.sidebar.button("Simulate")

# =========================
# FUNCTIONS
# =========================
def download_prices(tickers, start, end):
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )

    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]]
        prices.columns = tickers

    return prices.dropna()


def normalize_weights(w):
    w = np.array(w, dtype=float)
    return w / w.sum()


def portfolio_simulation(prices, weights, capital):
    returns = prices.pct_change().dropna()
    port_returns = returns.dot(weights)
    port_value = (1 + port_returns).cumprod() * capital
    return port_value, port_returns


def max_drawdown(series):
    cumulative = (1 + series).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    return drawdown.min() * 100


def sharpe_ratio(returns, risk_free=0.0):
    excess = returns - risk_free / 252
    return np.sqrt(252) * excess.mean() / excess.std()

# =========================
# MAIN
# =========================
if run:
    try:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        weights = [float(w.strip()) for w in weights_input.split(",") if w.strip()]

        if len(tickers) == 0:
            st.error("Please add at least one symbol")
            st.stop()

        if len(tickers) != len(weights):
            st.error("The number of weights and symbols must match")
            st.stop()

        weights = normalize_weights(weights)

        # Download prices
        asset_prices = download_prices(tickers, start_date, end_date)
        benchmark_prices = download_prices([benchmark_ticker], start_date, end_date)

        if asset_prices.empty or benchmark_prices.empty:
            st.error("Market data could not be downloaded")
            st.stop()

        # Align dates
        prices = asset_prices.join(benchmark_prices, how="inner")

        asset_prices = prices[tickers]
        benchmark_prices = prices[benchmark_ticker]

        # Simulations
        portfolio_value, portfolio_returns = portfolio_simulation(
            asset_prices, weights, initial_capital
        )

        benchmark_returns = benchmark_prices.pct_change().dropna()
        benchmark_value = (1 + benchmark_returns).cumprod() * initial_capital

        # =========================
        # METRICS
        # =========================
        total_return = (portfolio_value.iloc[-1] / initial_capital - 1) * 100
        annual_return = (
            (portfolio_value.iloc[-1] / initial_capital)
            ** (252 / len(portfolio_value)) - 1
        ) * 100

        volatility = portfolio_returns.std() * np.sqrt(252) * 100
        sharpe = sharpe_ratio(portfolio_returns)
        mdd = max_drawdown(portfolio_returns)

        b_total_return = (benchmark_value.iloc[-1] / initial_capital - 1) * 100
        b_annual_return = (
            (benchmark_value.iloc[-1] / initial_capital)
            ** (252 / len(benchmark_value)) - 1
        ) * 100

        # =========================
        # DISPLAY METRICS
        # =========================
        st.subheader("📌 Portfolio vs Benchmark (SPY)")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Final Value (USD)", f"${portfolio_value.iloc[-1]:,.2f}")
        c2.metric("Total Return (%)", f"{total_return:.2f}%")
        c3.metric("Annual Return (%)", f"{annual_return:.2f}%")
        c4.metric("Volatility (%)", f"{volatility:.2f}%")
        c5.metric("Sharpe Ratio", f"{sharpe:.2f}")

        c6, c7, _, _, _ = st.columns(5)
        c6.metric("Max Drawdown (%)", f"{mdd:.2f}%")
        c7.metric("SPY Annual Return (%)", f"{b_annual_return:.2f}%")

        # =========================
        # CHARTS
        # =========================
        st.subheader("📈 Growth of $1 (Portfolio vs SPY)")
        comparison = pd.DataFrame({
            "Portfolio": portfolio_value / initial_capital,
            "SPY": benchmark_value / initial_capital
        })
        st.line_chart(comparison)

        st.subheader("📊 Asset Prices (Adjusted)")
        st.line_chart(asset_prices)

        # =========================
        # TABLE
        # =========================
        st.subheader("📋 Portfolio Composition")
        table = pd.DataFrame({
            "Ticker": tickers,
            "Weight": weights,
            "Allocated Capital (USD)": weights * initial_capital
        })
        st.dataframe(table, use_container_width=True)

    except Exception as e:
        st.error(f"Simulation error: {e}")

st.markdown("---")
st.caption("Educational simulator · Not financial advice")
