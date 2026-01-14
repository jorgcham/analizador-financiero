import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date
import plotly.graph_objects as go
import plotly.express as px

# =========================
# CONFIGURATION
# =========================
st.set_page_config(page_title="Portfolio Simulator", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #1e2130 0%, #2d3250 100%);
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        border-left: 4px solid #00ff88;
    }
    h1 {
        color: #00ff88;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e2130;
        border-radius: 8px;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Portfolio Simulator")

# =========================
# SIDEBAR
# =========================
st.sidebar.header("⚙️ Configuration")

# Inicializar session state
if 'assets' not in st.session_state:
    st.session_state.assets = [
        {'ticker': 'AAPL', 'weight': 20},
        {'ticker': 'MSFT', 'weight': 20},
        {'ticker': 'GOOGL', 'weight': 20},
        {'ticker': 'AMZN', 'weight': 20},
        {'ticker': 'NVDA', 'weight': 20}
    ]

if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None

st.sidebar.subheader("💼 Portfolio Assets")

# Funciones para gestionar activos
def add_asset():
    st.session_state.assets.append({'ticker': '', 'weight': 0})

def remove_asset(index):
    if len(st.session_state.assets) > 1:
        st.session_state.assets.pop(index)

# Mostrar activos
for i, asset in enumerate(st.session_state.assets):
    col1, col2, col3 = st.sidebar.columns([3, 2, 1])
    
    with col1:
        asset['ticker'] = st.text_input(
            f"Symbol",
            value=asset['ticker'],
            key=f"ticker_{i}",
            placeholder="AAPL",
            label_visibility="collapsed"
        ).upper()
    
    with col2:
        asset['weight'] = st.number_input(
            f"Weight",
            min_value=0.0,
            max_value=100.0,
            value=float(asset['weight']),
            step=1.0,
            key=f"weight_{i}",
            label_visibility="collapsed"
        )
    
    with col3:
        if st.button("🗑️", key=f"remove_{i}", help="Remove"):
            remove_asset(i)
            st.rerun()

if st.sidebar.button("➕ Add Asset", use_container_width=True):
    add_asset()
    st.rerun()

# Validación de pesos
total_weight = sum(asset['weight'] for asset in st.session_state.assets)
if total_weight != 100:
    st.sidebar.warning(f"⚠️ Total: {total_weight:.1f}%")
else:
    st.sidebar.success(f"✅ Total: {total_weight:.1f}%")

# Botones de distribución
st.sidebar.markdown("**Quick Distribution:**")
col_eq, col_rand = st.sidebar.columns(2)

def set_equal_weights():
    equal_weight = 100.0 / len(st.session_state.assets)
    for asset in st.session_state.assets:
        asset['weight'] = round(equal_weight, 2)

def set_random_weights():
    random_weights = np.random.dirichlet(np.ones(len(st.session_state.assets))) * 100
    for i, asset in enumerate(st.session_state.assets):
        asset['weight'] = round(random_weights[i], 2)

with col_eq:
    st.button("⚖️ Equal", use_container_width=True, on_click=set_equal_weights, key="equal_btn")

with col_rand:
    st.button("🎲 Random", use_container_width=True, on_click=set_random_weights, key="random_btn")

st.sidebar.markdown("---")

# Parámetros
start_date = st.sidebar.date_input("📅 From", date(2020, 1, 1))
end_date = st.sidebar.date_input("📅 To", date.today())
initial_capital = st.sidebar.number_input("💰 Initial Capital (USD)", value=10000.0, step=1000.0)

benchmark_ticker = st.sidebar.selectbox("📈 Benchmark", ["SPY", "QQQ", "DIA", "IWM"], index=0)

run = st.sidebar.button("🚀 Run Simulation", use_container_width=True, type="primary")

# =========================
# FUNCTIONS
# =========================
def download_prices(tickers, start, end):
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
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

def create_performance_chart(portfolio_value, benchmark_value, initial_capital):
    fig = go.Figure()
    
    dates = portfolio_value.index
    
    fig.add_trace(go.Scatter(
        x=dates, 
        y=(portfolio_value / initial_capital - 1) * 100,
        name='Portfolio',
        line=dict(color='#00ff88', width=3),
        fill='tonexty',
        fillcolor='rgba(0, 255, 136, 0.1)'
    ))
    
    fig.add_trace(go.Scatter(
        x=dates, 
        y=(benchmark_value / initial_capital - 1) * 100,
        name='Benchmark',
        line=dict(color='#4c9aff', width=2),
        opacity=0.7
    ))
    
    fig.update_layout(
        template='plotly_dark',
        height=500,
        hovermode='x unified',
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='#ffffff'),
        xaxis=dict(showgrid=True, gridcolor='#1e2130'),
        yaxis=dict(showgrid=True, gridcolor='#1e2130', title='Total Return (%)'),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=0, r=0, t=30, b=0)
    )
    
    return fig

