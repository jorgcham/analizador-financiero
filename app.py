import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

# =========================
# CONFIGURACIÓN Y ESTILO
# =========================
st.set_page_config(page_title="Quant Portfolio Pro", layout="wide", page_icon="📈")

# Estilo para tarjetas de métricas
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1f77b4; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# =========================
# FUNCIONES DE CÁLCULO
# =========================
@st.cache_data(ttl=3600)
def download_data(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, auto_adjust=True)['Close']
    return data

def calculate_metrics(returns, weights, initial_capital):
    port_returns = returns.dot(weights)
    cum_returns = (1 + port_returns).cumprod()
    cum_value = cum_returns * initial_capital
    
    # Métricas anualizadas
    total_return = (cum_returns.iloc[-1] - 1) * 100
    ann_return = ((cum_returns.iloc[-1])**(252/len(port_returns)) - 1) * 100
    volatility = port_returns.std() * np.sqrt(252) * 100
    sharpe = (ann_return / volatility) if volatility != 0 else 0
    
    # Drawdown
    rolling_max = cum_returns.cummax()
    drawdown = (cum_returns - rolling_max) / rolling_max
    max_dd = drawdown.min() * 100
    
    return port_returns, cum_value, ann_return, volatility, sharpe, max_dd, drawdown

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("⚙️ Panel de Control")
    
    if 'assets' not in st.session_state:
        st.session_state.assets = [
            {'ticker': 'SPY', 'weight': 60.0},
            {'ticker': 'QQQ', 'weight': 40.0}
        ]

    st.subheader("📋 Composición")
    for i, asset in enumerate(st.session_state.assets):
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            asset['ticker'] = st.text_input(f"Ticker {i}", value=asset['ticker'], key=f"t_{i}").upper()
        with c2:
            asset['weight'] = st.number_input(f"%", value=float(asset['weight']), key=f"w_{i}", step=5.0)
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"r_{i}"):
                st.session_state.assets.pop(i)
                st.rerun()

    if st.button("➕ Añadir Activo", use_container_width=True):
        st.session_state.assets.append({'ticker': '', 'weight': 0.0})
        st.rerun()

    total_w = sum(a['weight'] for a in st.session_state.assets)
    st.progress(min(total_w/100, 1.0))
    st.write(f"Suma total: **{total_w:.1f}%**")

    st.divider()
    
    start_date = st.date_input("Fecha Inicio", date.today() - timedelta(days=365*5))
    end_date = st.date_input("Fecha Fin", date.today())
    initial_cap = st.number_input("Capital (USD)", value=10000, step=1000)
    benchmark = st.text_input("Benchmark", "SPY").upper()
    
    run_simulation = st.button("🚀 INICIAR ANÁLISIS", use_container_width=True, type="primary")

