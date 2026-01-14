import streamlit as st
import yfinance as yf
import pandas as pd
import quantstats as qs
from datetime import datetime, timedelta

st.set_page_config(page_title="Analizador Financiero", layout="wide")
st.title("📈 Mi Simulador de Inversiones")

# Barra lateral
st.sidebar.header("Tu Cartera")
tickers_in = st.sidebar.text_input("Empresas (separadas por coma)", "AAPL, MSFT, GLD")
pesos_in = st.sidebar.text_input("Pesos (ej: 0.5, 0.3, 0.2)", "0.34, 0.33, 0.33")
capital = st.sidebar.number_input("Capital Inicial (€)", value=1000)
anos = st.sidebar.slider("Años atrás", 1, 10, 5)

if st.sidebar.button("Simular"):
    lista_tickers = [t.strip().upper() for t in tickers_in.split(",")]
    lista_pesos = [float(p.strip()) for p in pesos_in.split(",")]
    
    inicio = datetime.now() - timedelta(days=365 * anos)
    datos = yf.download(lista_tickers, start=inicio, auto_adjust=True, progress=False)['Close']
    
    retornos = datos.pct_change().dropna()
    cartera_ret = (retornos * lista_pesos).sum(axis=1)
    
    st.subheader(f"¿Cuánto tendrías hoy si hubieras invertido {capital}€?")
    hoy = datetime.now()
    periodos = {"1 Año": 365, "3 Años": 365*3, "5 Años": 365*5}
    resultados = []
    
    for nombre, dias in periodos.items():
        fecha_pasada = hoy - timedelta(days=dias)
        if fecha_pasada > inicio:
            ret_total = 0
            for i, t in enumerate(lista_tickers):
                p_actual = float(datos[t].iloc[-1])
                p_pasado = float(datos[t].asof(fecha_pasada))
                ret_total += ((p_actual - p_pasado) / p_pasado) * lista_pesos[i]
            
            resultados.append({
                "Periodo": nombre,
                "Rentabilidad (%)": f"{ret_total*100:.2f}%",
                "Dinero Final": f"{capital * (1 + ret_total):.2f}€"
            })
    
    st.table(pd.DataFrame(resultados))
    st.subheader("Evolución de la inversión")
    fig = qs.plots.returns(cartera_ret, output=None, show=False)
    st.pyplot(fig)
