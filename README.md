# 🍕 Pizza on Mondays

Dashboard interactivo en Streamlit para explorar el comportamiento histórico de distintos sectores (Oil & Gas, Real Estate, Criptomonedas) y simular una cartera simple sobre ellos.

**App en vivo:** https://pizzaonmondays.streamlit.app/

## ¿Qué hace?

- Descarga precios históricos por sector con [yfinance](https://github.com/ranaroussi/yfinance).
- Calcula retornos diarios, retornos acumulados y volatilidad rolling.
- Muestra un resumen por activo (retorno total/anualizado, volatilidad, Sharpe aproximado, máximo drawdown, momentum reciente) y una recomendación descriptiva a partir de esas métricas.
- Simula la evolución de un capital inicial invertido en cada activo y en una cartera ponderada.
- Permite comparar la dispersión entre activos seleccionados.

> ⚠️ Todo lo que muestra la app es una lectura descriptiva de datos históricos, no asesoramiento financiero.

## Código y resultado en la app

Recorrido por cada bloque de [`app.py`](src/pizza_on_mondays/app.py) y qué produce en https://pizzaonmondays.streamlit.app/

### 1. Selección de sector y rango de fechas

```python
sector_name = st.selectbox(
    "Sector",
    list(SECTORS.keys()),
    format_func=lambda name: f"{SECTOR_ICONS.get(name, '')} {name}",
)
sector = SECTORS[sector_name]

start = col1.date_input("Desde", value=pd.Timestamp(sector["start"]), key=f"start_{sector_name}")
end = col2.date_input("Hasta", value=pd.Timestamp(sector["end"]), key=f"end_{sector_name}")
```

**En la app:** un desplegable para elegir entre *Oil & Gas* 🛢️, *Real Estate* 🏢 o *Criptomonedas*, y dos selectores de fecha lado a lado para acotar el período de análisis.

### 2. Descarga y limpieza de retornos

```python
@st.cache_data
def load_returns(tickers, start, end):
    data = yf.download(tickers, start=start, end=end)["Close"]
    data = data.ffill().bfill()
    return data.pct_change().dropna()
```

**En la app:** no se ve directamente — es el paso que trae los precios desde Yahoo Finance y calcula los retornos diarios que alimentan todo lo demás. Está cacheado (`@st.cache_data`) para no re-descargar en cada interacción.

### 3. Resumen y recomendación

```python
summary = build_summary(returns)
st.dataframe(summary.style.format({...}))
st.markdown(build_recommendation(summary))
```

**En la app:** una tabla con, por cada ticker, retorno total, retorno anualizado, volatilidad anualizada, Sharpe aproximado, máximo drawdown y momentum reciente — ordenada de mejor a peor Sharpe. Justo debajo, una lista en texto (viñetas) que destaca el mejor Sharpe, el mejor y peor momentum, el activo más volátil y el peor drawdown del período.

### 4. Retornos diarios y estadísticas

```python
st.dataframe(returns)
st.dataframe(returns.describe())
```

**En la app:** una tabla con los retornos diarios crudos de cada ticker, seguida de las estadísticas descriptivas estándar de pandas (media, desvío, mínimo, máximo, cuartiles).

### 5. Retornos acumulados

```python
st.line_chart((1 + returns).cumprod())
```

**En la app:** un gráfico de líneas con la evolución acumulada de cada activo a lo largo del período (base 1 = capital inicial normalizado).

### 6. Simulación de payoff

```python
initial_capital = st.number_input("Capital inicial", min_value=1.0, value=10_000.0, step=500.0)
payoff, portfolio_returns = simulate_payoff(returns, initial_capital)
st.line_chart(payoff)
st.dataframe(payoff_metrics(portfolio_returns).to_frame("Cartera").style.format("{:.2%}"))
```

**En la app:** un campo para ingresar el capital inicial, un gráfico de líneas mostrando cómo hubiera evolucionado ese capital en cada activo y en una cartera equiponderada ("Cartera"), y una tabla con retorno anualizado, Sharpe y máximo drawdown de esa cartera (vía QuantStats).

### 7. Volatilidad rolling

```python
st.line_chart(returns.rolling(21).std() * (252 ** 0.5))
```

**En la app:** un gráfico de líneas con la volatilidad anualizada calculada en ventanas móviles de 21 días hábiles (~1 mes), por activo.

### 8. Dispersión entre activos

```python
tickers = st.multiselect("Tickers a comparar", options=list(returns.columns), default=list(returns.columns[:4]))
if len(tickers) >= 2:
    fig = sns.pairplot(returns[tickers], kind="scatter", plot_kws={"alpha": 0.5})
    st.pyplot(fig.figure)
```

**En la app:** un selector múltiple de tickers y, al elegir dos o más, una matriz de gráficos de dispersión (pairplot de seaborn) mostrando cómo se relacionan los retornos diarios entre esos activos.

## Cómo correrlo localmente

Requiere Python 3.12+ y [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run streamlit run src/pizza_on_mondays/app.py
```

## Estructura del proyecto

```
src/pizza_on_mondays/
├── __init__.py
└── app.py          # app de Streamlit (lógica y UI)
notebooks/
└── ideas.ipynb      # exploración y prototipos
```
