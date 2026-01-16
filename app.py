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
# CONFIGURACIÓN Y ESTILO OSCURO
# =========================
st.set_page_config(page_title="Kwanti-Style Analytics", layout="wide", page_icon="📊")

# Aplicamos un tema oscuro personalizado vía CSS
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    .stMetric { background-color: #1e1e1e; padding: 15px; border-radius: 5px; border: 1px solid #333; }
    [data-testid="stSidebar"] { background-color: #1a1a1a; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e1e1e; border-radius: 5px 5px 0 0; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# Función de búsqueda de Yahoo Finance
def search_yahoo_tickers(searchterm: str):
    if not searchterm or len(searchterm) < 2: return []
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={searchterm}&quotesCount=5"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        return [f"{res['symbol']} - {res.get('longname', 'N/A')}" for res in data.get('quotes', [])]
    except: return []

# =========================
# SIDEBAR - GESTIÓN DE POSICIONES
# =========================
with st.sidebar:
    st.title("💼 Portfolio Setup")
    
    if 'assets' not in st.session_state:
        st.session_state.assets = []

    # Buscador de Tickers
    selected_full = st_searchbox(search_yahoo_tickers, placeholder="Add Symbol (e.g. AAPL)...", key="searcher")
    
    if selected_full:
        ticker = selected_full.split(" - ")[0]
        if st.button(f"➕ Add {ticker}", use_container_width=True):
            if not any(a['ticker'] == ticker for a in st.session_state.assets):
                st.session_state.assets.append({'ticker': ticker, 'weight': 0.0})
                st.rerun()

    st.divider()

    # Tabla de pesos en el Sidebar
    for i, asset in enumerate(st.session_state.assets):
        c1, c2, c3 = st.columns([3, 3, 1])
        c1.markdown(f"**{asset['ticker']}**")
        asset['weight'] = c2.number_input("%", value=float(asset['weight']), key=f"w_{i}", step=1.0)
        if c3.button("🗑️", key=f"del_{i}"):
            st.session_state.assets.pop(i)
            st.rerun()

    total_w = sum(a['weight'] for a in st.session_state.assets)
    if total_w != 100:
        st.warning(f"Total Weight: {total_w:.1f}%")
    else:
        st.success("Allocation: 100%")

    st.divider()
    start_date = st.date_input("From", date(2021, 1, 1))
    capital = st.number_input("Initial Value ($)", value=100000)
    benchmark = st.text_input("Comparison Benchmark", "SPY")
    
    analyze = st.button("🚀 RUN ANALYTICS", use_container_width=True, type="primary")

# =========================
# LÓGICA DE DATOS
# =========================
if analyze and len(st.session_state.assets) > 0:
    tickers = [a['ticker'] for a in st.session_state.assets]
    weights = np.array([a['weight']/100 for a in st.session_state.assets])
    
    with st.spinner('Synchronizing Market Data...'):
        # Descargamos datos de activos + benchmark
        all_syms = list(set(tickers + [benchmark]))
        data = yf.download(all_syms, start=start_date, actions=True)
        
        prices = data['Close'].ffill()
        divs = data['Dividends'].fillna(0) if 'Dividends' in data else pd.DataFrame(0, index=prices.index, columns=prices.columns)
        
        # Cálculos de Cartera
        rets = prices[tickers].pct_change().dropna()
        port_rets = rets.dot(weights)
        cum_value = (1 + port_rets).cumprod() * capital
        
        # Cálculos de Benchmark
        bench_rets = prices[benchmark].pct_change().dropna()
        bench_value = (1 + bench_rets).cumprod() * capital

    # =========================
    # VISTA ESTILO KWANTI
    # =========================
    st.title("Portfolio Analytics")

    # Fila Superior: Tabla de Posiciones y Gráfico de Tarta
    col_table, col_pie = st.columns([2, 1])
    
    with col_table:
        st.subheader(f"{len(tickers)} Positions")
        # Creamos el resumen de la tabla
        last_prices = prices[tickers].iloc[-1]
        table_data = pd.DataFrame({
            "Symbol": tickers,
            "Price": last_prices.values,
            "Weight": [f"{w*100:.1f}%" for w in weights],
            "Value": (weights * cum_value.iloc[-1]).astype(float)
        })
        st.dataframe(table_data.style.format({"Price": "${:,.2f}", "Value": "${:,.2f}"}), use_container_width=True, hide_index=True)
        st.caption(f"Portfolio Total Value: ${cum_value.iloc[-1]:,.2f}")

    with col_pie:
        fig_pie = px.pie(names=tickers, values=weights, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # SISTEMA DE TABS (Igual que Kwanti)
    tab_perf, tab_inc, tab_corr, tab_risk = st.tabs(["📈 Performance", "💵 Income", "🔗 Correlations", "⚠️ Risk"])

    with tab_perf:
        # Gráfico de Línea Comparativo
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=cum_value.index, y=cum_value, name="Demo Portfolio", line=dict(color='#a6ce39', width=2)))
        fig_line.add_trace(go.Scatter(x=bench_value.index, y=bench_value, name=f"{benchmark} Index", line=dict(color='#4a90e2', width=2)))
        fig_line.update_layout(template="plotly_dark", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Métricas de Performance
        p1, p2, p3 = st.columns(3)
        total_ret = (cum_value.iloc[-1] / capital - 1) * 100
        bench_ret = (bench_value.iloc[-1] / capital - 1) * 100
        p1.metric("Total Return", f"{total_ret:.2f}%", f"{total_ret - bench_ret:.2f}% vs Bench")
        p2.metric("Annualized Return", f"{((1 + total_ret/100)**(252/len(port_rets)) - 1)*100:.2f}%")
        p3.metric("Sharpe Ratio", f"{(port_rets.mean()*252) / (port_rets.std()*np.sqrt(252)):.2f}")

    with tab_inc:
        st.subheader("Estimated Dividend Income")
        shares = (weights * capital) / prices[tickers].iloc[0]
        portfolio_divs = (divs[tickers] * shares).sum(axis=1)
        monthly_divs = portfolio_divs.resample('M').sum()
        
        fig_inc = px.bar(x=monthly_divs.index, y=monthly_divs.values, labels={'x': 'Date', 'y': 'Income ($)'}, color_discrete_sequence=['#a6ce39'])
        fig_inc.update_layout(template="plotly_dark")
        st.plotly_chart(fig_inc, use_container_width=True)
        st.write(f"**Total Dividends Received:** ${portfolio_divs.sum():,.2f}")

    with tab_corr:
        st.subheader("Asset Correlation Matrix")
        corr = rets.corr()
        fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale='RdBu_r', range_color=[-1, 1])
        fig_corr.update_layout(template="plotly_dark")
        st.plotly_chart(fig_corr, use_container_width=True)

    with tab_risk:
        st.subheader("Risk & Volatility Analysis")
        # Drawdown
        peak = cum_value.cummax()
        dd = (cum_value - peak) / peak
        fig_dd = px.area(x=dd.index, y=dd.values * 100, title="Drawdown (%)", color_discrete_sequence=['#ff4b4b'])
        fig_dd.update_layout(template="plotly_dark")
        st.plotly_chart(fig_dd, use_container_width=True)
        
        r1, r2 = st.columns(2)
        r1.metric("Max Drawdown", f"{dd.min()*100:.2f}%")
        r2.metric("Annual Volatility", f"{port_rets.std()*np.sqrt(252)*100:.2f}%")

else:
    # Estado inicial: Pantalla vacía estilo Dashboard
    st.info("👈 Please add symbols and set weights to 100% in the sidebar to begin analysis.")
    ```

### ¿Qué hace a esta versión "Kwanti-Style"?

1.  **Layout de Dos Niveles:** Al igual que en tu imagen, arriba tienes la **Tabla de Posiciones** y el **Gráfico de Tarta (Pie Chart)**. Abajo tienes el análisis temporal.
2.  **Sistema de Pestañas (Tabs):** He implementado las pestañas exactas que se ven en Kwanti: *Performance, Income, Correlations y Risk*.
3.  **Visualización Dark:** He inyectado CSS para forzar un fondo gris oscuro/negro y tarjetas que resaltan la información, imitando la estética de terminal financiera.
4.  **Comparación Directa:** El gráfico principal siempre compara tu "Demo Portfolio" contra el Benchmark (normalmente SPY), calculando el diferencial de retorno.
5.  **Buscador Integrado:** Puedes añadir activos escribiendo su nombre, y el sistema limpia los datos automáticamente.

**¿Qué más podemos añadir?**
Si quieres ir más allá, puedo añadir la función **"Optimize"** (que aparece en el menú de arriba de tu imagen) para que el simulador calcule automáticamente qué pesos te darían el máximo retorno con el mínimo riesgo. ¿Te interesa?
