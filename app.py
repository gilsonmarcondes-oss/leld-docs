import json
import os
import sys
import urllib.parse
import gdown
import requests
import streamlit as st
import re

# Configuração da página - DEVE SER SEMPRE O PRIMEIRO COMANDO
st.set_page_config(page_title="LELD Docs Auditor", page_icon="🔒", layout="wide")

# Garante que a pasta raiz e a pasta src/ estejam no sys.path
RAIZ_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(RAIZ_DIR, "src")

for caminho in (RAIZ_DIR, SRC_DIR):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

from src.config import (
    CAMINHO_LATTES_PDF,
    CAMINHO_PUBLICACOES_PDF,
    CAMINHO_EVENTOS_PDF,
    ARQUIVO_SAIDA_PUBS_HTML,
    ARQUIVO_SAIDA_EVENTOS_HTML,
)

try:
    import main as auditor_main
except ImportError:
    try:
        from src import main as auditor_main
    except ImportError:
        auditor_main = None

# --- INÍCIO DA CONFIGURAÇÃO DE SEGURANÇA (COFRE) ---
if not os.path.exists("google_credentials.json"):
    try:
        with open("google_credentials.json", "w", encoding="utf-8") as f:
            f.write(st.secrets["google_credentials_json"])
    except Exception:
        st.error(
            "Erro: O segredo 'google_credentials_json' não foi encontrado no painel do Streamlit."
        )
        st.stop()
# --- FIM DA CONFIGURAÇÃO DE SEGURANÇA ---

try:
    with open("google_credentials.json", "r", encoding="utf-8") as f:
        creds_data = json.load(f)
        client_type = list(creds_data.keys())[0]
        CLIENT_ID = creds_data[client_type]["client_id"]
        CLIENT_SECRET = creds_data[client_type]["client_secret"]
        TOKEN_URI = creds_data[client_type].get(
            "token_uri", "https://oauth2.googleapis.com/token"
        )
        AUTH_URI = creds_data[client_type].get(
            "auth_uri", "https://accounts.google.com/o/oauth2/auth"
        )
except Exception as e:
    st.error(f"Erro ao carregar o ficheiro 'google_credentials.json': {e}")
    st.stop()

REDIRECT_URI = "https://leld-docs.streamlit.app"


def salvar_pdf_upload(uploaded_file, caminho_destino):
    """Garante que a pasta existe e salva o PDF exatamente onde o config.py espera."""
    pasta = os.path.dirname(caminho_destino)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(caminho_destino, "wb") as f:
        f.write(uploaded_file.getbuffer())


def baixar_pdf_drive(url_drive: str, caminho_destino: str):
    """Baixa um PDF do Google Drive diretamente para o disco em streaming."""
    pasta = os.path.dirname(caminho_destino)
    if pasta:
        os.makedirs(pasta, exist_ok=True)

    url_limpa = url_drive.strip()
    match = re.search(r"(?:/d/|id=)([a-zA-Z0-9_-]{25,})", url_limpa)
    if match:
        url_download = f"https://drive.google.com/uc?id={match.group(1)}"
    else:
        url_download = url_limpa

    resultado = gdown.download(
        url=url_download,
        output=caminho_destino,
        quiet=True,
    )

    if not resultado or not os.path.exists(caminho_destino):
        raise ValueError(
            "Não foi possível baixar o arquivo. Verifique o link e se ele está compartilhado como 'Qualquer pessoa com o link'."
        )

    with open(caminho_destino, "rb") as f:
        cabecalho = f.read(4)
    if cabecalho != b"%PDF":
        os.remove(caminho_destino)
        raise ValueError(
            "O link não retornou um PDF válido. Confirme se o acesso está como 'Qualquer pessoa com o link'."
        )


