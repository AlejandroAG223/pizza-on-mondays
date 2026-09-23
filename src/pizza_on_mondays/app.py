import pandas as pd
import seaborn as sns
import streamlit as st
import yfinance as yf

SECTORS = {
    "Oil & Gas": {
        "stocks": ["BP", "CVX", "EC", "SHEL", "SU", "TTE", "XOM"],
        "start": "2020-01-01",
        "end": "2026-12-31",
    },
    "Real Estate": {
        "stocks": [
            "ADC", "AKR", "BRX", "EPRT", "FCPT", "KIM", "KRG", "MAC", "NNN",
            "O", "PECO", "REG", "UE",
        ],
        "start": "2026-01-01",
        "end": "2026-12-31",
    },
    "Criptomonedas": {
        "stocks": ["BTC-USD", "DOGE-USD", "ZEC-USD"],
        "start": "2020-01-01",
        "end": "2026-12-31",
    },
}

SECTOR_ICONS = {
    "Oil & Gas": "🛢️",
    "Real Estate": "🏢",
    "Criptomonedas": "🪙",
}

TITLE_COLOR = "#87CEFA"  # azul claro


def colored_title(text: str) -> None:
    st.markdown(f"<h1 style='color:{TITLE_COLOR}'>{text}</h1>", unsafe_allow_html=True)


def colored_subheader(text: str) -> None:
    st.markdown(f"<h3 style='color:{TITLE_COLOR}'>{text}</h3>", unsafe_allow_html=True)


