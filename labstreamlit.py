import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import shutil
import os
from streamlit_autorefresh import st_autorefresh

# Força modo wide
st.set_page_config(layout="wide", page_title="Gráfico de Médias Móveis", page_icon="📈")


# Auto-refresh leve para verificar se o arquivo original foi alterado
st_autorefresh(interval=600_000, key="refresh_monitor")

# Caminhos dos arquivos
caminho_origem = r"\\teste\\Resultados Planta.xlsx"
caminho_destino = r"Resultados Planta.xlsx"

# Função para pegar a data/hora de modificação
def get_mod_time(path):
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0

# Verifica modificação
mod_time_origem = get_mod_time(caminho_origem)
mod_time_destino = get_mod_time(caminho_destino)

# Guarda o último mod_time conhecido
if "ultima_modificacao_origem" not in st.session_state:
    st.session_state["ultima_modificacao_origem"] = mod_time_destino

# Compara e exibe botão se mudou
if mod_time_origem != st.session_state["ultima_modificacao_origem"]:
    st.sidebar.warning("Arquivo de origem foi modificado.")
    if st.sidebar.button("🔄 Atualizar dados"):
        try:
            shutil.copy2(caminho_origem, caminho_destino)
            st.session_state["ultima_modificacao_origem"] = mod_time_origem
            st.sidebar.success("Arquivo atualizado com sucesso!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Erro ao copiar o arquivo: {e}")
else:
    st.sidebar.info("Dados atualizados.")


# === Verificação de modificação do arquivo ===
def get_mod_time(path):
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0

mod_time = get_mod_time(caminho_destino)

# === Funções com cache ===
@st.cache_data
def carregar_dados(arquivo, aba, colunas, mod_time, horas=None):
    dados = pd.read_excel(arquivo, sheet_name=aba, header=4, usecols=colunas)
    nomes_colunas = ["Data"]
    if horas:
        nomes_colunas += horas
    else:
        nomes_colunas += [f"{str(hora).zfill(2)}:00" for hora in range(1, 24)] + ["24:00"]
    dados.columns = nomes_colunas
    for i in range(len(dados)):
        if pd.isna(dados.loc[i, "Data"]):
            if i > 0 and pd.notna(dados.loc[i-1, "Data"]):
                dados.loc[i, "Data"] = dados.loc[i-1, "Data"] + pd.Timedelta(days=1)
    dados = dados.dropna(subset=["Data"]).dropna(how="all")
    return dados

@st.cache_data
def processar_dados(dados, valor_maximo, mod_time):
    linhas = []
    for idx, row in dados.iterrows():
        data_atual = row["Data"]
        for coluna in row.index:
            if coluna != "Data":
                valor_bruto = row[coluna]
                if isinstance(valor_bruto, str):
                    valor_bruto = valor_bruto.replace("<", "").replace(",", ".").strip()
                valor = pd.to_numeric(valor_bruto, errors="coerce")
                if pd.notna(valor) and valor != 0 and valor <= valor_maximo:
                    linhas.append({"Data": data_atual, "Hora": coluna, "Valor": valor})
    df = pd.DataFrame(linhas)
    if not df.empty:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
        df["HoraCorrigida"] = df["Hora"].replace({"24:00": "23:59"})
        df["DataHoraReal"] = pd.to_datetime(df["Data"].astype(str) + " " + df["HoraCorrigida"], errors="coerce")
        df = df.dropna(subset=["Valor"])
        df = df[df["Valor"] <= valor_maximo].reset_index(drop=True)
        df["Valor_MediaMovel_15"] = df["Valor"].rolling(window=15, min_periods=1).mean()
    return df

@st.cache_data
def carregar_todos(mod_time):
    def c(aba, colunas, valor_maximo, horas=None):
        dados = carregar_dados("Resultados Planta.xlsx", aba, colunas, mod_time, horas)
        return processar_dados(dados, valor_maximo, mod_time)

    horarios_3 = ["08:00", "16:00", "24:00"]
    horarios_12 = ["02:00", "04:00", "06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00", "24:00"]
    horarios_bar = ["04:00", "08:00", "12:00", "16:00", "20:00", "24:00"]

    return {
        "BAR | Au | Liq": c("Água de Processo", [0, 15, 16, 17, 18, 19, 20], 0.6, horarios_bar),
        #"BAR | CN | Liq": c("Água de Processo", [0, 21, 22, 23, 24, 25, 26], 50, horarios_bar),
        "LIX | Au | Liq": c("Líquidas", [0, 38, 39, 40], 50, horarios_3),
        #"LIX | Cu | Liq": c("Líquidas", [0, 65, 66, 67], 50, horarios_3),
        #"LIX | Fe | Liq": c("Líquidas", [0, 85, 86, 87], 50, horarios_3),
        "TQ01 | Au | Liq": c("Líquidas Saída TQ1 TQ2 TQ6 TQ7", [0] + list(range(7, 31)), 5),
        "TQ02 | Au | Liq": c("Líquidas Saída TQ1 TQ2 TQ6 TQ7", [0, 32, 33, 34], 1.5, horarios_3),
        #"TQ02 | Cu | Liq": c("Líquidas Saída TQ1 TQ2 TQ6 TQ7", [0, 38, 39, 40], 50, horarios_3),
        #"TQ02 | Fe | Liq": c("Líquidas Saída TQ1 TQ2 TQ6 TQ7", [0, 44, 45, 46], 50, horarios_3),
        "TQ06 | Au | Liq": c("Líquidas Saída TQ1 TQ2 TQ6 TQ7", [0, 51, 52, 53], 50, horarios_3),
        #"TQ06 | Cu | Liq": c("Líquidas Saída TQ1 TQ2 TQ6 TQ7", [0, 61, 62, 63], 50, horarios_3),
        #"TQ06 | Fe | Liq": c("Líquidas Saída TQ1 TQ2 TQ6 TQ7", [0, 71, 72, 73], 50, horarios_3),
        "TQ07 | Au | Liq": c("Líquidas Saída TQ1 TQ2 TQ6 TQ7", [0] + list(range(82, 94)), 50, horarios_12),
        "REJ | Au | Liq": c("Líquidas", [0, 101, 102, 103], 0.8, horarios_3),
        #"REJ | Cu | Liq": c("Líquidas", [0, 111, 112, 113], 50, horarios_3),
        #"REJ | Fe | Liq": c("Líquidas", [0, 122, 123, 124], 50, horarios_3),
    }