def create_pie_chart(tickers, weights):
    colors = px.colors.qualitative.Set3
    
    fig = go.Figure(data=[go.Pie(
        labels=tickers,
        values=weights,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color='#0e1117', width=2)),
        textposition='inside',
        textinfo='label+percent',
        textfont=dict(size=14, color='white')
    )])
    
    fig.update_layout(
        template='plotly_dark',
        height=400,
        showlegend=True,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='#ffffff'),
        margin=dict(l=0, r=0, t=0, b=0)
    )
    
    return fig

# =========================
# MAIN
# =========================
if run:
    with st.spinner('🔄 Loading data and running simulation...'):
        try:
            tickers = [asset['ticker'] for asset in st.session_state.assets if asset['ticker'].strip()]
            weights = [asset['weight'] / 100.0 for asset in st.session_state.assets if asset['ticker'].strip()]

            if len(tickers) == 0:
                st.error("❌ Please add at least one symbol")
                st.stop()

            weights = normalize_weights(weights)

            # Download data
            asset_prices = download_prices(tickers, start_date, end_date)
            benchmark_prices = download_prices([benchmark_ticker], start_date, end_date)

            if asset_prices.empty or benchmark_prices.empty:
                st.error("❌ Could not download market data")
                st.stop()

            # Align dates
            prices = asset_prices.join(benchmark_prices, how="inner")
            asset_prices = prices[tickers]
            benchmark_prices = prices[benchmark_ticker]

            # Run simulations
            portfolio_value, portfolio_returns = portfolio_simulation(asset_prices, weights, initial_capital)
            benchmark_returns = benchmark_prices.pct_change().dropna()
            benchmark_value = (1 + benchmark_returns).cumprod() * initial_capital

            # Calculate metrics
            total_return = (portfolio_value.iloc[-1] / initial_capital - 1) * 100
            annual_return = ((portfolio_value.iloc[-1] / initial_capital) ** (252 / len(portfolio_value)) - 1) * 100
            volatility = portfolio_returns.std() * np.sqrt(252) * 100
            sharpe = sharpe_ratio(portfolio_returns)
            mdd = max_drawdown(portfolio_returns)
            
            b_total_return = (benchmark_value.iloc[-1] / initial_capital - 1) * 100
            b_annual_return = ((benchmark_value.iloc[-1] / initial_capital) ** (252 / len(benchmark_value)) - 1) * 100

            # Guardar resultados en session_state
            st.session_state.simulation_results = {
                'tickers': tickers,
                'weights': weights,
                'portfolio_value': portfolio_value,
                'benchmark_value': benchmark_value,
                'asset_prices': asset_prices,
                'total_return': total_return,
                'annual_return': annual_return,
                'volatility': volatility,
                'sharpe': sharpe,
                'mdd': mdd,
                'b_total_return': b_total_return,
                'b_annual_return': b_annual_return,
                'initial_capital': initial_capital,
                'benchmark_ticker': benchmark_ticker
            }

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.session_state.simulation_results = None
            st.session_state.simulation_results = None

