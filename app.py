import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(page_title="Ultra Portfolio Analyzer", layout="wide", page_icon="💰")

st.markdown("""
    <style>
    .metric-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# =========================
# FUNCIONES NUCLEARES
# =========================
@st.cache_data(ttl=86400)
def get_clean_data(tickers, start, end):
    # Descargamos datos con dividendos para calcular el Income
    data = yf.download(tickers, start=start, end=end, actions=True)
    if data.empty:
        return None, None
    
    # Manejo de Multi-index de yfinance
    if isinstance(data.columns, pd.MultiIndex):
        prices = data['Close']
        dividends = data['Dividends']
    else:
        prices = data[['Close']]
        prices.columns = tickers
        dividends = data[['Dividends']]
        dividends.columns = tickers
        
    return prices.ffill(), dividends.fillna(0)

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("🏢 Composición de Cartera")
    
    if 'assets' not in st.session_state:
        st.session_state.assets = [{'ticker': 'AAPL', 'weight': 50.0}, {'ticker': 'MSFT', 'weight': 50.0}]

    for i, asset in enumerate(st.session_state.assets):
        cols = st.columns([3, 2, 1])
        asset['ticker'] = cols[0].text_input(f"Ticker", asset['ticker'], key=f"t_{i}").upper()
        asset['weight'] = cols[1].number_input(f"%", value=float(asset['weight']), key=f"w_{i}")
        if cols[2].button("❌", key=f"del_{i}"):
            st.session_state.assets.pop(i)
            st.rerun()

    if st.button("➕ Añadir Activo"):
        st.session_state.assets.append({'ticker': 'SPY', 'weight': 0.0})
        st.rerun()

    st.divider()
    start_date = st.date_input("Fecha Inicio", date.today() - timedelta(days=365*3))
    capital = st.number_input("Capital Inicial ($)", value=10000)
    
    run = st.button("📊 ANALIZAR AHORA", use_container_width=True, type="primary")

# =========================
# LÓGICA PRINCIPAL
# =========================
if run:
    tickers = [a['ticker'] for a in st.session_state.assets if a['ticker']]
    weights = np.array([a['weight']/100 for a in st.session_state.assets if a['ticker']])
    
    if abs(sum(weights) - 1.0) > 0.001:
        st.error(f"Los pesos suman {sum(weights)*100:.1f}%. Deben sumar 100%.")
        st.stop()

    prices, divs = get_clean_data(tickers, start_date, date.today())
    bench_prices, _ = get_clean_data(['SPY'], start_date, date.today())

    if prices is not None:
        # 1. Cálculos de Performance
        rets = prices.pct_change().dropna()
        port_rets = rets.dot(weights)
        
        cum_prod = (1 + port_rets).cumprod()
        portfolio_value = cum_prod * capital
        
        # 2. Income (Dividendos)
        # Estimamos income basado en los dividendos pagados por unidad invertida
        shares = (weights * capital) / prices.iloc[0]
        portfolio_divs = (divs * shares).sum(axis=1)
        total_income = portfolio_divs.sum()
        
        # 3. Métricas de Riesgo
        vol_anual = port_rets.std() * np.sqrt(252) * 100
        total_ret = (cum_prod.iloc[-1] - 1) * 100
        ann_ret = ((1 + total_ret/100)**(252/len(port_rets)) - 1) * 100
        
        # Max Drawdown
        peak = portfolio_value.cummax()
        drawdown = (portfolio_value - peak) / peak
        max_dd = drawdown.min() * 100

        # --- VISUALIZACIÓN ---
        st.title("Resultados del Análisis")
        
        # Fila 1: Métricas Clave
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valor Final", f"${portfolio_value.iloc[-1]:,.2f}")
        c2.metric("Retorno Total", f"{total_ret:.2f}%")
        c3.metric("Income Generado (Divs)", f"${total_income:,.2f}")
        c4.metric("Max Drawdown", f"{max_dd:.2f}%", delta_color="inverse")

        st.divider()

        # Fila 2: Gráficos Principales
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            st.subheader("🚀 Crecimiento del Capital")
            fig_perf = px.line(portfolio_value, labels={'value': 'USD', 'Date': 'Fecha'})
            fig_perf.update_layout(showlegend=False, template="plotly_white")
            st.plotly_chart(fig_perf, use_container_width=True)
            

        with col_g2:
            st.subheader("🛡️ Perfil de Riesgo")
            st.write(f"**Volatilidad Anual:** {vol_anual:.2f}%")
            st.write(f"**Sharpe Ratio:** {(ann_ret/vol_anual):.2f}")
            
            # Gráfico de tarta de composición
            fig_pie = px.pie(names=tickers, values=weights, hole=0.5)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()

        # Fila 3: Income y Drawdown
        col_g3, col_g4 = st.columns(2)
        
        with col_g3:
            st.subheader("💵 Income Mensual Estimado")
            monthly_income = portfolio_divs.resample('M').sum()
            fig_inc = px.bar(monthly_income, labels={'value': 'USD', 'Date': 'Mes'})
            st.plotly_chart(fig_inc, use_container_width=True)

        with col_g4:
            st.subheader("📉 Análisis de Caídas (Drawdown)")
            fig_dd = px.area(drawdown * 100, labels={'value': '% Caída'})
            fig_dd.update_traces(fillcolor='rgba(255, 0, 0, 0.3)', line_color='red')
            st.plotly_chart(fig_dd, use_container_width=True)
            

        # Fila 4: Matriz de Correlación
        st.subheader("🔗 Correlación entre Activos")
        st.write("Si los activos están muy correlacionados (cerca de 1), el riesgo es mayor.")
        fig_corr = px.imshow(rets.corr(), text_auto=".2f", color_continuous_scale='RdBu_r')
        st.plotly_chart(fig_corr, use_container_width=True)

    else:
        st.error("Error al descargar datos. Verifica que los Tickers sean correctos.")

else:
    st.info("Configura tu cartera en el panel izquierdo y haz clic en Analizar.")