# =========================
# CUERPO PRINCIPAL
# =========================
if run_simulation:
    if abs(total_w - 100) > 0.1:
        st.warning("⚠️ La suma de los pesos debe ser 100% para continuar.")
        st.stop()

    try:
        tickers = [a['ticker'] for a in st.session_state.assets if a['ticker']]
        weights = np.array([a['weight']/100 for a in st.session_state.assets if a['ticker']])
        
        # 1. Obtención de Datos
        with st.spinner("Descargando datos históricos..."):
            all_assets = list(set(tickers + [benchmark]))
            prices = download_data(all_assets, start_date, end_date)
            
            if prices.empty: 
                st.error("No se encontraron datos para los tickers ingresados.")
                st.stop()

            # Sincronizar retornos
            returns_all = prices.pct_change().dropna()
            port_returns_ts, port_value_ts, ann_ret, vol, sharpe, mdd, dd_series = calculate_metrics(
                returns_all[tickers], weights, initial_cap
            )
            
            bench_ret_ts, bench_value_ts, b_ann_ret, b_vol, b_sharpe, b_mdd, _ = calculate_metrics(
                returns_all[[benchmark]], [1.0], initial_cap
            )

        # 2. Resumen de Métricas
        st.subheader("📈 Resumen de Rendimiento")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Valor Final", f"${port_value_ts.iloc[-1]:,.2f}", f"{(port_value_ts.iloc[-1]/initial_cap - 1):.1%}")
        m2.metric("Retorno Anual", f"{ann_ret:.2f}%", f"vs {b_ann_ret:.2f}% Bench")
        m3.metric("Volatilidad Anual", f"{vol:.2f}%", f"{vol - b_vol:.1f}% vs Bench", delta_color="inverse")
        m4.metric("Máxima Caída (MDD)", f"{mdd:.2f}%", delta_color="normal")

        # 3. Gráfico Principal
        st.divider()
        fig_main = go.Figure()
        fig_main.add_trace(go.Scatter(x=port_value_ts.index, y=port_value_ts, name="Cartera", line=dict(color='#1f77b4', width=3)))
        fig_main.add_trace(go.Scatter(x=bench_value_ts.index, y=bench_value_ts, name=f"Benchmark ({benchmark})", line=dict(color='#cfcfcf', dash='dash')))
        fig_main.update_layout(title="Crecimiento del Capital (USD)", hovermode="x unified", template="none")
        st.plotly_chart(fig_main, use_container_width=True)

        # 4. Análisis Mensual (Heatmap)
        st.subheader("📅 Mapa de Calor de Retornos Mensuales")
        monthly_ret = port_returns_ts.resample('M').apply(lambda x: (1 + x).prod() - 1)
        heatmap_df = monthly_ret.to_frame(name='Ret')
        heatmap_df['Year'] = heatmap_df.index.year
        heatmap_df['Month'] = heatmap_df.index.strftime('%b')
        
        heatmap_pivot = heatmap_df.pivot(index='Year', columns='Month', values='Ret')
        months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        heatmap_pivot = heatmap_pivot.reindex(columns=[m for m in months_order if m in heatmap_pivot.columns])
        
        st.dataframe(heatmap_pivot.style.format("{:.2%}")
                     .background_gradient(cmap='RdYlGn', axis=None), use_container_width=True)

        # 5. Riesgo y Diversificación
        st.divider()
        col_risk1, col_risk2 = st.columns(2)
        
        with col_risk1:
            st.subheader("📉 Períodos de Drawdown")
            fig_dd = px.area(dd_series * 100, title="Caída desde máximos (%)", color_discrete_sequence=['#e74c3c'])
            fig_dd.update_layout(showlegend=False, template="none")
            st.plotly_chart(fig_dd, use_container_width=True)

        with col_risk2:
            st.subheader("🧬 Matriz de Correlación")
            corr_matrix = returns_all[tickers].corr()
            fig_corr = px.imshow(corr_matrix, text_auto=".2f", color_continuous_scale='Blues')
            st.plotly_chart(fig_corr, use_container_width=True)

        # 6. Optimización (Frontera Eficiente)
        st.divider()
        st.subheader("🎯 Optimización de Cartera (Simulación Monte Carlo)")
        
        num_portfolios = 500
        results = np.zeros((3, num_portfolios))
        
        for i in range(num_portfolios):
            w = np.random.random(len(tickers))
            w /= np.sum(w)
            p_ret = np.sum(returns_all[tickers].mean() * w) * 252
            p_vol = np.sqrt(np.dot(w.T, np.dot(returns_all[tickers].cov() * 252, w)))
            results[0,i] = p_ret
            results[1,i] = p_vol
            results[2,i] = p_ret / p_vol # Sharpe

        fig_scatter = px.scatter(x=results[1,:], y=results[0,:], color=results[2,:],
                                labels={'x': 'Volatilidad Esperada', 'y': 'Retorno Esperado', 'color': 'Sharpe Ratio'},
                                title="Frontera Eficiente (Escenarios Aleatorios)")
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.info("Este gráfico muestra 500 combinaciones posibles de tus activos. Los puntos amarillos son las carteras más eficientes.")

    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")

else:
    # Pantalla de Bienvenida
    st.info("👋 Configura tus tickers y pesos en la izquierda, luego presiona 'Iniciar Análisis'.")
    st.markdown("""
    ### Qué puedes analizar aquí:
    1. **Retorno vs Benchmark:** Compara tu estrategia con el S&P 500.
    2. **Análisis Mensual:** Mira en qué meses del año suele ir mejor tu cartera.
    3. **Riesgo:** Visualiza las caídas históricas y la correlación entre tus activos.
    4. **Optimización:** Descubre si existe una combinación de pesos más eficiente.
    """)



st.markdown("---")
st.caption("Quant Simulator 2026 | Datos de mercado vía yfinance")
