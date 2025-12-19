import sys
import subprocess
import importlib.util
import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path, PureWindowsPath
import itertools
from requests_oauthlib import OAuth2Session
import time
import requests
import io
import tempfile
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, quote
import os
import re
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner

# --- LINK DIRETO DA IMAGEM NO GITHUB ---
url_imagem = "https://raw.githubusercontent.com/DellaVolpe69/Images/main/AppBackground02.png"
url_logo = "https://raw.githubusercontent.com/DellaVolpe69/Images/main/DellaVolpeLogoBranco.png"
fox_image = "https://raw.githubusercontent.com/DellaVolpe69/Images/main/Foxy4.png"

###### CONFIGURAR O TÍTULO DA PÁGINA #######
st.set_page_config(
    page_title="Pendências do Inventário",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    f"""
    <style>
    /* Remove fundo padrão dos elementos de cabeçalho que às vezes ‘brigam’ com o BG */
    header, [data-testid="stHeader"] {{
        background: transparent;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("""
<style>
/* Forçar cor branca em qualquer texto dentro de markdown ou write */
/* p, span, div, label { */
p, label {
    color: #EDEBE6 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ===== Seletores amplos para pegar warnings/alerts em várias versões do Streamlit ===== */

/* Container genérico (várias builds usam esse data-testid) */
div[data-testid="stNotificationContent"],
div[data-testid="stNotification"],
div[data-testid="stAlert"],
div[class*="stNotification"],
div[class*="stAlert"],
div[role="alert"] {
    color: #EDEBE6 !important;         /* cor do texto */
}

/* Pegar explicitamente parágrafos/spans dentro do warning (onde o texto costuma estar) */
div[data-testid="stNotificationContent"] p,
div[data-testid="stNotificationContent"] span,
div[role="alert"] p,
div[role="alert"] span,
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span {
    color: #EDEBE6 !important;
}

/* Algumas builds colocam o texto dentro de elementos com classe .stMarkdown */
div[data-testid="stNotificationContent"] .stMarkdown,
div[role="alert"] .stMarkdown {
    color: #EDEBE6 !important;
}

/* Força também em labels e botões filhos (caso o warning tenha estruturas internas) */
div[data-testid="stNotification"] label,
div[role="alert"] label,
div[data-testid="stNotification"] button,
div[role="alert"] button {
    color: #EDEBE6 !important;
}
</style>
""", unsafe_allow_html=True)

##########################################
###### CARREGAR MÓDULOS E PARQUETS #######
# Caminho local onde o módulo será baixado
modulos_dir = Path(__file__).parent / "Modulos"

# Se o diretório ainda não existir, faz o clone direto do GitHub
if not modulos_dir.exists():
    print("📥 Clonando repositório Modulos do GitHub...")
    subprocess.run([
        "git", "clone",
        "https://github.com/DellaVolpe69/Modulos.git",
        str(modulos_dir)
    ], check=True)

# Garante que o diretório está no caminho de importação
if str(modulos_dir) not in sys.path:
    sys.path.insert(0, str(modulos_dir))

# Agora importa o módulo normalmente
from Modulos import AzureLogin
from Modulos import ConectionSupaBase
###################################
import Modulos.Minio.examples.MinIO as meu_minio

from Modulos.Minio.examples.MinIO import read_file  # ajuste o caminho se necessário

@st.cache_data(show_spinner="Carregando FILIAL...")
def load_filial():
    return read_file('dados/CV_FILIAL.parquet', 'calculation-view')

try:
    df_filial = load_filial()
except Exception as e:
    st.error(f"Erro ao carregar FILIAL: {e}")
    st.stop()

# st.dataframe(df_ibge.head())

df_filial = df_filial[['SALESORG', 'TXTMD_1']].drop_duplicates().reset_index(drop=True)
###################################
#combinacoes = sorted([f"{''.join(p)}" for p in itertools.product("NS", repeat=7)])

# 🔗 Conexão com o Supabase
supabase = ConectionSupaBase.conexao()

# Inicializa o estado da página
if "pagina" not in st.session_state:
    st.session_state.pagina = "menu"

# Funções para trocar de página
def ir_para_cadastrar():
    st.session_state.pagina = "Cadastrar"

def ir_para_editar():
    st.session_state.pagina = "Editar"

# --- CSS personalizado ---
st.markdown(f"""
    <style>
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.7)),
                        url("{url_imagem}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* Inputs padrão: text_input, number_input, date_input, etc */
        input, textarea {{
            border: 1px solid white !important;
            border-radius: 5px !important;
        }}
        
        /* Selectbox (parte fechada) */
        .stSelectbox div[data-baseweb="select"] > div {{
            border: 1px solid white !important;
            border-radius: 5px !important;
        }}
        
        /* Date input container */
        .stDateInput input {{
            border: 1px solid white !important;
            border-radius: 5px !important;
        }}

        .stButton > button {{
            background-color: #FF5D01 !important;
            color: #EDEBE6 !important;
            border: 2px solid white !important;
            padding: 0.6em 1.2em;
            border-radius: 10px !important;
            font-size: 1rem;
            font-weight: 500;
            font-color: #EDEBE6 !important;
            cursor: pointer;
            transition: 0.2s ease;
            text-decoration: none !important;   /* 👈 AQUI remove de vez */
            display: inline-block;
        }}
        .stButton > button:hover {{
            background-color: #993700 !important;
            color: #FF5D01 !important;
            transform: scale(1.03);
            font-color: #FF5D01 !important;
            border: 2px solid #FF5D01 !important;
        }}

        /* RODAPÉ FIXO */
        .footer {{
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            text-align: center;
            font-size: 14px;
            padding: 8px 0;
            text-shadow: 1px 1px 2px black;
        }}
        .footer a {{
            color: #FF5D01;
            text-decoration: none;
            font-weight: bold;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÃO DE RODAPÉ ---
def rodape():
    st.markdown("""
        <div class="footer">
            © 2025 <b>Della Volpe</b> | Desenvolvido por <a href="#">Raphael Chiavegati Oliveira</a>
        </div>
    """, unsafe_allow_html=True)

##################################################################
################ FUNÇÕES DO FORMULÁRIO DE JANELAS ################
##################################################################

# Função para carregar dados
#def carregar_dados():
#    data = supabase.table("Pendencias_Inventario").select("*").execute()
#    return pd.DataFrame(data.data)

def carregar_dados(limit=10000):
    data = (
        supabase.table("Pendencias_Inventario")
        .select("*")
        .order("ID", desc=True)   # ordena do maior para o menor
        .limit(limit)             # pega só os últimos 5 mil
        .execute()
    )

    df = pd.DataFrame(data.data)

    # opcional: reordena do mais antigo → mais novo para ficar "bonito"
    df = df.sort_values(by="ID").reset_index(drop=True)

    return df

# Função para inserir
def inserir_registro(
    fornecedor, 
    fornecedor_cnpj, 
    nfe, 
    status, 
    obs, 
    criado_por, 
    matricula, 
    estado_da_etiqueta, 
    qr, 
    chave, 
    pedido, 
    volume, 
    email,
    filial
):

    # -----------------------------
    # 🚀 Enviar ao Supabase
    # -----------------------------
    res = supabase.table("Pendencias_Inventario").insert({
        "FORNECEDOR": fornecedor,
        "FORNECEDOR_CNPJ": fornecedor_cnpj,
        "NF_E": nfe,
        "STATUS": status,
        "OBS": obs,
        "CRIADO_POR": criado_por,
        "MATRICULA": matricula,
        "ESTADO_DA_ETIQUETA": estado_da_etiqueta,
        "QR": qr,
        "CHAVE": chave,
        "PEDIDO": pedido,
        "VOLUME": volume,
        "EMAIL": email,
        "FILIAL": filial
    }).execute()
    
    return res

# Função para atualizar
def atualizar_registro(id,
                       nfe):
    
    supabase.table("Pendencias_Inventario").update({
        "NF_E": nfe
    }).eq("ID", id).execute()
    st.success("✏️ Registro atualizado com sucesso!")

# Função para excluir
def excluir_registro(id):
    supabase.table("Pendencias_Inventario").delete().eq("ID", id).execute()
    st.success("🗑️ Registro excluído com sucesso!")
    
def extrair_dados(texto: str) -> dict:
    # pega somente a parte do XML
    inicio = texto.find("<Nota>")
    xml_str = texto[inicio:]

    root = ET.fromstring(xml_str)

    chave = root.findtext("ChaveNF")
    nfe = root.findtext("NumeroDoc")
    pedido = root.findtext("Pedido")
    etiquetas = root.findtext("Etiquetas")

    # converte 1/1 → 1;1
    volume = etiquetas.replace("/", ";") if etiquetas else None

    return {
        "chave": chave,
        "nfe": nfe,
        "pedido": pedido,
        "volume": volume
    }

# Função para limpar campos invisíveis
def limpar_campos():
    st.session_state.dados_nota = {}
    # 🔥 Remove o valor do textarea com segurança
    st.session_state.pop("entrada_xml", None)

    for campo in ["chave", "nfe", "pedido", "volume"]:
        if campo in st.session_state:
            del st.session_state[campo]
    
# Função para verificar se já existe um cadastro igual
def verificar_existencia(referencia_medicao, incoterms, prioridade, tipo_carga, vigencia_inicio):
    result = (
        supabase.table("Pendencias_Inventario")
        .select("ID")
        .eq("REFERENCIA_MEDICAO", referencia_medicao)
        .eq("INCOTERMS", incoterms)
        .eq("PRIORIDADE", prioridade)
        .eq("TIPO_CARGA", tipo_carga)
        .eq("VIGENCIA_INICIO", vigencia_inicio)
        .execute()
    )

    # Se encontrar alguma linha → já existe
    return len(result.data) > 0

###########################################################################
###########################################################################

#df_filial = MinIO.read_file('dados/CV_FILIAL.parquet', 'calculation-view')[['SALESORG', 'TXTMD_1']].drop_duplicates().reset_index(drop=True)
#df_filial = df_filial[['SALESORG', 'TXTMD_1']].drop_duplicates().reset_index(drop=True)

##################################################################
##################################################################
##################################################################

# --- MENU PRINCIPAL ---
if st.session_state.pagina == "menu":
    st.markdown(f"""
        <div class="header" style="text-align: center; padding-top: 2em;">
            <img src="{url_logo}" alt="Logo Della Volpe" 
                 style="width: 40%; max-width: 200px; height: auto; margin-bottom: 10px;">
            <h1 style="color: #EDEBE6; text-shadow: 1px 1px 3px black;">
                Pendências do Inventário
            </h1>
        </div>
    """, unsafe_allow_html=True)
    # Espaço antes dos botões (ajuste quantos <br> quiser)
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button("Cadastrar", use_container_width=True, on_click=ir_para_cadastrar)
        st.button("Editar", use_container_width=True, on_click=ir_para_editar)
    rodape()

# --- PÁGINA CADASTRAR ---
if st.session_state.pagina == "Cadastrar":
    st.markdown(
    "<h1 style='text-align: center; color: #EDEBE6; text-shadow: 1px 1px 3px black;'>"
    "📝 Pendências do Inventário"
    "</h1>",
    unsafe_allow_html=True
)
    
    # Inicializa estado
    # if "scanner_ativo" not in st.session_state:
    #     st.session_state.scanner_ativo = False

    # if "xml_qr" not in st.session_state:
    #     st.session_state.xml_qr = ""

    if "dados_nota" not in st.session_state:
        st.session_state.dados_nota = {}
    
    ############################################
    
    matricula = st.text_input("Digite sua matrícula:", help="Apenas números. Exemplo: 12345")
    # Verificação se o valor contém apenas números e tem 10 caracteres
    if matricula:
        if not matricula.isdigit():
            st.error("⚠️ A matrícula deve conter apenas números.")
            
    filial = st.selectbox("Filial", df_filial['TXTMD_1'].sort_values(ascending=True))
    filial = df_filial.loc[df_filial['TXTMD_1'] == filial, 'SALESORG'].iloc[0]
    
    status = st.selectbox(
        "Área Inventariada:",
        options=["ARMAZEM", "PENDENCIA", "OCORRÊNCIA", "DEVOLUÇÃO"],
        index=0  
    )    
    
    ############################################
    
    estado_da_etiqueta = st.selectbox(
        "Estado da Etiqueta:",
        options=["Normal", "Sem Etiqueta", "Etiqueta sem QRCode"],
        key="estado_da_etiqueta",
        on_change=limpar_campos  # 🔥 dispara a limpeza ao mudar
    )
    
    criado_por = ""
    chave = ""
    pedido = ""
    volume = ""
    qr = ""
    fornecedor = ""
    fornecedor_cnpj = ""
    nfe = ""
    obs = ""
    email = ""
    entrada = ""
    ############################################
    
    # -----------------------------------
    # Lógica da tela
    # -----------------------------------
    if estado_da_etiqueta == "Normal":
    
    ############################################
        
        entrada = st.text_area(
            "Conteúdo do Código / XML",
            height=150,
            key="entrada_xml"
        )

        if st.session_state.entrada_xml:
            st.session_state.dados_nota = extrair_dados(st.session_state.entrada_xml)

            dados = st.session_state.dados_nota

            chave = st.session_state["chave"] = dados.get("chave", "")
            nfe = st.session_state["nfe"] = dados.get("nfe", "")
            pedido = st.session_state["pedido"] = dados.get("pedido", "")
            volume = st.session_state["volume"] = dados.get("volume", "")

            st.text_input("Chave NF-e:", key="chave", disabled=True)
            st.text_input("Número da NF-e:", key="nfe", disabled=True)
            st.text_input("Pedido", key="pedido", disabled=True)
            st.text_input("Volume:", key="volume", disabled=True)

            qr = st.session_state.entrada_xml

    ############################################

    elif estado_da_etiqueta == "Sem Etiqueta":
        
        entrada = ""
        
        chave = ""
        
        fornecedor = st.text_input("Nome do Fornecedor:")
        
        nfe = st.text_input("Número da NF-e:")
        
        obs = st.text_area("Observação:")
        
    ############################################
    
    elif estado_da_etiqueta == "Etiqueta sem QRCode":
        
        entrada = ""
        
        chave = ""
        
        fornecedor_cnpj = st.text_input("CNPJ do Fornecedor:")
        
        nfe = st.text_input("Número da NF-e:")
        
        obs = st.text_area("Observação:")
        
    ############################################
    
    st.markdown("""
        <style>
        /* Texto do label do file_uploader */
        div[data-testid="stFileUploader"] div {
            color: #EDEBE6 !important;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("Anexos", accept_multiple_files=True)
    
    # Criar espaço vazio nas laterais e centralizar os botões
    esp1, centro, esp2 = st.columns([1, 2, 1])

    with centro:
        # Duas colunas de mesma largura para os botões
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("Voltar ao Menu", use_container_width=True):
                limpar_campos()   # 🔥 limpa QR, campos e scanner
                st.session_state.pagina = "menu"
                st.rerun()
                st.stop() 

        with col2:
            ############################################
            
            if st.button("💾 Salvar", use_container_width=True):

                if nfe and matricula:

                    #################################################
                    
                    # 1) Salva o registro no Supabase                                                        
                    res = inserir_registro(
                        fornecedor=fornecedor,
                        fornecedor_cnpj=fornecedor_cnpj,
                        nfe=nfe,
                        status=status,
                        obs=obs,
                        criado_por=criado_por,
                        matricula=matricula,
                        estado_da_etiqueta=estado_da_etiqueta,
                        qr=qr,
                        chave=chave,
                        pedido=pedido,
                        volume=volume,
                        email=st.session_state.get("user_email", "desconhecido"),
                        filial=filial
                    )
                    novo_id = res.data[0]["ID"]
                    
                    # 2) Upload dos anexos
                    anexos_nomes = []

                    for idx, file in enumerate(uploaded_files, start=1):
                        ext = file.name.split(".")[-1]
                        nome_minio = f"{novo_id}_{idx}.{ext}"

                        # Salvar temporariamente o arquivo
                        with tempfile.NamedTemporaryFile(delete=False) as tmp:
                            tmp.write(file.getvalue())
                            temp_path = tmp.name  # caminho do arquivo salvo

                        # Enviar ao MinIO
                        meu_minio.upload(
                            object_name="PendenciasInventario/"+ nome_minio,
                            bucket_name="formularios",
                            file_path=temp_path
                        )

                        anexos_nomes.append(nome_minio)

                        # Remove o arquivo temporário
                        os.remove(temp_path)

                    #st.session_state.pagina = "Sucesso"  # vai pra página oculta
                    st.success("✅ Registro atualizado com sucesso!")
                    st.balloons()
                    limpar_campos()
                    st.stop()
                    
                else:
                    st.warning("⚠️ Preencha todos os campos obrigatórios.")
                #st.rerun()
                st.stop()                 
                    
        ########################################################################################             

# --- PÁGINA EDITAR ---
elif st.session_state.pagina == "Editar":
    st.markdown(
    "<h1 style='text-align: center; color: #EDEBE6; text-shadow: 1px 1px 3px black;'>"
    "✏️ Editar"
    "</h1>",
    unsafe_allow_html=True
)
    st.markdown("<h3 style='color: white;'>Lista de Registros</h3>", unsafe_allow_html=True)
    df = carregar_dados()
    
    # estilo abrangente para títulos de expander (várias versões do Streamlit)
    st.markdown("""
    <style>
    /* seletor moderno: expander com data-testid */
    div[data-testid="stExpander"] > div[role="button"],
    div[data-testid="stExpander"] > button,
    div[data-testid="stExpander"] summary {
        color: #EDEBE6 !important;
    }
    
    /* spans/labels dentro do botão (algumas builds usam span) */
    div[data-testid="stExpander"] span,
    div[data-testid="stExpander"] [aria-expanded="true"] span {
        color: #FF8C00 !important;
    }

    /* ícone SVG do expander (setinha) */
    div[data-testid="stExpander"] svg,
    div[data-testid="stExpander"] button svg {
        fill: #EDEBE6 !important;
        stroke: #EDEBE6 !important;
    }

    /* fallback para classes antigas / alternadas */
    .st-expanderHeader,
    .stExpanderHeader,
    .css-1v0mbdj-summary { /* exemplo de classe gerada dinamicamente */
        color: #EDEBE6 !important;
    }

    /* força também quando o texto está dentro de um label/button com background */
    div[data-testid="stExpander"] button {
        color: #EDEBE6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if not df.empty:
        # 🔍 Filtros

        with st.expander("🔎 Filtros"):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                filtro_nfe = st.selectbox(
                    "Número da NF-e", 
                    ["Todas"] + sorted(df["NF_E"].unique().tolist())
                )

            with col2:
                filtro_status = st.selectbox(
                    "Status", 
                    ["Todas"] + sorted(df["STATUS"].unique().tolist())
                )
                
            with col3:
                filtro_matricula = st.selectbox(
                    "Matrícula", 
                    ["Todas"] + sorted(df["MATRICULA"].dropna().unique().tolist())
                )
                
            with col4:
                filtro_filial = st.selectbox(
                    "Filial", 
                    ["Todas"] + sorted(df["FILIAL"].unique().tolist())
                )

            # Filtro de data
            col1, col2 = st.columns(2)
            with col1:
                data_inicio = st.date_input("Data Início (vigência)", value=None)
            with col2:
                data_fim = st.date_input("Data Fim (vigência)", value=None)

        # Aplicar filtros
        if filtro_nfe != "Todas":
            df = df[df["NF_E"] == filtro_nfe]

        if filtro_status != "Todas":
            df = df[df["STATUS"] == filtro_status]
            
        if filtro_matricula != "Todas":
            df = df[df["MATRICULA"] == filtro_matricula]

        if filtro_filial != "Todas":
            df = df[df["FILIAL"] == filtro_filial]

        df["CARIMBO"] = (
            pd.to_datetime(df["CARIMBO"], errors="coerce")
            .dt.tz_localize(None)
        )

        if data_inicio is not None:
            data_inicio_ts = pd.Timestamp(data_inicio)
            df = df[df["CARIMBO"] >= data_inicio_ts]

        if data_fim is not None:
            data_fim_ts = pd.Timestamp(data_fim) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            df = df[df["CARIMBO"] <= data_fim_ts]

        # Mostrar tabela filtrada
        #df.drop(columns=['CREATED_AT'], inplace=True)
        df.sort_values(by=["ID", "NF_E", "STATUS", "MATRICULA", "FILIAL", "CARIMBO"], ascending=[False, False, True, True, True, True], inplace=True)
        st.dataframe(df.copy().set_index('ID'))

    if not df.empty:

        # Selecionar registro para editar/excluir
        id_registro = st.selectbox("Selecione o ID para editar/excluir", df["ID"].sort_values(ascending=False))

        registro = df[df["ID"] == id_registro].iloc[0]
        
        prefixo = f"PendenciasInventario/{id_registro}"

        anexos = meu_minio.listar_anexos("formularios", prefixo)
        
        st.subheader("📎 Anexos deste registro")

        if anexos:
            for caminho_completo in anexos:
                nome = caminho_completo.split("/")[-1]  # extraindo só "123_1.pdf"

                st.write("➡️", nome)

                data = meu_minio.manager.client.get_object(
                    "formularios",
                    caminho_completo
                ).read()

                st.download_button("Baixar", data, file_name=nome)
        else:
            st.info("Nenhum anexo encontrado para este registro.")

        with st.expander("✏️ Editar Registro"):
            
            novo_nfe = st.text_input("Número da NF-e", registro["NF_E"])

            if st.button("Salvar Alterações"):

                #st.info("🔄 Atualizando registro...")
                atualizar_registro(id_registro,
                                        novo_nfe)
                st.session_state.pagina = "Editado"  # vai pra página oculta
                st.rerun()
                st.stop() 
                    
        # Inicializar flag
        if "confirmar_exclusao" not in st.session_state:
            st.session_state.confirmar_exclusao = False
        if "registro_pendente_exclusao" not in st.session_state:
            st.session_state.registro_pendente_exclusao = None

        with st.expander("🗑️ Excluir Registro"):

            # Primeiro botão: pedir confirmação
            if st.button("Excluir", type="primary"):
                st.session_state.confirmar_exclusao = True
                st.session_state.registro_pendente_exclusao = id_registro
                st.rerun()

            # Se clicou em "Excluir", aparece a confirmação
            if st.session_state.confirmar_exclusao:

                st.warning("⚠️ Tem certeza de que deseja excluir este registro?")

                col1, col2 = st.columns(2)

                # Botão "Sim"
                with col1:
                    if st.button("Sim, excluir", type="primary"):
                        excluir_registro(st.session_state.registro_pendente_exclusao)
                        st.session_state.confirmar_exclusao = False
                        st.session_state.registro_pendente_exclusao = None
                        st.session_state.pagina = "Excluido"
                        st.rerun()

                # Botão "Não"
                with col2:
                    if st.button("Cancelar"):
                        st.session_state.confirmar_exclusao = False
                        st.session_state.registro_pendente_exclusao = None
                        st.rerun()
    else:
        st.info("Nenhum registro encontrado.")

    # Criar espaço vazio nas laterais e centralizar os botões
    esp1, centro, esp2 = st.columns([1, 1, 1])

    with centro:
        if st.button("Voltar ao Menu", use_container_width=True):
            st.session_state.pagina = "menu"
            st.rerun()
            st.stop()   # ← ESSENCIAL NO LUGAR DO return            

# 🟢 Página oculta de sucesso (não aparece no menu)
elif st.session_state.pagina == "Sucesso":

    # Força a página a subir para o topo
    st.markdown("""
        <script>
            window.parent.document.querySelector('section.main').scrollTo(0, 0);
        </script>
    """, unsafe_allow_html=True)

    st.markdown('<div class="foguete">', unsafe_allow_html=True)
    st.markdown("<h3 style='color: white;'>🎈 Cadastro efetuado!</h3>", unsafe_allow_html=True)

    fox_image_html = f"""
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
    ">
        <img src="{fox_image}" alt="Foxy" 
            style="
                width: min(400px, 80vw);
                height: auto;
                margin-bottom: 10px;
            ">
    </div>
    """
    
    st.markdown(fox_image_html, unsafe_allow_html=True)
    st.success("✅ Registro atualizado com sucesso!")
    st.balloons()
    
    # Criar espaço vazio nas laterais e centralizar os botões
    esp1, centro, esp2 = st.columns([1, 1, 1])

    with centro:
        if st.button("Ok", use_container_width=True):
            st.session_state.pagina = "menu"
            st.rerun()
            st.stop()   # ← ESSENCIAL NO LUGAR DO return     

# 🟢 Página oculta de editado (não aparece no menu)
elif st.session_state.pagina == "Editado":

    # Força a página a subir para o topo
    st.markdown("""
        <script>
            window.parent.document.querySelector('section.main').scrollTo(0, 0);
        </script>
    """, unsafe_allow_html=True)

    st.markdown('<div class="foguete">', unsafe_allow_html=True)
    st.markdown("<h3 style='color: white;'>🎈 Dado editado!</h3>", unsafe_allow_html=True)

    fox_image_html = f"""
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
    ">
        <img src="{fox_image}" alt="Foxy" 
            style="
                width: min(400px, 80vw);
                height: auto;
                margin-bottom: 10px;
            ">
    </div>
    """

    st.markdown(fox_image_html, unsafe_allow_html=True)

    st.success("✅ Registro atualizado com sucesso!")
    st.balloons()

    # Criar espaço vazio nas laterais e centralizar os botões
    esp1, centro, esp2 = st.columns([1, 1, 1])

    with centro:
        if st.button("Ok", use_container_width=True):
            st.session_state.pagina = "menu"
            st.rerun()
            st.stop()   # ← ESSENCIAL NO LUGAR DO return   
    
# 🟢 Página oculta de editado (não aparece no menu)
elif st.session_state.pagina == "Excluido":

    # Força a página a subir para o topo
    st.markdown("""
        <script>
            window.parent.document.querySelector('section.main').scrollTo(0, 0);
        </script>
    """, unsafe_allow_html=True)

    st.markdown('<div class="foguete">', unsafe_allow_html=True)
    st.markdown("<h3 style='color: white;'>🎈 Dado excluído!</h3>", unsafe_allow_html=True)

    fox_image_html = f"""
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
    ">
        <img src="{fox_image}" alt="Foxy" 
            style="
                width: min(400px, 80vw);
                height: auto;
                margin-bottom: 10px;
            ">
    </div>
    """

    st.markdown(fox_image_html, unsafe_allow_html=True)

    st.success("✅ Registro excluído com sucesso!")
    st.balloons()

    # Criar espaço vazio nas laterais e centralizar os botões
    esp1, centro, esp2 = st.columns([1, 1, 1])

    with centro:
        if st.button("Ok", use_container_width=True):
            st.session_state.pagina = "menu"
            st.rerun()
            st.stop()   # ← ESSENCIAL NO LUGAR DO return   