@st.cache_data
def load_returns(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    data = yf.download(tickers, start=start, end=end)["Close"]
    data = data.ffill()  # NO miedo
    data = data.bfill()  # miedo te crea un lookahead bias
    return data.pct_change().dropna()


def build_summary(returns: pd.DataFrame, momentum_window: int = 21) -> pd.DataFrame:
    """Resume, por activo, los datos más relevantes del período seleccionado."""
    cumulative = (1 + returns).cumprod()
    n_days = len(returns)

    total_return = cumulative.iloc[-1] - 1
    annualized_return = (1 + total_return) ** (252 / n_days) - 1 if n_days > 0 else 0
    annualized_vol = returns.std() * (252 ** 0.5)
    sharpe = annualized_return / annualized_vol.replace(0, pd.NA)

    running_max = cumulative.cummax()
    max_drawdown = (cumulative / running_max - 1).min()

    momentum = (
        (1 + returns.tail(momentum_window)).prod() - 1
        if n_days >= 1
        else pd.Series(0, index=returns.columns)
    )

    summary = pd.DataFrame(
        {
            "Retorno total": total_return,
            "Retorno anualizado": annualized_return,
            "Volatilidad anualizada": annualized_vol,
            "Sharpe (aprox., rf=0)": sharpe,
            "Máx. drawdown": max_drawdown,
            f"Momentum últimos {momentum_window}d": momentum,
        }
    )
    return summary.sort_values("Sharpe (aprox., rf=0)", ascending=False)


def build_recommendation(summary: pd.DataFrame, momentum_window: int = 21) -> str:
    """Genera una nota descriptiva a tener en cuenta, en base a métricas históricas.

    No es asesoramiento financiero: es una lectura rápida de los datos del período
    para usar como punto de partida antes de decidir un movimiento.
    """
    if summary.empty:
        return "No hay datos suficientes en el período seleccionado para generar una recomendación."

    momentum_col = f"Momentum últimos {momentum_window}d"

    best_sharpe = summary["Sharpe (aprox., rf=0)"].idxmax()
    best_momentum = summary[momentum_col].idxmax()
    worst_momentum = summary[momentum_col].idxmin()
    most_volatile = summary["Volatilidad anualizada"].idxmax()
    worst_drawdown = summary["Máx. drawdown"].idxmin()

    lines = [
        f"- **{best_sharpe}** muestra la mejor relación retorno/riesgo del período "
        f"(Sharpe aprox. {summary.loc[best_sharpe, 'Sharpe (aprox., rf=0)']:.2f}), "
        "un candidato a mirar si se busca eficiencia riesgo-retorno.",
        f"- **{best_momentum}** tiene el mejor impulso reciente "
        f"({summary.loc[best_momentum, momentum_col]:+.1%} en los últimos {momentum_window} días hábiles), "
        "lo que podría indicar una tendencia a favor a seguir de cerca.",
        f"- **{worst_momentum}** muestra el impulso más débil "
        f"({summary.loc[worst_momentum, momentum_col]:+.1%} en el mismo período), "
        "vale la pena entender qué lo está frenando antes de sumar exposición.",
        f"- **{most_volatile}** presenta la mayor volatilidad anualizada "
        f"({summary.loc[most_volatile, 'Volatilidad anualizada']:.1%}), por lo que conviene "
        "dimensionar cualquier posición con cautela.",
        f"- **{worst_drawdown}** tuvo la caída máxima más pronunciada del período "
        f"({summary.loc[worst_drawdown, 'Máx. drawdown']:.1%}), un dato clave para el manejo de riesgo.",
    ]
    return "\n".join(lines)


@st.cache_data(ttl=3600)
def load_fundamentals(ticker: str) -> tuple[dict, pd.DataFrame]:
    """Trae el perfil (`info`) y un resumen anual de estados financieros de yfinance."""
    t = yf.Ticker(ticker)
    try:
        info = t.info or {}
    except Exception:
        info = {}

    rows = {
        "Ingresos": (t.income_stmt, "Total Revenue"),
        "Utilidad neta": (t.income_stmt, "Net Income"),
        "EBITDA": (t.income_stmt, "EBITDA"),
        "Free cash flow": (t.cashflow, "Free Cash Flow"),
    }
    financials = {}
    for label, (statement, row) in rows.items():
        if statement is not None and row in statement.index:
            financials[label] = statement.loc[row]
    financials = pd.DataFrame(financials)
    if not financials.empty:
        financials.index = pd.to_datetime(financials.index).year
        financials = financials.sort_index().dropna(how="all")
    return info, financials


def fmt_money(value, currency: str = "USD") -> str:
    if value is None or pd.isna(value):
        return "N/D"
    for size, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= size:
            return f"{value / size:,.2f} {suffix} {currency}"
    return f"{value:,.0f} {currency}"


def fmt_num(value, pattern: str = "{:.2f}") -> str:
    return "N/D" if value is None or pd.isna(value) else pattern.format(value)


def build_company_description(info: dict) -> str:
    """Arma una descripción en texto a partir de los fundamentals de yfinance."""
    name = info.get("longName") or info.get("shortName") or info.get("symbol")
    currency = info.get("currency", "USD")

    location = ", ".join(p for p in (info.get("city"), info.get("country")) if p)
    intro = f"**{name}** ({info.get('symbol')})"
    if info.get("sector"):
        intro += f" opera en el sector **{info['sector']}**"
        if info.get("industry"):
            intro += f", industria **{info['industry']}**"
    if location:
        intro += f", con sede en {location}"
    if info.get("fullTimeEmployees"):
        intro += f" y cerca de {info['fullTimeEmployees']:,} empleados"
    lines = [intro + "."]

    market_cap = info.get("marketCap")
    if market_cap:
        size = (
            "mega cap" if market_cap >= 200e9
            else "large cap" if market_cap >= 10e9
            else "mid cap" if market_cap >= 2e9
            else "small cap"
        )
        lines.append(
            f"- **Tamaño:** capitalización de {fmt_money(market_cap, currency)} ({size})."
        )

    pe = info.get("trailingPE")
    fpe = info.get("forwardPE")
    if pe:
        view = "exigente" if pe > 30 else "moderada" if pe > 15 else "baja"
        text = f"- **Valoración:** P/E de {pe:.1f}x (valoración {view})"
        if fpe:
            trend = "crecimiento" if fpe < pe else "caída"
            text += f"; el P/E forward de {fpe:.1f}x sugiere que el mercado espera {trend} de utilidades"
        lines.append(text + ".")

    margin = info.get("profitMargins")
    roe = info.get("returnOnEquity")
    if margin is not None or roe is not None:
        parts = []
        if margin is not None:
            parts.append(f"margen neto de {margin:.1%}")
        if roe is not None:
            quality = "alto" if roe > 0.15 else "razonable" if roe > 0.08 else "bajo"
            parts.append(f"ROE de {roe:.1%} ({quality})")
        lines.append(f"- **Rentabilidad:** {' y '.join(parts)}.")

    growth = info.get("revenueGrowth")
    if growth is not None:
        lines.append(f"- **Crecimiento:** los ingresos variaron {growth:+.1%} interanual.")

    de = info.get("debtToEquity")
    cr = info.get("currentRatio")
    if de is not None or cr is not None:
        parts = []
        if de is not None:
            level = "elevado" if de > 150 else "moderado" if de > 50 else "bajo"
            parts.append(f"deuda/patrimonio de {de / 100:.2f}x (endeudamiento {level})")
        if cr is not None:
            liquidity = "holgada" if cr >= 1.5 else "ajustada" if cr >= 1 else "débil"
            parts.append(f"current ratio de {cr:.2f} (liquidez {liquidity})")
        lines.append(f"- **Salud financiera:** {' y '.join(parts)}.")

    dy = info.get("dividendYield")
    if dy:
        lines.append(f"- **Dividendos:** rendimiento de {dy:.2f}% anual.")

    beta = info.get("beta")
    if beta is not None:
        view = "más volátil" if beta > 1.2 else "menos volátil" if beta < 0.8 else "similar"
        lines.append(f"- **Riesgo de mercado:** beta de {beta:.2f} ({view} que el mercado).")

    target = info.get("targetMeanPrice")
    price = info.get("currentPrice")
    if target and price:
        lines.append(
            f"- **Analistas:** consenso *{info.get('recommendationKey', 'N/D')}*, precio objetivo "
            f"promedio {target:,.2f} {currency} ({target / price - 1:+.1%} vs. precio actual)."
        )
    return "\n".join(lines)


def render_company_descriptor() -> None:
    colored_subheader("🔎 Descriptor de empresas")
    ticker = st.text_input(
        "Ticker de la acción (ej. AAPL, XOM, O)", key="descriptor_ticker"
    ).strip().upper()
    if not ticker:
        return

    with st.spinner(f"Buscando fundamentals de {ticker}..."):
        info, financials = load_fundamentals(ticker)

    if not (info.get("longName") or info.get("shortName")):
        st.warning(f"No se encontró información para **{ticker}**. Revisá el ticker.")
        return

    if info.get("quoteType") not in (None, "EQUITY"):
        st.info(
            f"{ticker} es de tipo {info.get('quoteType')}: no tiene fundamentals de empresa, "
            "solo se muestra el perfil básico."
        )

    st.markdown(build_company_description(info))

    currency = info.get("currency", "USD")
    cols = st.columns(4)
    cols[0].metric("Market cap", fmt_money(info.get("marketCap"), currency))
    cols[1].metric("P/E (trailing)", fmt_num(info.get("trailingPE"), "{:.1f}x"))
    cols[2].metric("P/B", fmt_num(info.get("priceToBook"), "{:.2f}x"))
    cols[3].metric("EV/EBITDA", fmt_num(info.get("enterpriseToEbitda"), "{:.1f}x"))
    cols = st.columns(4)
    cols[0].metric("Margen neto", fmt_num(info.get("profitMargins"), "{:.1%}"))
    cols[1].metric("ROE", fmt_num(info.get("returnOnEquity"), "{:.1%}"))
    cols[2].metric("Dividend yield", fmt_num(info.get("dividendYield"), "{:.2f}%"))
    cols[3].metric("Beta", fmt_num(info.get("beta")))

    if info.get("longBusinessSummary"):
        with st.expander("Descripción del negocio (Yahoo Finance)"):
            st.write(info["longBusinessSummary"])
            if info.get("website"):
                st.markdown(f"🌐 {info['website']}")

    if not financials.empty:
        st.markdown(f"**Estados financieros anuales ({currency})**")
        st.bar_chart(financials[[c for c in ("Ingresos", "Utilidad neta") if c in financials]])
        st.dataframe(financials.T.style.format(lambda v: fmt_money(v, "")))


def main() -> None:
    st.set_page_config(page_title="Pizza on Mondays", layout="wide")
    colored_title("🍕 Pizza on Mondays")

    sector_name = st.selectbox(
        "Sector",
        list(SECTORS.keys()),
        format_func=lambda name: f"{SECTOR_ICONS.get(name, '')} {name}",
    )
    sector = SECTORS[sector_name]

    colored_subheader(f"{SECTOR_ICONS.get(sector_name, '')} {sector_name}")

    col1, col2 = st.columns(2)
    start = col1.date_input(
        "Desde", value=pd.Timestamp(sector["start"]), key=f"start_{sector_name}"
    )
    end = col2.date_input(
        "Hasta", value=pd.Timestamp(sector["end"]), key=f"end_{sector_name}"
    )

    returns = load_returns(sector["stocks"], str(start), str(end))

    colored_subheader("📌 Resumen y recomendación")
    summary = build_summary(returns)
    st.dataframe(
        summary.style.format(
            {
                "Retorno total": "{:.1%}",
                "Retorno anualizado": "{:.1%}",
                "Volatilidad anualizada": "{:.1%}",
                "Sharpe (aprox., rf=0)": "{:.2f}",
                "Máx. drawdown": "{:.1%}",
                summary.columns[-1]: "{:+.1%}",
            }
        )
    )
    st.markdown(build_recommendation(summary))
    st.caption(
        "⚠️ Esto es una lectura descriptiva de datos históricos, no una recomendación "
        "de inversión. Cualquier decisión debe considerar el contexto macro, los "
        "fundamentals de cada compañía y tu propio perfil de riesgo."
    )

    colored_subheader("Retornos diarios")
    st.dataframe(returns)

    colored_subheader("Estadísticas")
    st.dataframe(returns.describe())

    colored_subheader("Retornos acumulados")
    st.line_chart((1 + returns).cumprod())

    colored_subheader("Volatilidad (rolling 21 días, anualizada)")
    st.line_chart(returns.rolling(21).std() * (252 ** 0.5))

    colored_subheader("Dispersión entre activos")
    tickers = st.multiselect(
        "Tickers a comparar",
        options=list(returns.columns),
        default=list(returns.columns[:4]),
        key=f"tickers_{sector_name}",
    )
    if len(tickers) >= 2:
        fig = sns.pairplot(returns[tickers], kind="scatter", plot_kws={"alpha": 0.5})
        st.pyplot(fig.figure)
    else:
        st.info("Elegí al menos dos tickers para ver la dispersión.")

    render_company_descriptor()


if __name__ == "__main__":
    main()