# Mostrar resultados si existen
if st.session_state.simulation_results:
    results = st.session_state.simulation_results

    # =========================
    # DISPLAY
    # =========================
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Performance", "💰 Allocation", "📈 Asset Prices"])
    
    with tab1:
        # Metrics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        col1.metric("💵 Final Value", f"${results['portfolio_value'].iloc[-1]:,.0f}", 
                   f"{results['total_return']:+.2f}%")
        col2.metric("📈 Total Return", f"{results['total_return']:.2f}%")
        col3.metric("📆 Annual Return", f"{results['annual_return']:.2f}%")
        col4.metric("📉 Volatility", f"{results['volatility']:.2f}%")
        col5.metric("⚡ Sharpe Ratio", f"{results['sharpe']:.2f}")
        col6.metric("🔻 Max Drawdown", f"{results['mdd']:.2f}%")
        
        st.markdown("---")
        
        # Performance chart
        st.plotly_chart(create_performance_chart(
            results['portfolio_value'], 
            results['benchmark_value'], 
            results['initial_capital']), 
            use_container_width=True)
        
        # Comparison table
        st.subheader("📊 Portfolio vs Benchmark")
        comparison_df = pd.DataFrame({
            'Metric': ['Total Return', 'Annual Return', 'Volatility', 'Sharpe Ratio', 'Max Drawdown'],
            'Portfolio': [f"{results['total_return']:.2f}%", f"{results['annual_return']:.2f}%", 
                         f"{results['volatility']:.2f}%", f"{results['sharpe']:.2f}", f"{results['mdd']:.2f}%"],
            f"{results['benchmark_ticker']}": [f"{results['b_total_return']:.2f}%", 
                                                f"{results['b_annual_return']:.2f}%", "-", "-", "-"]
        })
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    with tab2:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🥧 Portfolio Allocation")
            st.plotly_chart(create_pie_chart(results['tickers'], results['weights'] * 100), 
                           use_container_width=True)
        
        with col2:
            st.subheader("📋 Position Details")
            position_df = pd.DataFrame({
                'Ticker': results['tickers'],
                'Weight (%)': [f"{w*100:.2f}%" for w in results['weights']],
                'Capital ($)': [f"${w * results['initial_capital']:,.2f}" for w in results['weights']],
                'Final Value ($)': [f"${results['portfolio_value'].iloc[-1] * w:,.2f}" for w in results['weights']]
            })
            st.dataframe(position_df, use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("📈 Individual Asset Performance")
        
        # Normalize prices
        normalized_prices = results['asset_prices'] / results['asset_prices'].iloc[0] * 100
        
        fig = go.Figure()
        colors = px.colors.qualitative.Set2
        
        for i, ticker in enumerate(results['tickers']):
            fig.add_trace(go.Scatter(
                x=normalized_prices.index,
                y=normalized_prices[ticker],
                name=ticker,
                line=dict(width=2, color=colors[i % len(colors)])
            ))
        
        fig.update_layout(
            template='plotly_dark',
            height=500,
            hovermode='x unified',
            plot_bgcolor='#0e1117',
            paper_bgcolor='#0e1117',
            font=dict(color='#ffffff'),
            xaxis=dict(showgrid=True, gridcolor='#1e2130'),
            yaxis=dict(showgrid=True, gridcolor='#1e2130', title='Normalized Price'),
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error: {e}")

else:
    # Placeholder
    st.info("👈 Configure your portfolio and click '🚀 Run Simulation' to start")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 Final Value", "$0.00")
    col2.metric("📈 Total Return", "0.00%")
    col3.metric("⚡ Sharpe Ratio", "0.00")

st.markdown("---")
st.caption("⚠️ Educational tool only • Not financial advice • Data provided by Yahoo Finance")
