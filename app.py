import streamlit as st
import yfinance as yf
import pandas as pd
import quantstats as qs
from datetime import datetime, timedelta

st.set_page_config(page_title="Simulador de Inversión Personal", layout="wide")
st.title("🚀 Simulador de Inversión Histórica")

# --- BARRA LATERAL: CONFIGURACIÓN ---
st.sidebar.header("Parámetros de la Simulación")

tickers_in = st.sidebar.text_input("Símbolos (ej: AAPL, MSFT, TSLA, GLD)", "AAPL, MSFT, GLD")
pesos_in = st.sidebar.text_input("Pesos (deben sumar 1.0. Ej: 0.4, 0.4, 0.2)", "0.34, 0.33, 0.33")
capital = st.sidebar.number_input("Cantidad invertida (€)", value=1000)

# NUEVO: Selección de Fechas
st.sidebar.subheader("Periodo de Análisis")
fecha_inicio = st.sidebar.date_input("Fecha de Inicio", datetime.now() - timedelta(days=365*5))
fecha_fin = st.sidebar.date_input("Fecha de Fin", datetime.now())

benchmark = "SPY" # S&P 500 para comparar

if st.sidebar.button("Ejecutar Simulación"):
    try:
        # 1. Procesar Tickers y Pesos
        lista_tickers = [t.strip().upper() for t in tickers_in.split(",")]
        lista_pesos = [float(p.strip()) for p in pesos_in.split(",")]
        
        if abs(sum(lista_pesos) - 1.0) > 0.01:
            st.error("⚠️ Los pesos deben sumar 1.0 exactos.")
        else:
            # 2. Descargar Datos
            todos = lista_tickers + [benchmark]
            datos = yf.download(todos, start=fecha_inicio, end=fecha_fin, auto_adjust=True, progress=False)['Close']
            
            # Limpiar datos: Quitar zonas horarias para evitar el error TypeError
            datos.index = datos.index.tz_localize(None)
            
            # 3. Calcular Retornos
            retornos = datos.pct_change().dropna()
            
            # Calculamos retorno de tu cartera
            cartera_ret = (retornos[lista_tickers] * lista_pesos).sum(axis=1)
            # Calculamos retorno del S&P 500
            bench_ret = retornos[benchmark]

            # --- RESULTADOS NUMÉRICOS ---
            st.subheader(f"Análisis desde {fecha_inicio} hasta {fecha_fin}")
            
            # Valor final de tu dinero
            v_final_cartera = capital * (1 + (cartera_ret + 1).prod() - 1)
            v_final_bench = capital * (1 + (bench_ret + 1).prod() - 1)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Tu Cartera", f"{v_final_cartera:,.2f}€", f"{((v_final_cartera/capital)-1)*100:.2f}%")
            col2.metric("S&P 500 (Mercado)", f"{v_final_bench:,.2f}€", f"{((v_final_bench/capital)-1)*100:.2f}%")
            col3.metric("Diferencia Ganada", f"{v_final_cartera - v_final_bench:,.2f}€")

            # --- GRÁFICOS ---
            st.subheader("📈 Evolución de 1€ invertido")
            # Esto crea el gráfico comparativo profesional
            fig = qs.plots.returns(cartera_ret, bench_ret, output=None, show=False)
            st.pyplot(fig)
            
            st.subheader("📉 Periodos de Caída (Drawdown)")
            fig_drawdown = qs.plots.drawdown(cartera_ret, output=None, show=False)
            st.pyplot(fig_drawdown)

    except Exception as e:
        st.error(f"Hubo un error con los símbolos o las fechas. Asegúrate de que los tickers existen. Error: {e}")
