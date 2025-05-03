import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# === Configurações iniciais ===
st.set_page_config(layout="wide", page_title="Gráfico de Médias Móveis", page_icon="📈")
st.title("Visualizador de Séries Temporais - Médias Móveis")

# === URL pública do Parquet no Azure ===
URL_PARQUET = "https://auraprodstorage.blob.core.windows.net/public-parquet/consolidado.parquet"

# === Função de carregamento com cache ===
@st.cache_data
def carregar_dados():
    df = pd.read_parquet(URL_PARQUET, engine="pyarrow")
    df["DataHoraReal"] = pd.to_datetime(df["DataHoraReal"])
    return df

# === Carregar dados ===
df = carregar_dados()

# === Sidebar: filtros ===
st.sidebar.header("Configurações")

# Fontes disponíveis
fontes_disponiveis = sorted(df["Fonte"].unique())
fontes_selecionadas = st.sidebar.multiselect(
    "Selecione as fontes:",
    options=fontes_disponiveis,
    default=fontes_disponiveis
)

# Período padrão: últimos 30 dias
data_max = df["DataHoraReal"].max()
data_min = data_max - pd.Timedelta(days=30)
inicio, fim = st.sidebar.date_input("Período:", [data_min.date(), data_max.date()])

# Média móvel
periodo_movel = st.sidebar.slider("Período da Média Móvel:", 1, 50, 6, 1)

# Gráfico único ou separado
grafico_unico = st.sidebar.checkbox("Exibir em um único gráfico", value=True)

# === Aplicar filtros ===
df_filtrado = df[
    (df["Fonte"].isin(fontes_selecionadas)) &
    (df["DataHoraReal"].dt.date >= inicio) &
    (df["DataHoraReal"].dt.date <= fim)
].copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado no período selecionado.")
    st.stop()

# Calcular média móvel por grupo
df_filtrado["MediaMovel"] = df_filtrado.groupby("Fonte")["Valor"].transform(
    lambda x: x.rolling(window=periodo_movel, min_periods=1).mean()
)

# === Exibir gráfico ===
if grafico_unico:
    fig = go.Figure()
    for fonte in fontes_selecionadas:
        dados_fonte = df_filtrado[df_filtrado["Fonte"] == fonte]
        fig.add_trace(go.Scatter(
            x=dados_fonte["DataHoraReal"],
            y=dados_fonte["MediaMovel"],
            mode="lines",
            name=fonte
        ))
    fig.update_layout(
        title=f"Médias Móveis - {periodo_movel} períodos",
        xaxis_title="Data e Hora",
        yaxis_title="Valor",
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    for fonte in fontes_selecionadas:
        dados_fonte = df_filtrado[df_filtrado["Fonte"] == fonte]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dados_fonte["DataHoraReal"],
            y=dados_fonte["Valor"],
            mode="markers",
            name="Bruto",
            marker=dict(size=4, color="lightgray")
        ))
        fig.add_trace(go.Scatter(
            x=dados_fonte["DataHoraReal"],
            y=dados_fonte["MediaMovel"],
            mode="lines",
            name="Média Móvel"
        ))
        fig.update_layout(
            title=fonte,
            xaxis_title="Data e Hora",
            yaxis_title="Valor",
            height=500
        )
        st.subheader(fonte)
        st.plotly_chart(fig, use_container_width=True)
