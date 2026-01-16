import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as iogo
from datetime import date, timedelta

# =========================
# CONFIGURACIÓN Y ESTILO
# =========================
st.set_page_config(page_title="Pro Portfolio Simulator", layout="wide", page_icon="📈")

# CSS personalizado para mejorar la estética
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Pro Portfolio Simulator")
st.caption("Herramienta de análisis cuantitativo estilo Kwanti")

# =========================
# SIDEBAR - PARÁMETROS
# =========================
with st.sidebar:
    st.header("Configuración")
    
    if 'assets' not in st.session_state:
        st.session_state.assets = [
            {'ticker': 'SPY', 'weight': 50.0},
            {'ticker': 'QQQ', 'weight': 50.0}
        ]

    # Gestión de activos
    st.subheader("🔍 Activos")
    for i, asset in enumerate(st.session_state.assets):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            asset['ticker'] = st.text_input(f"Ticker", value=asset['ticker'], key=f"t_{i}").upper()
        with col2:
            asset['weight'] = st.number_input(f"%", value=float(asset['weight']), key=f"w_{i}")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"r_{i}"):
                st.session_state.assets.pop(i)
                st.rerun()

    if st.button("➕ Añadir Activo"):
        st.session_state.assets.append({'ticker': '', 'weight': 0.0})
        st.rerun()

    total_w = sum(a['weight'] for a in st.session_state.assets)
    if abs(total_w - 100) > 0.01:
        st.error(f"Pesos: {total_w}% (Debe ser 100%)")
    else:
        st.success("✅ Pesos validados")

    st.divider()
    
    start_date = st.date_input("Fecha Inicio", date.today() - timedelta(days=365*5))
    end_date = st.date_input("Fecha Fin", date.today())
    initial_cap = st.number_input("Capital Inicial (USD)", value=10000)
    benchmark_symbol = st.text_input("Benchmark (ej. SPY)", "SPY")
    
    run_btn = st.button("🚀 EJECUTAR SIMULACIÓN", use_container_width=True, type="primary")

# =========================
# LÓGICA DE CÁLCULO
# =========================
def get_data(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, auto_adjust=True)['Close']
    return data

if run_btn and abs(total_w - 100) < 0.01:
    try:
        with st.spinner('Calculando métricas...'):
            tickers = [a['ticker'] for a in st.session_state.assets]
            weights = np.array([a['weight']/100 for a in st.session_state.assets])
            
            # Descarga de datos
            all_tickers = list(set(tickers + [benchmark_symbol]))
            prices = get_data(all_tickers, start_date, end_date)
            
            if prices.empty:
                st.error("No se pudieron obtener datos. Revisa los tickers.")
                st.stop()

            # Cálculo de retornos
            returns = prices[tickers].pct_change().dropna()
            bench_returns = prices[benchmark_symbol].pct_change().dropna()
            
            # Cartera
            port_returns = returns.dot(weights)
            cum_port = (1 + port_returns).cumprod() * initial_cap
            cum_bench = (1 + bench_returns).cumprod() * initial_cap

            # =========================
            # MÉTRICAS CLAVE
            # =========================
            total_ret = (cum_port.iloc[-1] / initial_cap - 1) * 100
            ann_ret = ((1 + total_ret/100)**(252/len(port_returns)) - 1) * 100
            vol = port_returns.std() * np.sqrt(252) * 100
            sharpe = (ann_ret / vol) if vol != 0 else 0
            
            # Drawdown
            rolling_max = cum_port.cummax()
            drawdown = (cum_port - rolling_max) / rolling_max
            max_dd = drawdown.min() * 100

            # Dashboard de métricas
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Valor Final", f"${cum_port.iloc[-1]:,.2f}")
            m2.metric("Retorno Anualizado", f"{ann_ret:.2f}%")
            m3.metric("Ratio Sharpe", f"{sharpe:.2f}")
            m4.metric("Max Drawdown", f"{max_dd:.2f}%", delta_color="inverse")

            # =========================
            # GRÁFICOS INTERACTIVOS
            # =========================
            st.divider()
            
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("📈 Crecimiento de la Inversión")
                fig_growth = iogo.Figure()
                fig_growth.add_trace(iogo.Scatter(x=cum_port.index, y=cum_port, name="Cartera", line=dict(color='#1f77b4')))
                fig_growth.add_trace(iogo.Scatter(x=cum_bench.index, y=cum_bench, name=f"Benchmark ({benchmark_symbol})", line=dict(color='#ff7f0e', dash='dash')))
                fig_growth.update_layout(hovermode="x unified", template="plotly_white")
                st.plotly_chart(fig_growth, use_container_width=True)

            with col_right:
                st.subheader("📉 Análisis de Drawdown (Riesgo)")
                fig_dd = px.area(drawdown * 100, title="Caída desde el máximo (%)", color_discrete_sequence=['red'])
                fig_dd.update_layout(showlegend=False, template="plotly_white")
                st.plotly_chart(fig_dd, use_container_width=True)

            st.divider()

            col_bot1, col_bot2 = st.columns(2)

            with col_bot1:
                st.subheader("🧩 Correlación entre Activos")
                corr_matrix = returns.corr()
                fig_corr = px.imshow(corr_matrix, text_auto=True, color_continuous_scale='RdBu_r')
                st.plotly_chart(fig_corr, use_container_width=True)
                st.info("Una correlación baja (cercana a 0) indica mejor diversificación.")

            with col_bot2:
                st.subheader("🍰 Composición")
                fig_pie = px.pie(values=weights*100, names=tickers, hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as e:
        st.error(f"Error en la simulación: {e}")

else:
    st.info("Configura los activos en la barra lateral y haz clic en 'Ejecutar Simulación'. Asegúrate de que los pesos sumen 100%.")

st.markdown("---")
st.caption("Nota: Los datos son obtenidos de Yahoo Finance. Este simulador no constituye asesoría financiera.")
