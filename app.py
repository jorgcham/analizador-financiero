import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from streamlit_searchbox import st_searchbox
import requests

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(page_title="Quant Search Simulator", layout="wide", page_icon="🔍")

# Función para buscar tickers en la API de Yahoo Finance
def search_yahoo_tickers(searchterm: str):
    if not searchterm:
        return []
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={searchterm}&quotesCount=5"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    data = response.json()
    # Retorna una lista de tuplas (Nombre para mostrar, Valor del ticker)
    return [f"{res['symbol']} - {res.get('longname', '')}" for res in data.get('quotes', [])]

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("🚀 Mi Cartera")
    
    if 'assets' not in st.session_state:
        st.session_state.assets = []

    # Buscador Predictivo para añadir activos
    st.subheader("Añadir nuevo activo")
    selected_ticker_full = st_searchbox(
        search_yahoo_tickers,
        placeholder="Escribe el nombre o ticker (ej: Apple)...",
        key="ticker_searcher",
    )

    if selected_ticker_full:
        # Extraemos solo el ticker (lo que está antes del guion)
        ticker_to_add = selected_ticker_full.split(" - ")[0]
        if st.button(f"Añadir {ticker_to_add}"):
            if not any(a['ticker'] == ticker_to_add for a in st.session_state.assets):
                st.session_state.assets.append({'ticker': ticker_to_add, 'weight': 0.0})
                st.rerun()

    st.divider()

    # Mostrar y editar activos añadidos
    for i, asset in enumerate(st.session_state.assets):
        cols = st.columns([3, 2, 1])
        cols[0].markdown(f"**{asset['ticker']}**")
        asset['weight'] = cols[1].number_input(f"%", value=float(asset['weight']), key=f"w_{i}", step=5.0)
        if cols[2].button("🗑️", key=f"del_{i}"):
            st.session_state.assets.pop(i)
            st.rerun()

    total_w = sum(a['weight'] for a in st.session_state.assets)
    st.write(f"Suma total: `{total_w:.1f}%`")
    
    st.divider()
    start_date = st.date_input("Desde", date(2020, 1, 1))
    capital = st.number_input("Capital Inicial ($)", value=10000)
    
    run_btn = st.button("ANALIZAR CARTERA", use_container_width=True, type="primary")

# =========================
# LÓGICA DE DATOS Y VISUALIZACIÓN
# =========================
if run_btn:
    if abs(total_w - 100) > 0.1:
        st.error("Los pesos deben sumar 100%")
        st.stop()

    tickers = [a['ticker'] for a in st.session_state.assets]
    weights = np.array([a['weight']/100 for a in st.session_state.assets])

    with st.spinner('Obteniendo datos de Yahoo Finance...'):
        data = yf.download(tickers, start=start_date, actions=True)
        prices = data['Close'].ffill()
        divs = data['Dividends'].fillna(0) if 'Dividends' in data else pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # Performance
        rets = prices.pct_change().dropna()
        port_rets = rets.dot(weights)
        cum_value = (1 + port_rets).cumprod() * capital
        
        # Income (Dividendos)
        shares = (weights * capital) / prices.iloc[0]
        portfolio_divs = (divs * shares).sum(axis=1)

        # MÉTRICAS
        st.header(f"Resultados: Cartera vs SPY")
        
        c1, c2, c3, c4 = st.columns(4)
        total_ret = (cum_value.iloc[-1] / capital - 1) * 100
        ann_vol = port_rets.std() * np.sqrt(252) * 100
        
        c1.metric("Valor Final", f"${cum_value.iloc[-1]:,.2f}")
        c2.metric("Retorno Total", f"{total_ret:.2f}%")
        c3.metric("Volatilidad Anual", f"{ann_vol:.2f}%")
        c4.metric("Total Dividendos", f"${portfolio_divs.sum():,.2f}")

        # GRÁFICOS
        tab1, tab2, tab3 = st.tabs(["📈 Performance", "⚠️ Riesgo", "💰 Income"])
        
        with tab1:
            fig_perf = px.line(cum_value, title="Crecimiento de la Inversión")
            st.plotly_chart(fig_perf, use_container_width=True)
            
        with tab2:
            st.subheader("Análisis de Riesgo")
            peak = cum_value.cummax()
            dd = (cum_value - peak) / peak
            fig_dd = px.area(dd * 100, title="Máximo Drawdown (Caídas)", color_discrete_sequence=['red'])
            st.plotly_chart(fig_dd, use_container_width=True)
            
            st.subheader("Matriz de Correlación")
            fig_corr = px.imshow(rets.corr(), text_auto=".2f", color_continuous_scale='RdBu_r')
            st.plotly_chart(fig_corr, use_container_width=True)

        with tab3:
            st.subheader("Ingresos por Dividendos")
            monthly_div = portfolio_divs.resample('M').sum()
            fig_div = px.bar(monthly_div, title="Dividendos Mensuales Cobrados ($)")
            st.plotly_chart(fig_div, use_container_width=True)

else:
    st.info("Utiliza el buscador de la izquierda para añadir empresas y analiza tu estrategia.")