def renderizar_seletor_pdf(titulo: str, caminho_destino: str, chave: str, limite_mb: int = 200):
    """Exibe abas de Upload direto e Link do Google Drive para um documento."""
    st.markdown(f"**{titulo}**")
    aba_upload, aba_drive = st.tabs(["📤 Upload", "🔗 Google Drive"])

    with aba_upload:
        arquivo = st.file_uploader(
            f"Enviar {titulo}",
            type=["pdf"],
            key=f"upload_{chave}",
            max_upload_size=limite_mb,
            label_visibility="collapsed",
        )
        if arquivo:
            salvar_pdf_upload(arquivo, caminho_destino)

    with aba_drive:
        url_drive = st.text_input(
            "Link do Google Drive",
            placeholder="https://drive.google.com/file/d/...",
            key=f"drive_url_{chave}",
            label_visibility="collapsed",
        )
        if st.button("⬇️ Baixar do Drive", key=f"btn_drive_{chave}", use_container_width=True):
            if not url_drive.strip():
                st.warning("Cole o link do Google Drive primeiro.")
            else:
                with st.spinner("Baixando PDF do Google Drive..."):
                    try:
                        baixar_pdf_drive(url_drive, caminho_destino)
                    except Exception as e:
                        st.error(f"Erro ao baixar: {e}")

    if os.path.exists(caminho_destino):
        tamanho_mb = os.path.getsize(caminho_destino) / (1024 * 1024)
        st.success(f"Pronto: `{os.path.basename(caminho_destino)}` ({tamanho_mb:.1f} MB)")


def aplicar_chave_api(chave: str):
    """Sincroniza a chave informada na sessão com as variáveis de ambiente e .env."""
    chave_limpa = chave.strip()
    if chave_limpa:
        os.environ["GOOGLE_API_KEY"] = chave_limpa
        os.environ["GEMINI_API_KEY"] = chave_limpa
        with open(".env", "w", encoding="utf-8") as f_env:
            f_env.write(f"GEMINI_API_KEY={chave_limpa}\n")
            f_env.write(f"GOOGLE_API_KEY={chave_limpa}\n")


