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
}

SECTOR_ICONS = {
    "Oil & Gas": "🛢️",
    "Real Estate": "🏢",
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


if __name__ == "__main__":
    main()
