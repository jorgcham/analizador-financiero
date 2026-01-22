import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# ==============================================================================
# PAGE CONFIG
# ==============================================================================
st.set_page_config(
    page_title="Professional Fundamental Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .positive {
        color: #28a745;
        font-weight: bold;
    }
    .negative {
        color: #dc3545;
        font-weight: bold;
    }
    .neutral {
        color: #ffc107;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# BENCHMARK ENGINE
# ==============================================================================
class BenchmarkEngine:
    SECTOR_ETF_MAP = {
        'Technology': 'XLK',
        'Financial Services': 'XLF',
        'Healthcare': 'XLV',
        'Consumer Cyclical': 'XLY',
        'Energy': 'XLE',
        'Industrials': 'XLI',
        'Consumer Defensive': 'XLP',
        'Utilities': 'XLU',
        'Real Estate': 'XLRE',
        'Communication Services': 'XLC',
        'Basic Materials': 'XLB'
    }

    @staticmethod
    def get_benchmark(sector):
        etf_ticker = BenchmarkEngine.SECTOR_ETF_MAP.get(sector, 'SPY')
        try:
            etf = yf.Ticker(etf_ticker)
            info = etf.info
            return {
                'ticker': etf_ticker,
                'pe': info.get('trailingPE', 20.0) or 20.0,
                'pb': info.get('priceToBook', 3.0) or 3.0,
                'ps': info.get('priceToSalesTrailing12Months', 2.0) or 2.0,
                'margin': info.get('profitMargins', 0.10) or 0.10,
                'roe': info.get('returnOnEquity', 0.12) or 0.12,
                'roa': info.get('returnOnAssets', 0.05) or 0.05,
            }
        except:
            return {
                'ticker': 'DEFAULT',
                'pe': 20.0, 'pb': 3.0, 'ps': 2.0,
                'margin': 0.10, 'roe': 0.12, 'roa': 0.05,
            }

# ==============================================================================
# DATA AUDITOR
# ==============================================================================
class DataAuditor:
    def __init__(self, analyst):
        self.analyst = analyst
        self.errors = []
        self.warnings = []
        self.verified_items = 0
        self.total_checks = 0

    def verify_all(self):
        # Verificación de datos brutos
        self.total_checks += 1
        if self.analyst.info:
            self.verified_items += 1
        
        # Verificar precio actual
        self.total_checks += 1
        current_price = self.analyst.get('currentPrice') or self.analyst.get('regularMarketPrice')
        if current_price and current_price > 0:
            self.verified_items += 1
        else:
            self.warnings.append("Precio actual no disponible")
        
        # Verificar P/E
        self.total_checks += 1
        pe = self.analyst.get('trailingPE')
        eps = self.analyst.get('trailingEps')
        if pe and current_price and eps and eps > 0:
            pe_calc = current_price / eps
            if abs(pe_calc - pe) / pe < 0.05:
                self.verified_items += 1
            else:
                self.warnings.append(f"P/E discrepancia detectada")
        
        # Verificar márgenes
        self.total_checks += 1
        gross_margin = self.analyst.get('grossMargins')
        if gross_margin and 0 <= gross_margin <= 1:
            self.verified_items += 1
        
        success_rate = (self.verified_items / self.total_checks * 100) if self.total_checks > 0 else 0
        
        return {
            'total_checks': self.total_checks,
            'verified': self.verified_items,
            'warnings': len(self.warnings),
            'errors': len(self.errors),
            'success_rate': success_rate,
            'warning_list': self.warnings,
            'error_list': self.errors
        }

# ==============================================================================
# FUNDAMENTAL ANALYST
# ==============================================================================
class FundamentalAnalyst:
    def __init__(self, ticker):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = {}
        self.financials = None
        self.balance = None
        self.cashflow = None
        self.history = None
        self.benchmark = {}

    def load_all_data(self):
        self.info = self.stock.info
        if not self.info.get('currentPrice') and not self.info.get('regularMarketPrice'):
            raise ValueError(f"Ticker {self.ticker} not found")
        
        try:
            self.financials = self.stock.financials
            self.balance = self.stock.balance_sheet
            self.cashflow = self.stock.cashflow
            self.history = self.stock.history(period="5y")
        except:
            pass
        
        sector = self.info.get('sector', 'Unknown')
        self.benchmark = BenchmarkEngine.get_benchmark(sector)

    def get(self, key, default=0.0):
        val = self.info.get(key)
        return float(val) if val is not None else default

    def get_statement_value(self, statement, key, period=0):
        try:
            if statement is not None and not statement.empty:
                if key in statement.index:
                    val = statement.loc[key].iloc[period]
                    return float(val) if pd.notna(val) else 0.0
        except:
            pass
        return 0.0

    def calculate_score(self):
        score = 0
        max_score = 100
        
        # Valuación
        pe = self.get('trailingPE')
        if pe > 0 and self.benchmark['pe'] > 0:
            if pe < self.benchmark['pe'] * 0.8:
                score += 20
            elif pe < self.benchmark['pe'] * 1.2:
                score += 10
        
        # Rentabilidad
        if self.get('profitMargins') > self.benchmark['margin']:
            score += 10
        if self.get('returnOnEquity') > self.benchmark['roe']:
            score += 10
        
        # Crecimiento
        if self.get('revenueGrowth') > 0.05:
            score += 10
        if self.get('earningsGrowth') > 0.05:
            score += 10
        
        # Salud financiera
        if self.get('currentRatio') > 1.5:
            score += 10
        de_ratio = self.get('debtToEquity') / 100.0 if self.get('debtToEquity') > 10 else self.get('debtToEquity')
        if de_ratio < 1.0:
            score += 10
        
        # Red flags
        red_flags = 0
        green_flags = 0
        
        if self.get('trailingEps') > 0:
            green_flags += 1
        else:
            red_flags += 1
        
        if self.get('freeCashflow') > 0:
            green_flags += 1
        else:
            red_flags += 1
        
        score += max(0, (green_flags - red_flags) * 3)
        score = min(score, max_score)
        
        return score

# ==============================================================================
# STREAMLIT APP
# ==============================================================================
def main():
    st.markdown('<div class="main-header">📊 Professional Fundamental Analysis Engine</div>', unsafe_allow_html=True)
    st.markdown("### Comprehensive Multi-Factor Equity Research Platform")
    
    # Sidebar
    with st.sidebar:
        st.header("🔍 Analysis Settings")
        ticker_input = st.text_input("Enter Ticker Symbol", value="AAPL", placeholder="e.g., AAPL, MSFT, NVDA")
        analyze_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
        
        st.divider()
        st.markdown("**About**")
        st.info("This tool provides comprehensive fundamental analysis using real-time data from Yahoo Finance.")
        
        st.markdown("**Features:**")
        st.markdown("✅ Valuation Metrics\n✅ Profitability Analysis\n✅ Financial Health\n✅ Growth Metrics\n✅ Data Auditing")
    
    if analyze_button and ticker_input:
        with st.spinner(f'🔄 Loading data for {ticker_input.upper()}...'):
            try:
                analyst = FundamentalAnalyst(ticker_input)
                analyst.load_all_data()
                
                # Company Overview
                st.header("1️⃣ Company Overview")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Ticker", analyst.ticker)
                    st.metric("Exchange", analyst.info.get('exchange', 'N/A'))
                
                with col2:
                    market_cap = analyst.get('marketCap')
                    st.metric("Market Cap", f"${market_cap/1e9:.2f}B" if market_cap > 0 else "N/A")
                    st.metric("Sector", analyst.info.get('sector', 'N/A'))
                
                with col3:
                    current_price = analyst.get('currentPrice') or analyst.get('regularMarketPrice')
                    st.metric("Current Price", f"${current_price:.2f}" if current_price > 0 else "N/A")
                    st.metric("Industry", analyst.info.get('industry', 'N/A')[:20])
                
                with col4:
                    employees = analyst.info.get('fullTimeEmployees')
                    st.metric("Employees", f"{employees:,}" if employees else "N/A")
                    st.metric("Country", analyst.info.get('country', 'N/A'))
                
                st.markdown(f"**Company Name:** {analyst.info.get('longName', 'N/A')}")
                
                # Valuation Metrics
                st.header("2️⃣ Valuation Metrics")
                col1, col2 = st.columns(2)
                
                with col1:
                    pe = analyst.get('trailingPE')
                    benchmark_pe = analyst.benchmark['pe']
                    delta_pe = ((pe - benchmark_pe) / benchmark_pe * 100) if benchmark_pe > 0 and pe > 0 else 0
                    st.metric("P/E Ratio (Trailing)", f"{pe:.2f}" if pe > 0 else "N/A", 
                             f"{delta_pe:+.1f}% vs sector", delta_color="inverse")
                    
                    pb = analyst.get('priceToBook')
                    st.metric("Price/Book", f"{pb:.2f}" if pb > 0 else "N/A")
                    
                    peg = analyst.get('pegRatio')
                    st.metric("PEG Ratio", f"{peg:.2f}" if peg > 0 else "N/A")
                
                with col2:
                    fwd_pe = analyst.get('forwardPE')
                    st.metric("P/E Ratio (Forward)", f"{fwd_pe:.2f}" if fwd_pe > 0 else "N/A")
                    
                    ps = analyst.get('priceToSalesTrailing12Months')
                    st.metric("Price/Sales", f"{ps:.2f}" if ps > 0 else "N/A")
                    
                    ev_ebitda = analyst.get('enterpriseToEbitda')
                    st.metric("EV/EBITDA", f"{ev_ebitda:.2f}" if ev_ebitda > 0 else "N/A")
                
                # Valuation status
                if pe > 0 and benchmark_pe > 0:
                    ratio = pe / benchmark_pe
                    if ratio < 0.8:
                        st.success(f"✅ UNDERVALUED - P/E is {((1-ratio)*100):.0f}% below sector average")
                    elif ratio > 1.2:
                        st.error(f"⚠️ OVERVALUED - P/E is {((ratio-1)*100):.0f}% above sector average")
                    else:
                        st.info("➡️ FAIRLY VALUED")
                
                # Profitability
                st.header("3️⃣ Profitability & Efficiency")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    gross_margin = analyst.get('grossMargins') * 100
                    st.metric("Gross Margin", f"{gross_margin:.2f}%" if gross_margin > 0 else "N/A")
                
                with col2:
                    operating_margin = analyst.get('operatingMargins') * 100
                    st.metric("Operating Margin", f"{operating_margin:.2f}%" if operating_margin > 0 else "N/A")
                
                with col3:
                    profit_margin = analyst.get('profitMargins') * 100
                    benchmark_margin = analyst.benchmark['margin'] * 100
                    st.metric("Net Margin", f"{profit_margin:.2f}%" if profit_margin != 0 else "N/A",
                             f"{(profit_margin - benchmark_margin):+.1f}% vs sector")
                
                with col4:
                    roe = analyst.get('returnOnEquity') * 100
                    st.metric("ROE", f"{roe:.2f}%" if roe > 0 else "N/A")
                
                # Financial Health
                st.header("4️⃣ Financial Health & Leverage")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    de_ratio = analyst.get('debtToEquity') / 100.0 if analyst.get('debtToEquity') > 10 else analyst.get('debtToEquity')
                    st.metric("Debt-to-Equity", f"{de_ratio:.2f}" if de_ratio > 0 else "N/A")
                
                with col2:
                    current_ratio = analyst.get('currentRatio')
                    st.metric("Current Ratio", f"{current_ratio:.2f}" if current_ratio > 0 else "N/A")
                
                with col3:
                    quick_ratio = analyst.get('quickRatio')
                    st.metric("Quick Ratio", f"{quick_ratio:.2f}" if quick_ratio > 0 else "N/A")
                
                total_cash = analyst.get('totalCash')
                total_debt = analyst.get('totalDebt')
                if total_cash > 0 and total_debt > 0:
                    net_cash = total_cash - total_debt
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Cash", f"${total_cash/1e9:.2f}B")
                    with col2:
                        st.metric("Total Debt", f"${total_debt/1e9:.2f}B")
                    with col3:
                        st.metric("Net Cash", f"${net_cash/1e9:.2f}B", delta_color="normal" if net_cash > 0 else "inverse")
                
                # Growth Metrics
                st.header("5️⃣ Growth Metrics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    rev_growth = analyst.get('revenueGrowth') * 100
                    st.metric("Revenue Growth (YoY)", f"{rev_growth:+.2f}%" if rev_growth != 0 else "N/A",
                             delta_color="normal" if rev_growth > 0 else "inverse")
                
                with col2:
                    earnings_growth = analyst.get('earningsGrowth') * 100
                    st.metric("Earnings Growth (YoY)", f"{earnings_growth:+.2f}%" if earnings_growth != 0 else "N/A",
                             delta_color="normal" if earnings_growth > 0 else "inverse")
                
                with col3:
                    earnings_qtr = analyst.get('earningsQuarterlyGrowth') * 100
                    st.metric("Earnings Growth (QoQ)", f"{earnings_qtr:+.2f}%" if earnings_qtr != 0 else "N/A",
                             delta_color="normal" if earnings_qtr > 0 else "inverse")
                
                # Revenue Trend Chart
                if analyst.financials is not None and not analyst.financials.empty:
                    try:
                        if 'Total Revenue' in analyst.financials.index:
                            revenues = analyst.financials.loc['Total Revenue']
                            if len(revenues) >= 2:
                                fig = go.Figure()
                                fig.add_trace(go.Bar(
                                    x=[date.year for date in revenues.index[:4]],
                                    y=[rev/1e9 for rev in revenues.values[:4]],
                                    marker_color='#1f77b4'
                                ))
                                fig.update_layout(
                                    title="Revenue Trend (Last 4 Years)",
                                    xaxis_title="Year",
                                    yaxis_title="Revenue (Billions USD)",
                                    height=300
                                )
                                st.plotly_chart(fig, use_container_width=True)
                    except:
                        pass
                
                # Cash Flow Analysis
                st.header("6️⃣ Cash Flow Analysis")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    operating_cf = analyst.get('operatingCashflow')
                    st.metric("Operating Cash Flow", f"${operating_cf/1e9:.2f}B" if operating_cf > 0 else "N/A")
                
                with col2:
                    free_cf = analyst.get('freeCashflow')
                    st.metric("Free Cash Flow", f"${free_cf/1e9:.2f}B" if free_cf > 0 else "N/A")
                
                with col3:
                    if free_cf > 0:
                        market_cap = analyst.get('marketCap')
                        if market_cap > 0:
                            fcf_yield = (free_cf / market_cap) * 100
                            st.metric("FCF Yield", f"{fcf_yield:.2f}%")
                
                # Dividends
                st.header("7️⃣ Dividends & Shareholder Returns")
                div_yield = analyst.get('dividendYield')
                
                if div_yield > 0:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Dividend Yield", f"{div_yield*100:.2f}%")
                    with col2:
                        div_rate = analyst.get('dividendRate')
                        st.metric("Annual Dividend", f"${div_rate:.2f}")
                    with col3:
                        payout_ratio = analyst.get('payoutRatio') * 100
                        st.metric("Payout Ratio", f"{payout_ratio:.2f}%")
                else:
                    st.info("ℹ️ No dividend currently paid")
                
                # Risk Assessment
                st.header("8️⃣ Risk Assessment")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    beta = analyst.get('beta', 1.0)
                    st.metric("Beta (Volatility)", f"{beta:.2f}")
                
                with col2:
                    short_pct = analyst.get('shortPercentOfFloat') * 100
                    if short_pct > 0:
                        st.metric("Short % of Float", f"{short_pct:.2f}%")
                        if short_pct > 15:
                            st.warning("⚠️ High short interest detected!")
                
                with col3:
                    week52_high = analyst.get('fiftyTwoWeekHigh')
                    week52_low = analyst.get('fiftyTwoWeekLow')
                    if week52_high > 0 and week52_low > 0 and current_price > 0:
                        position = ((current_price - week52_low) / (week52_high - week52_low)) * 100
                        st.metric("52W Range Position", f"{position:.0f}%")
                
                # 52-Week Range Visualization
                if week52_high > 0 and week52_low > 0 and current_price > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Indicator(
                        mode="gauge+number+delta",
                        value=current_price,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "Current Price vs 52-Week Range"},
                        delta={'reference': week52_high},
                        gauge={
                            'axis': {'range': [week52_low, week52_high]},
                            'bar': {'color': "#1f77b4"},
                            'steps': [
                                {'range': [week52_low, week52_low + (week52_high-week52_low)*0.33], 'color': "lightgray"},
                                {'range': [week52_low + (week52_high-week52_low)*0.33, week52_low + (week52_high-week52_low)*0.66], 'color': "gray"}
                            ],
                        }
                    ))
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Analyst Consensus
                st.header("9️⃣ Wall Street Consensus")
                target_mean = analyst.get('targetMeanPrice')
                num_analysts = analyst.get('numberOfAnalystOpinions')
                recommendation = analyst.info.get('recommendationKey', 'N/A')
                
                if target_mean > 0 and current_price > 0:
                    upside = ((target_mean - current_price) / current_price) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Number of Analysts", f"{int(num_analysts)}")
                    with col2:
                        st.metric("Consensus Rating", recommendation.upper())
                    with col3:
                        st.metric("Mean Target Price", f"${target_mean:.2f}",
                                 f"{upside:+.2f}% upside", delta_color="normal" if upside > 0 else "inverse")
                else:
                    st.info("ℹ️ No analyst coverage available")
                
                # Quality Checks
                st.header("🔟 Quality Checks & Investment Score")
                
                red_flags = []
                green_flags = []
                
                if analyst.get('trailingEps') < 0:
                    red_flags.append("Company is not profitable (negative EPS)")
                else:
                    green_flags.append("Positive earnings")
                
                if de_ratio > 2.0:
                    red_flags.append(f"High leverage (D/E = {de_ratio:.2f})")
                elif de_ratio < 0.5:
                    green_flags.append("Low debt levels")
                
                if analyst.get('freeCashflow') < 0:
                    red_flags.append("Negative free cash flow")
                else:
                    green_flags.append("Positive free cash flow")
                
                if analyst.get('currentRatio') < 1.0:
                    red_flags.append(f"Liquidity concern (Current Ratio = {analyst.get('currentRatio'):.2f})")
                elif analyst.get('currentRatio') > 1.5:
                    green_flags.append("Strong liquidity position")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if green_flags:
                        st.success("✅ **STRENGTHS**")
                        for flag in green_flags:
                            st.write(f"• {flag}")
                
                with col2:
                    if red_flags:
                        st.error("⚠️ **RED FLAGS**")
                        for flag in red_flags:
                            st.write(f"• {flag}")
                
                # Investment Verdict
                score = analyst.calculate_score()
                
                if score >= 80:
                    rating = "STRONG BUY"
                    color = "green"
                elif score >= 60:
                    rating = "BUY"
                    color = "green"
                elif score >= 40:
                    rating = "HOLD"
                    color = "orange"
                elif score >= 20:
                    rating = "SELL"
                    color = "red"
                else:
                    rating = "STRONG SELL"
                    color = "red"
                
                st.markdown("---")
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=score,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "Fundamental Score"},
                        gauge={
                            'axis': {'range': [0, 100]},
                            'bar': {'color': color},
                            'steps': [
                                {'range': [0, 40], 'color': "lightgray"},
                                {'range': [40, 60], 'color': "gray"},
                                {'range': [60, 100], 'color': "lightgreen"}
                            ],
                        }
                    ))
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown(f"### Investment Rating: **:{color}[{rating}]**")
                    
                    if score >= 60:
                        st.success("""
                        ✅ **Strong Fundamentals**
                        
                        This stock shows strong fundamental characteristics and may be suitable 
                        for long-term investment consideration.
                        """)
                    elif score >= 40:
                        st.warning("""
                        ⚠️ **Mixed Signals**
                        
                        Consider holding if already invested, but proceed with caution 
                        if initiating a new position.
                        """)
                    else:
                        st.error("""
                        ❌ **Weak Fundamentals**
                        
                        This stock may not be suitable for conservative investors 
                        at current levels.
                        """)
                
                # Data Audit
                st.header("🔍 Data Audit Report")
                auditor = DataAuditor(analyst)
                audit_results = auditor.verify_all()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Checks", audit_results['total_checks'])
                with col2:
                    st.metric("Verified", audit_results['verified'])
                with col3:
                    st.metric("Warnings", audit_results['warnings'])
                with col4:
                    st.metric("Success Rate", f"{audit_results['success_rate']:.1f}%")
                
                if audit_results['success_rate'] >= 80:
                    st.success("✅ Data quality is excellent. Analysis is reliable.")
                elif audit_results['success_rate'] >= 60:
                    st.warning("⚠️ Data quality is acceptable but review warnings.")
                else:
                    st.error("❌ Data quality issues detected. Use with caution.")
                
                if audit_results['warning_list']:
                    with st.expander("⚠️ View Warnings"):
                        for warning in audit_results['warning_list']:
                            st.write(f"• {warning}")
                
                # Disclaimer
                st.markdown("---")
                st.caption("""
                **Disclaimer:** This analysis is for informational purposes only and does not constitute 
                financial advice. Always conduct your own research and consult with a qualified financial 
                advisor before making investment decisions.
                """)
                
            except Exception as e:
                st.error(f"❌ Error analyzing {ticker_input.upper()}: {str(e)}")
                st.info("Please verify the ticker symbol is correct and try again.")
    
    else:
        st.info("👈 Enter a ticker symbol in the sidebar and click 'Run Analysis' to begin.")
        
        # Example tickers
        st.markdown("### 💡 Try these popular tickers:")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**Tech**\n- AAPL\n- MSFT\n- GOOGL")
        with col2:
            st.markdown("**Finance**\n- JPM\n- BAC\n- GS")
        with col3:
            st.markdown("**Healthcare**\n- JNJ\n- PFE\n- UNH")
        with col4:
            st.markdown("**Consumer**\n- AMZN\n- WMT\n- NKE")

if __name__ == "__main__":
    main()
