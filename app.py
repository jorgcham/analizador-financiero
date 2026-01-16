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
# CONFIGURACIÓN Y ESTILO
# =========================
st.set_page_config(page_title="Kwanti Pro Simulator", layout="wide", page_icon="📈")

# Estilo CSS para imitar la interfaz oscura de Kwanti
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 5px; }
    .stTabs [data-baseweb="tab-list"] { background-color: #0e1117; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; }
    .stTabs [data-baseweb="tab"]:hover { color: #ffffff; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #58a6ff; border-bottom-color: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

def search_yahoo_tickers(searchterm: str):
    if not searchterm or len(searchterm) < 2: return []
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={searchterm}&quotesCount=5"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = response.json()
        return [f"{res['symbol']} - {res.get('longname', 'N/A')}" for res in data.get('quotes', [])]
    except: return []

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.title("Settings")
    
    if 'assets' not in st.session_state:
        st.session_state.assets = []

    st.subheader("Add Assets")
    selected_full = st_searchbox(search_yahoo_tickers, placeholder="Search Symbol...", key="search_bar")
    
    if selected_full:
        ticker = selected_full.split(" - ")[0]
        if st.button(f"Add {ticker}", use_container_width=True):
            if not any(a['ticker'] == ticker for a in st.session_state.assets):
                st.session_state.assets.append({'ticker': ticker, 'weight': 0.0})
                st.rerun()

    st.divider()
    for i, asset in enumerate(st.session_state.assets):
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.write(f"**{asset['ticker']}**")
        asset['weight'] = c2.number_input("%", value=float(asset['weight']), key=f"w_{i}", step=1.0)
        if c3.button("🗑️", key=f"d_{i}"):
            st.session_state.assets.pop(i)
            st.rerun()

    total_w = sum(a['weight'] for a in st.session_state.assets)
    st.write(f"**Total Allocation:** {total_w:.1f}%")
    
    st.divider()
    start_date = st.date_input("Start Date", date(2022, 1, 1))
    capital = st.number_input("Capital ($)", value=100000)
    benchmark = st.text_input("Benchmark", "SPY")
    
    run_btn = st.button("RUN SIMULATION", use_container_width=True, type="primary")

# =========================
# MAIN ANALYTICS
# =========================
if run_btn and len(st.session_state.assets) > 0:
    tickers = [a['ticker'] for a in st.session_state.assets]
    weights = np.array([a['weight']/100 for a in st.session_state.assets])
    
    with st.spinner('Downloading Market Data...'):
        all_syms = list(set(tickers + [benchmark]))
        data = yf.download(all_syms, start=start_date, actions=True)
        prices = data['Close'].ffill()
        divs = data['Dividends'].fillna(0) if 'Dividends' in data else pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # Portfolio returns
        rets = prices[tickers].pct_change().dropna()
        port_rets = rets.dot(weights)
        cum_value = (1 + port_rets).cumprod() * capital
        
        # Benchmark returns
        bench_rets = prices[benchmark].pct_change().dropna()
        bench_value = (1 + bench_rets).cumprod() * capital

    # Header de Posiciones (Estilo tabla Kwanti)
    st.subheader("Portfolio Positions")
    col_t, col_p = st.columns([2, 1])
    
    with col_t:
        last_prices = prices[tickers].iloc[-1]
        df_summary = pd.DataFrame({
            "Symbol": tickers,
            "Last Price": last_prices.values,
            "Weight": [f"{w*100:.1f}%" for w in weights],
            "Allocated Value": (weights * cum_value.iloc[-1]).astype(float)
        })
        st.dataframe(df_summary.style.format({"Last Price": "${:,.2f}", "Allocated Value": "${:,.2f}"}), 
                     hide_index=True, use_container_width=True)

    with col_p:
        fig_pie = px.pie(names=tickers, values=weights, hole=0.5, 
                         color_discrete_sequence=px.colors.sequential.Blues_r)
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=False, 
                              paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    # Tabs de Análisis
    t_perf, t_risk, t_inc = st.tabs(["Performance", "Risk Analysis", "Income"])

    with t_perf:
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=cum_value.index, y=cum_value, name="My Portfolio", line=dict(color='#00ff00', width=2)))
        fig_line.add_trace(go.Scatter(x=bench_value.index, y=bench_value, name=benchmark, line=dict(color='#58a6ff', width=2, dash='dash')))
        fig_line.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', 
                              plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified")
        st.plotly_chart(fig_line, use_container_width=True)

    with t_risk:
        st.subheader("Drawdown & Correlation")
        peak = cum_value.cummax()
        dd = (cum_value - peak) / peak
        fig_dd = px.area(x=dd.index, y=dd.values * 100, title="Drawdown (%)", color_discrete_sequence=['red'])
        fig_dd.update_layout(template="plotly_dark")
        st.plotly_chart(fig_dd, use_container_width=True)
        
        st.subheader("Correlation Matrix")
        fig_corr = px.imshow(rets.corr(), text_auto=".2f", color_continuous_scale='RdBu_r')
        st.plotly_chart(fig_corr, use_container_width=True)

    with t_inc:
        st.subheader("Dividends")
        shares = (weights * capital) / prices[tickers].iloc[0]
        portfolio_divs = (divs[tickers] * shares).sum(axis=1)
        st.metric("Total Income (Dividends)", f"${portfolio_divs.sum():,.2f}")
        fig_div = px.bar(portfolio_divs.resample('M').sum(), title="Monthly Income")
        st.plotly_chart(fig_div, use_container_width=True)

else:
    st.info("Add tickers in the sidebar and click 'RUN SIMULATION' to start.")
