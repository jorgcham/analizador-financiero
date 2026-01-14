import streamlit as st
import yfinance as yf
import pandas as pd
import quantstats as qs
from datetime import datetime, timedelta

st.set_page_config(page_title="Analizador Pro", layout="wide")
st.title("📈 Mi Simulador de Inversiones vs Mercado")

# Barra lateral
st.sidebar.header("Tu Cartera")
tickers_in = st.sidebar.text_input("Empresas (ej: AAPL, MSFT, GLD)", "AAPL, MSFT, GLD")
pesos_in = st.sidebar.text_input("Pesos (ej: 0.34, 0.33, 0.33)", "0.34, 0.33, 0.33")
capital = st.sidebar.number_input("Inversión Inicial (€)", value=1000)
anos = st.sidebar.slider("Años atrás", 1, 10, 6)

# Añadimos un benchmark (S&P 500)
benchmark = "SPY"

if st.sidebar.button("Simular e Imprimir Gráficos"):
    lista_tickers = [t.strip().upper() for t in tickers_in.split(",")]
    lista_pesos = [float(p.strip()) for p in pesos_in.split(",")]
    
    inicio = datetime.now() - timedelta(days=365 * anos)
    # Descargamos tus activos + el mercado (SPY)
    todos = lista_tickers + [benchmark]
    datos = yf.download(todos, start=inicio, auto_adjust=True, progress=False)['Close']
    
    # Preparamos retornos
    retornos = datos.pct_change().dropna()
    cartera_ret = (retornos[lista_tickers] * lista_pesos).sum(axis=1)
    bench_ret = retornos[benchmark]

    st.subheader(f"Resultado de invertir {capital}€ frente al S&P 500")
    
    hoy = datetime.now()
    periodos = {"1 Año": 365, "3 Años": 365*3, "5 Años": 365*5}
    res_data = []
    
    for nombre, dias in periodos.items():
        f_pasada = hoy - timedelta(days=dias)
        if f_pasada > inicio:
            # Tu cartera
            v_final_c = 0
            v_final_b = capital * (1 + ( (datos[benchmark].iloc[-1] - datos[benchmark].asof(f_pasada)) / datos[benchmark].asof(f_pasada) ))
            
            for i, t in enumerate(lista_tickers):
                p_act = float(datos[t].iloc[-1])
                p_pas = float(datos[t].asof(f_pasada))
                v_final_c += (capital * lista_pesos[i]) * (p_act / p_pas)
            
            res_data.append({
                "Periodo": nombre,
                "Tu Cartera (€)": f"{v_final_c:.2f}€",
                "S&P 500 (€)": f"{v_final_b:.2f}€",
                "Diferencia": f"{v_final_c - v_final_b:.2f}€"
            })
    
    st.table(pd.DataFrame(res_data))

    # GRÁFICO PROFESIONAL SIN ERRORES
    st.subheader("Gráfico Comparativo: Tu Cartera vs Mercado")
    # Limpieza de datos para el gráfico
    cartera_ret.index = pd.to_datetime(cartera_ret.index).tz_localize(None)
    bench_ret.index = pd.to_datetime(bench_ret.index).tz_localize(None)
    
    fig = qs.plots.returns(cartera_ret, bench_ret, output=None, show=False)
    st.pyplot(fig)
