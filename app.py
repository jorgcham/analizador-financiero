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
pesos_in = st.sidebar.text_input("Pesos (ej: 0.34, 0.33, 0.33)", "0.34, 0.33, 0.33")
capital = st.sidebar.number_input("Capital Inicial (€)", value=1000)
anos = st.sidebar.slider("Años atrás", 1, 10, 5)

if st.sidebar.button("Simular"):
    lista_tickers = [t.strip().upper() for t in tickers_in.split(",")]
    lista_pesos = [float(p.strip()) for p in pesos_in.split(",")]
    
    # Descarga de datos
    inicio = datetime.now() - timedelta(days=365 * anos)
    # Forzamos que los datos sean una tabla limpia
    datos = yf.download(lista_tickers, start=inicio, auto_adjust=True, progress=False)['Close']
    
    if len(lista_tickers) > 1:
        retornos = datos.pct_change().dropna()
        cartera_ret = (retornos * lista_pesos).sum(axis=1)
    else:
        cartera_ret = datos.pct_change().dropna()

    st.subheader(f"¿Cuánto tendrías hoy si hubieras invertido {capital}€?")
    
    # Tabla de resultados limpia
    hoy = datetime.now()
    periodos = {"1 Año": 365, "3 Años": 365*3, "5 Años": 365*5}
    resultados = []
    
    for nombre, dias in periodos.items():
        fecha_pasada = hoy - timedelta(days=dias)
        if fecha_pasada > inicio:
            try:
                # Cálculo robusto para evitar el error "nan"
                valor_final_total = 0
                for i, t in enumerate(lista_tickers):
                    serie_ticker = datos[t] if len(lista_tickers) > 1 else datos
                    p_actual = float(serie_ticker.iloc[-1])
                    p_pasado = float(serie_ticker.asof(fecha_pasada))
                    ret_individual = (p_actual - p_pasado) / p_pasado
                    valor_final_total += (capital * lista_pesos[i]) * (1 + ret_individual)
                
                rent_total_pct = ((valor_final_total / capital) - 1) * 100
                
                resultados.append({
                    "Periodo": nombre,
                    "Rentabilidad (%)": f"{rent_total_pct:.2f}%",
                    "Dinero Final": f"{valor_final_total:.2f}€"
                })
            except:
                continue
    
    st.table(pd.DataFrame(resultados))

    # Gráfico corregido para evitar el error rojo
    st.subheader("Evolución de la inversión")
    # Convertimos a serie de tiempo limpia para QuantStats
    cartera_ret.index = pd.to_datetime(cartera_ret.index)
    fig = qs.plots.returns(cartera_ret, output=None, show=False)
    st.pyplot(fig)
