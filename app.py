import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(page_title="Simulador de Portfolio", layout="wide")
st.title("Portfolio Simulator")
st.markdown("___________________________________________________")

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Parameters")

tickers_input = st.sidebar.text_input(
    "Tickers (ej: AAPL,MSFT,GOOGL)",
    value="AAPL,MSFT,GOOGL"
)

weights_input = st.sidebar.text_input(
    "Weights (ej: 0.4,0.3,0.3)",
    value="0.34,0.33,0.33"
)

start_date = st.sidebar.date_input("From", date(2020, 1, 1))
end_date = st.sidebar.date_input("To", date.today())

initial_capital = st.sidebar.number_input(
    "Initial Capital ($)", value=10000.0, step=500.0
)

run = st.sidebar.button("Simular")

# =========================
# FUNCIONES
# =========================
def get_prices(tickers, start, end):
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


def simulate(prices, weights, capital):
    returns = prices.pct_change().dropna()
    portfolio_ret = returns.dot(weights)
    portfolio_value = (1 + portfolio_ret).cumprod() * capital
    return portfolio_value, portfolio_ret

# =========================
# MAIN
# =========================
if run:
    try:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        weights = [float(w.strip()) for w in weights_input.split(",") if w.strip()]

        if len(tickers) == 0:
            st.error("Add at least one symbol")
            st.stop()

        if len(tickers) != len(weights):
            st.error("The number of weights and symbols must be the same")
            st.stop()

        weights = normalize_weights(weights)

        prices = get_prices(tickers, start_date, end_date)
        if prices.empty:
            st.error("It wasn´t possible to download the data")
            st.stop()

        portfolio_value, portfolio_ret = simulate(
            prices, weights, initial_capital
        )

        # =========================
        # MÉTRICAS
        # =========================
        total_return = (portfolio_value.iloc[-1] / initial_capital - 1) * 100
        annual_return = (
            (portfolio_value.iloc[-1] / initial_capital)
            ** (252 / len(portfolio_value)) - 1
        ) * 100
        volatility = portfolio_ret.std() * np.sqrt(252) * 100

        c1, c2, c3 = st.columns(3)
        c1.metric("Final Value ($)", f"{portfolio_value.iloc[-1]:,.2f}")
        c2.metric("Total Return (%)", f"{total_return:.2f}%")
        c3.metric("Annual Volatility (%)", f"{volatility:.2f}%")

        # =========================
        # GRÁFICOS
        # =========================
        st.subheader("Porfolio Evolution")
        st.line_chart(portfolio_value)

        st.subheader("Adjusted Prices")
        st.line_chart(prices)

        # =========================
        # TABLA
        # =========================
        st.subheader("Portolio Composition")
        table = pd.DataFrame({
            "Ticker": tickers,
            "Weight": weights,
            "Asigned Capital (€)": weights * initial_capital
        })
        st.dataframe(table, use_container_width=True)

    except Exception as e:
        st.error(f"Error in the simulation: {e}")

st.markdown("---")
st.caption("_____________________________________________________")