def main():
    st.title("🔒 LELD Docs Auditor")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = ""
    if "relatorios_salvos_sessao" not in st.session_state:
        st.session_state.relatorios_salvos_sessao = {}

    if not st.session_state.authenticated:
        st.info("Acesso restrito. Faça login com a sua conta institucional (@unesp.br).")

        auth_params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"{AUTH_URI}?" + urllib.parse.urlencode(auth_params)

        st.markdown(
            f'<a href="{auth_url}" target="_blank">'
            f'<button style="background-color:#4285F4; color:white; padding:12px 24px; '
            f'border:none; border-radius:6px; cursor:pointer; font-size:16px; font-weight:bold;">'
            f"🔑 Entrar com Google"
            f"</button></a>",
            unsafe_allow_html=True,
        )

        query_params = st.query_params
        if "code" in query_params:
            code = query_params["code"]
            token_data = {
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            }

            try:
                response = requests.post(TOKEN_URI, data=token_data, timeout=15)
                token_json = response.json()

                if response.status_code == 200:
                    access_token = token_json.get("access_token")
                    user_response = requests.get(
                        "https://www.googleapis.com/oauth2/v2/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=15,
                    )
                    user_info = user_response.json()
                    email = (user_info.get("email") or "").lower()

                    if email.endswith("@unesp.br") or email == "gilsonmarcondes@gmail.com":
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(
                            f"O e-mail **{email}** não tem permissão. Apenas contas institucionais (@unesp.br) são aceites."
                        )
                        st.query_params.clear()
                else:
                    st.error(
                        f"Erro na autenticação com o Google: {token_json.get('error_description', token_json)}"
                    )
                    st.query_params.clear()
            except Exception as e:
                st.error(f"Erro de conexão ao validar o token: {e}")
                st.query_params.clear()

    else:
        with st.sidebar:
            st.success(f"Sessão iniciada como:\n**{st.session_state.user_email}**")
            st.divider()

            st.subheader("🔑 Configuração da API")
            user_api_key = st.text_input(
                "Insira a sua Google API Key",
                value=st.session_state.gemini_api_key,
                type="password",
                help="Obtenha gratuitamente em aistudio.google.com",
            )

            if user_api_key:
                st.session_state.gemini_api_key = user_api_key.strip()
                aplicar_chave_api(st.session_state.gemini_api_key)
                st.success("Chave configurada com sucesso!")
            else:
                st.warning("⚠️ Insira a sua chave do Gemini para habilitar a auditoria.")

            st.divider()
            if st.button("🚪 Terminar Sessão", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.session_state.gemini_api_key = ""
                st.session_state.relatorios_salvos_sessao = {}
                for var in ["GOOGLE_API_KEY", "GEMINI_API_KEY"]:
                    if var in os.environ:
                        del os.environ[var]
                if os.path.exists(".env"):
                    os.remove(".env")
                st.query_params.clear()
                st.rerun()

        st.success("Acesso autorizado! Pode iniciar a preparação dos documentos.")
        st.subheader("📁 Gestão de Documentos para Auditoria")
        st.write("Faça o upload dos ficheiros PDF abaixo ou cole o link do Google Drive (para arquivos grandes).")

        col1, col2, col3 = st.columns(3)

        with col1:
            renderizar_seletor_pdf("Currículo Lattes (PDF)", CAMINHO_LATTES_PDF, "lattes")

        with col2:
            renderizar_seletor_pdf("Publicações (PDF)", CAMINHO_PUBLICACOES_PDF, "pubs")

        with col3:
            renderizar_seletor_pdf("Eventos (PDF)", CAMINHO_EVENTOS_PDF, "eventos")

        st.divider()

        if st.button("🚀 Executar Auditoria Completa", use_container_width=True):
            chave_ativa = st.session_state.gemini_api_key or os.environ.get("GEMINI_API_KEY", "").strip()
            if not chave_ativa:
                st.error(
                    "❌ Por favor, insira a sua Google API Key na barra lateral antes de executar a auditoria."
                )
            elif not auditor_main or not hasattr(auditor_main, "main"):
                st.error("❌ O módulo de auditoria (src/main.py) não foi localizado corretamente.")
            else:
                aplicar_chave_api(chave_ativa)
                with st.spinner(
                    "⏳ A executar o pipeline de auditoria... Isso pode levar alguns minutos. Aguarde."
                ):
                    try:
                        auditor_main.main()
                        st.session_state.auditoria_concluida = True
                        st.success("✨ Processamento de auditoria finalizado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro durante a execução da auditoria: {e}")

        relatorios_oficiais = [
            ("Relatório Consolidado de Publicações", ARQUIVO_SAIDA_PUBS_HTML),
            ("Relatório Consolidado de Eventos", ARQUIVO_SAIDA_EVENTOS_HTML),
        ]

        encontrados = [
            (titulo, caminho)
            for titulo, caminho in relatorios_oficiais
            if caminho and os.path.exists(caminho)
        ]

        if encontrados:
            st.divider()
            st.subheader("📥 Relatórios Gerados Disponíveis para Download:")

            for idx, (titulo, caminho_html) in enumerate(encontrados):
                nome_ficheiro = os.path.basename(caminho_html)
                with open(caminho_html, "rb") as f_down:
                    conteudo_bytes = f_down.read()

                st.download_button(
                    label=f"⬇️ Descarregar {titulo} ({nome_ficheiro})",
                    data=conteudo_bytes,
                    file_name=nome_ficheiro,
                    mime="text/html",
                    use_container_width=True,
                    key=f"download_oficial_{idx}",
                )

        if st.session_state.relatorios_salvos_sessao:
            st.divider()
            st.subheader("📥 Relatórios Gerados Disponíveis para Download:")

            for nome_arq, conteudo_bytes in sorted(
                st.session_state.relatorios_salvos_sessao.items()
            ):
                st.download_button(
                    label=f"⬇️ Descarregar {nome_arq}",
                    data=conteudo_bytes,
                    file_name=nome_arq,
                    mime="text/html",
                    use_container_width=True,
                    key=f"download_final_{nome_arq}",
                )


if __name__ == "__main__":
    main()
