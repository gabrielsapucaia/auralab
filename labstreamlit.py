import streamlit as st   
import pandas as pd   
import plotly.graph_objects as go   
import hashlib
import requests

# === Configurações iniciais ===   
st.set_page_config(layout="wide", page_title="Gráfico de Médias Móveis", page_icon="📈")   
st.title("Visualizador de Séries Temporais - Médias Móveis")   
   
# === URL pública do Parquet no Azure ===
URL_PARQUET = "https://auraprodstorage.blob.core.windows.net/public-parquet/consolidado.parquet"

# === Botão na sidebar para recarregar dados manualmente ===
if st.sidebar.button("🔁 Recarregar Dados"):
    st.cache_data.clear()
    st.session_state.hash_parquet = None
    st.toast("📦 Dados recarregados manualmente!")

# === Verificar alteração do conteúdo do Parquet pela hash ===
def get_remote_hash(url):
    response = requests.get(url)
    if response.status_code != 200:
        return None
    return hashlib.md5(response.content).hexdigest()

# Calcular hash e comparar com a anterior
novo_hash = get_remote_hash(URL_PARQUET)
hash_antigo = st.session_state.get("hash_parquet")

if novo_hash and novo_hash != hash_antigo:
    st.cache_data.clear()
    st.session_state.hash_parquet = novo_hash
    st.toast("🆕 Novo conteúdo detectado e carregado!")

# === Função de carregamento com cache com TTL de 10 min ===
@st.cache_data(ttl=600)
def carregar_dados():
    df = pd.read_parquet(URL_PARQUET, engine="pyarrow")
    df["DataHoraReal"] = pd.to_datetime(df["DataHoraReal"])
    return df

# === Carregar todos os dados ===
df = carregar_dados()

# === Obter intervalo total e definir últimos 30 dias como padrão ===
data_max = df["DataHoraReal"].max()
data_min_total = df["DataHoraReal"].min()
data_min_default = data_max - pd.Timedelta(days=30)

# === Inicializar session_state se necessário ===
if "fontes" not in st.session_state:
    st.session_state.fontes = sorted(df["Fonte"].unique())
if "periodo" not in st.session_state:
    st.session_state.periodo = [data_min_default.date(), data_max.date()]
if "periodo_movel" not in st.session_state:
    st.session_state.periodo_movel = 6
if "grafico_unico" not in st.session_state:
    st.session_state.grafico_unico = True

# === Sidebar: controles ===
st.sidebar.header("Configurações")

# Botão de reset
if st.sidebar.button("🔄 Resetar Filtros"):
    st.session_state.fontes = sorted(df["Fonte"].unique())
    st.session_state.periodo = [data_min_default.date(), data_max.date()]
    st.session_state.periodo_movel = 6
    st.session_state.grafico_unico = True

# Widgets com valores controlados por session_state
fontes_selecionadas = st.sidebar.multiselect(
    "Selecione as fontes:",
    options=sorted(df["Fonte"].unique()),
    default=st.session_state.fontes,
    key="fontes"
)

periodo = st.sidebar.date_input(
    "Período:",
    value=st.session_state.periodo,
    min_value=data_min_total.date(),
    max_value=data_max.date(),
    key="periodo"
)

periodo_movel = st.sidebar.slider(
    "Período da Média Móvel:",
    1, 20,
    value=st.session_state.periodo_movel,
    key="periodo_movel"
)

grafico_unico = st.sidebar.checkbox(
    "Exibir em um único gráfico",
    value=st.session_state.grafico_unico,
    key="grafico_unico"
)

# Corrigir início e fim
if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
    inicio, fim = periodo
else:
    inicio = periodo
    fim = data_max.date()

st.sidebar.caption(f"Intervalo disponível: {data_min_total.date()} até {data_max.date()}")

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

# === ORDEM MANUAL DOS GRÁFICOS ===
ordem_manual = [
    "BAR_Au_L",
    "LIX_Au_L",
    "TQ01_Au_L",
    "TQ02_Au_L",
    "TQ06_Au_L",
    "TQ07_Au_L",
    "REJ_Au_L"
]

# Reordenar fontes selecionadas de acordo com a ordem manual
fontes_selecionadas = sorted(
    fontes_selecionadas,
    key=lambda f: ordem_manual.index(f) if f in ordem_manual else len(ordem_manual)
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
