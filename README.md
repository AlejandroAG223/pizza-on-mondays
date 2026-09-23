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
