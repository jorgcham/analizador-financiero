import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date

# -------------------------
# Configuración página
# -------------------------
st.set_page_config(page_title="Simulador de Portfolio", layout="wide")

st.title("📊 Simulador de Inversiones de Portfolio")
st.markdown("Simula qué habría pasado si hubieras invertido en un conjunto de acciones en un periodo determinado.")

# -------------------------
# Sidebar - Inputs
# -------------------------
st.sidebar.header("Parámetros de simulación")

symbols_input = st.sidebar.text_input(
    "Símbolos de acciones (separados por coma)",
    value="AAPL,MSFT,GOOGL"
)

start_date = st.sidebar.date_input(
    "Fecha de inicio",
    value=date(2020, 1, 1)
)

end_date = st.sidebar.date_input(
    "Fecha de fin",
    value=date.today()
)

initial_investment = st.sidebar.number_input(
    "Capital inicial (€)",
    min_value=0.0,
    value=10000.0,
    step=500.0
)

weights_input = st.sidebar.text_input(
    "Pesos del portfolio (ej: 0.4,0.3,0.3)",
    value="0.34,0.33,0.33"
)

run_button = st.sidebar.button("Simular")

# -------------------------
# Funciones auxiliares
# -------------------------

def load_data(symbols, start, end):
    raw = yf.download(symbols, start=start, end=end, progress=False)

    if raw.empty:
        return pd.DataFrame()

    # Manejo robusto de Adj Close
    if isinstance(raw.columns, pd.MultiIndex):
        data = raw["Adj Close"]
    else:
        data = raw[["Adj Close"]]
        data.columns = symbols

    return data.dropna()


def normalize_weights(weights):
    weights = np.array(weights, dtype=float)
    return weights / weights.sum()


def simulate_portfolio(prices, weights, investment):
    returns = prices.pct_change().dropna()
    portfolio_returns = returns.dot(weights)
    portfolio_value = (1 + portfolio_returns).cumprod() * investment
    return portfolio_value, portfolio_returns

# -------------------------
# Lógica principal
# -------------------------
if run_button:
    try:
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
        weights = [float(w.strip()) for w in weights_input.split(",") if w.strip()]

        if len(symbols) == 0:
            st.error("❌ Introduce al menos un símbolo")
            st.stop()

        if len(symbols) != len(weights):
            st.error("❌ El número de símbolos y pesos debe coincidir")
            st.stop()

        weights = normalize_weights(weights)

        prices = load_data(symbols, start_date, end_date)

        if prices.empty:
            st.error("❌ No se pudieron obtener datos para los símbolos seleccionados")
            st.stop()

        portfolio_value, portfolio_returns = simulate_portfolio(
            prices, weights, initial_investment
        )

        # -------------------------
        # Métricas
        # -------------------------
        total_return = (portfolio_value.iloc[-1] / initial_investment - 1) * 100
        annualized_return = (
            (portfolio_value.iloc[-1] / initial_investment)
            ** (252 / len(portfolio_value))
            - 1
        ) * 100
        volatility = portfolio_returns.std() * np.sqrt(252) * 100

        col1, col2, col3 = st.columns(3)
        col1.metric("Valor final (€)", f"{portfolio_value.iloc[-1]:,.2f}")
        col2.metric("Retorno total (%)", f"{total_return:.2f}%")
        col3.metric("Volatilidad anual (%)", f"{volatility:.2f}%")

        # -------------------------
        # Gráficos
        # -------------------------
        st.subheader("📈 Evolución del valor del portfolio")
        st.line_chart(portfolio_value)

        st.subheader("📊 Precios ajustados de las acciones")
        st.line_chart(prices)

        # -------------------------
        # Tabla resumen
        # -------------------------
        st.subheader("📋 Resumen del portfolio")
        summary_df = pd.DataFrame({
            "Símbolo": symbols,
            "Peso": weights,
            "Inversión inicial (€)": weights * initial_investment
        })

        st.dataframe(summary_df, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Error en la simulación: {e}")

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption("Simulador educativo. No constituye asesoramiento financiero.")