# === Streamlit App ===
st.title("Visualizador de DataFrames - Gráficos Separados")
st.sidebar.header("Configurações")

with st.spinner("Carregando dados..."):
    dataframes = carregar_todos(mod_time)

# === Período padrão: últimos 30 dias da data mais recente (seguro) ===
data_maxima = max((d["DataHoraReal"].max() for d in dataframes.values() if not d.empty), default=None)
if data_maxima:
    data_minima = data_maxima - pd.Timedelta(days=30)
else:
    data_maxima = pd.to_datetime("today")
    data_minima = data_maxima - pd.Timedelta(days=30)


# === Filtro de datas padrão: últimos 30 dias da data mais recente ===r
data_maxima = max((d["DataHoraReal"].max() for d in dataframes.values() if not d.empty), default=None)
if data_maxima:
    data_minima = data_maxima - pd.Timedelta(days=30)
else:
    data_maxima = pd.to_datetime("today")
    data_minima = data_maxima - pd.Timedelta(days=30)

st.sidebar.subheader("Filtro de Datas")
data_inicio, data_fim = st.sidebar.date_input(
    "Período:",
    value=(data_minima.date(), data_maxima.date()),
    min_value=data_minima.date(),
    max_value=data_maxima.date()
)

# Slider simples (sem estado persistente)
periodo_movel = st.sidebar.slider(
    "Período da Média Móvel:",
    min_value=1,
    max_value=50,
    value=6,
    step=1
)

# Multiselect com todos os gráficos já selecionados por padrão
opcoes = list(dataframes.keys())
selecionados = st.sidebar.multiselect(
    "Selecione os conjuntos de dados:",
    options=opcoes,
    default=opcoes
)

# Checkbox do tipo de gráfico
grafico_unico = st.sidebar.checkbox("Exibir em um único gráfico", value=True)


# === Plot ===
if selecionados:
    if grafico_unico:
        fig = go.Figure()

        for nome in selecionados:
            df = dataframes[nome].copy()
            df = df[(df["DataHoraReal"].dt.date >= data_inicio) & (df["DataHoraReal"].dt.date <= data_fim)]

            if df.empty:
                st.warning(f"Sem dados para {nome} no período.")
                continue

            if periodo_movel == 15 and "Valor_MediaMovel_15" in df.columns:
                df["Valor_MediaMovel"] = df["Valor_MediaMovel_15"]
            else:
                df["Valor_MediaMovel"] = df["Valor"].rolling(window=periodo_movel, min_periods=1).mean()

            fig.add_trace(go.Scatter(
                x=df["DataHoraReal"],
                y=df["Valor_MediaMovel"],
                mode="lines",
                name=nome,
                line=dict(width=2)
            ))

        fig.update_layout(
            title=f"Médias Móveis - {periodo_movel} períodos",
            xaxis_title="Data e Hora",
            yaxis_title="Valor",
            height=600,
            margin=dict(l=50, r=50, t=50, b=50),
            uirevision="grafico_movel"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        for nome in selecionados:
            st.subheader(f"Gráfico - {nome}")
            df = dataframes[nome].copy()
            df = df[(df["DataHoraReal"].dt.date >= data_inicio) & (df["DataHoraReal"].dt.date <= data_fim)]

            if df.empty:
                st.warning(f"Sem dados para {nome} no período.")
                continue

            if periodo_movel == 15 and "Valor_MediaMovel_15" in df.columns:
                df["Valor_MediaMovel"] = df["Valor_MediaMovel_15"]
            else:
                df["Valor_MediaMovel"] = df["Valor"].rolling(window=periodo_movel, min_periods=1).mean()

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["DataHoraReal"],
                y=df["Valor"],
                mode='markers',
                name="Dados Brutos",
                marker=dict(symbol="x", size=4, color="lightgray"),
                showlegend=False
            ))
            fig.add_trace(go.Scatter(
                x=df["DataHoraReal"],
                y=df["Valor_MediaMovel"],
                mode='lines',
                name=nome,
                line=dict(width=2)
            ))
            fig.update_layout(
                title=f"{nome} - Média Móvel {periodo_movel} períodos",
                xaxis_title="Data e Hora",
                yaxis_title="Valor",
                height=500,
                margin=dict(l=50, r=50, t=50, b=50),
                uirevision="grafico_movel"
            )
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Selecione pelo menos um conjunto de dados.")
