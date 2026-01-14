import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date

# =========================
# CONFIGURATION
# =========================
st.set_page_config(page_title="Portfolio Simulator", layout="wide")
st.title("Portfolio Simulator")
st.markdown("_______________________________________________________________")
st.markdown("---")

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Parameters")

# Inicializar session state para los activos
if 'assets' not in st.session_state:
    st.session_state.assets = [
        {'ticker': 'AAPL', 'weight': 34},
        {'ticker': 'MSFT', 'weight': 33},
        {'ticker': 'GOOGL', 'weight': 33}
    ]

st.sidebar.subheader("📊 Portfolio Assets")

# Función para agregar nuevo activo
def add_asset():
    st.session_state.assets.append({'ticker': '', 'weight': 0})

# Función para eliminar activo
def remove_asset(index):
    if len(st.session_state.assets) > 1:
        st.session_state.assets.pop(index)

# Mostrar cada activo con sus controles
for i, asset in enumerate(st.session_state.assets):
    col1, col2, col3 = st.sidebar.columns([3, 2, 1])
    
    with col1:
        asset['ticker'] = st.text_input(
            f"Symbol {i+1}",
            value=asset['ticker'],
            key=f"ticker_{i}",
            placeholder="e.g. AAPL"
        ).upper()
    
    with col2:
        asset['weight'] = st.number_input(
            f"Weight {i+1} (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(asset['weight']),
            step=1.0,
            key=f"weight_{i}"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️", key=f"remove_{i}", help="Remove asset"):
            remove_asset(i)
            st.rerun()

# Botón para agregar nuevo activo
if st.sidebar.button("➕ Add Asset", use_container_width=True):
    add_asset()
    st.rerun()

# Mostrar suma de pesos
total_weight = sum(asset['weight'] for asset in st.session_state.assets)
if total_weight != 100:
    st.sidebar.warning(f"⚠️ Total weight: {total_weight:.1f}% (should be 100%)")
else:
    st.sidebar.success(f"✅ Total weight: {total_weight:.1f}%")

# Botones para distribución automática de pesos
st.sidebar.markdown("**Quick Weight Distribution:**")
col_eq, col_rand = st.sidebar.columns(2)

with col_eq:
    if st.button("⚖️ Equal", use_container_width=True, help="Distribute weights equally"):
        num_assets = len(st.session_state.assets)
        equal_weight = 100.0 / num_assets
        for asset in st.session_state.assets:
            asset['weight'] = round(equal_weight, 2)
        st.rerun()

with col_rand:
    if st.button("🎲 Random", use_container_width=True, help="Distribute weights randomly"):
        # Generar pesos aleatorios que sumen 100
        random_weights = np.random.dirichlet(np.ones(len(st.session_state.assets))) * 100
        for i, asset in enumerate(st.session_state.assets):
            asset['weight'] = round(random_weights[i], 2)
        st.rerun()

st.sidebar.markdown("---")

# Parámetros de fecha y capital
start_date = st.sidebar.date_input("From", date(2020, 1, 1))
end_date = st.sidebar.date_input("To", date.today())

initial_capital = st.sidebar.number_input(
    "Initial Capital (USD)", value=10000.0, step=500.0
)

benchmark_ticker = "SPY"

run = st.sidebar.button("🚀 Simulate", use_container_width=True, type="primary")

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
        # Filtrar activos válidos
        tickers = [asset['ticker'] for asset in st.session_state.assets if asset['ticker'].strip()]
        weights = [asset['weight'] / 100.0 for asset in st.session_state.assets if asset['ticker'].strip()]

        if len(tickers) == 0:
            st.error("Please add at least one symbol")
            st.stop()

        if len(tickers) != len(weights):
            st.error("The number of weights and symbols must match")
            st.stop()

        # Normalizar pesos (por si no suman exactamente 100%)
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
        st.subheader("Portfolio vs Benchmark (SPY)")

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

        st.subheader("Asset Prices (Adjusted)")
        st.line_chart(asset_prices)

        # =========================
        # TABLE
        # =========================
        st.subheader("Portfolio Composition")
        table = pd.DataFrame({
            "Ticker": tickers,
            "Weight (%)": [w * 100 for w in weights],
            "Allocated Capital (USD)": weights * initial_capital
        })
        st.dataframe(table, use_container_width=True)

    except Exception as e:
        st.error(f"Simulation error: {e}")

st.markdown("---")
st.caption("Educational simulator · Not financial advice")
