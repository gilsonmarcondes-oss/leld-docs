import streamlit as st
import os
import json
import sys
import importlib
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import dotenv

# Configuração da página (baseada no layout do seu print)
st.set_page_config(page_title="LELD Docs Auditor", page_icon="🔒", layout="wide")

# =====================================================================
# 1. CONFIGURAÇÃO DE DIRETÓRIOS
# =====================================================================
PASTA_DADOS = Path("Dados")
PASTA_DADOS.mkdir(exist_ok=True)

# =====================================================================
# 2. CONFIGURAÇÃO DO LOGIN GOOGLE (OAUTH 2.0)
# =====================================================================
REDIRECT_URI = "https://leld-docs.streamlit.app/"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

def obter_config_google():
    """Lê as credenciais do Streamlit Secrets ou do arquivo local."""
    if "google_credentials_json" in st.secrets:
        return json.loads(st.secrets["google_credentials_json"])
    elif os.path.exists("client_secret.json"):
        with open("client_secret.json", "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        st.error("❌ Credenciais OAuth do Google não encontradas nos Secrets.")
        st.stop()

def autenticar_usuario():
    """Gerencia o fluxo de login com @unesp.br."""
    if "usuario_email" in st.session_state and st.session_state["usuario_email"]:
        return st.session_state["usuario_email"]

    # Verifica se o Google acabou de redirecionar de volta com o código ("code")
    query_params = st.query_params
    if "code" in query_params:
        try:
            client_config = obter_config_google()
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            flow.fetch_token(code=query_params["code"])
            credentials = flow.credentials

            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                client_config["web"]["client_id"]
            )
            email = id_info.get("email", "")

            # Limpa o parâmetro "code" da URL para não dar erro ao atualizar a página
            st.query_params.clear()

            if email.endswith("@unesp.br"):
                st.session_state["usuario_email"] = email
                st.rerun()
            else:
                st.error("🚫 Acesso restrito! Utilize o seu e-mail institucional (@unesp.br).")
                st.stop()
        except Exception as e:
            st.query_params.clear()
            st.error(f"Erro ao validar o login com o Google: {e}")
            st.stop()

    # Se ainda não está logado, mostra o botão de login
    client_config = obter_config_google()
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, _ = flow.authorization_url(prompt="select_account")

    st.title("🔒 LELD Docs Auditor")
    st.info("Faça login com a sua conta institucional da **UNESP** (`@unesp.br`) para acessar o sistema.")
    
    # target="_top" evita o erro 403 do iframe do Streamlit
    st.markdown(
        f'<a href="{auth_url}" target="_top" style="display:inline-block; padding:10px 20px; '
        f'background-color:#0b57d0; color:white; text-decoration:none; border-radius:6px; font-weight:bold;">'
        f'🔑 Entrar com Google (@unesp.br)</a>',
        unsafe_allow_html=True
    )
    st.stop()

# =====================================================================
# 3. EXECUÇÃO DO LOGIN E BARRA LATERAL (SIDEBAR)
# =====================================================================
email_logado = autenticar_usuario()

with st.sidebar:
    st.success(f"Sessão iniciada como:\n**{email_logado}**")
    st.divider()
    st.subheader("🔑 Configuração da API")
    
    api_key_input = st.text_input(
        "Insira a sua Google API Key",
        type="password",
        help="Cole aqui a sua chave gerada no Google AI Studio e pressione Enter."
    )

    # BLINDAGEM DA CHAVE API: Assim que você digita, ele injeta no sistema E cria o .env temporário
    if api_key_input:
        chave_limpa = api_key_input.strip()
        os.environ["GEMINI_API_KEY"] = chave_limpa
        os.environ["GOOGLE_API_KEY"] = chave_limpa
        st.session_state["GEMINI_API_KEY"] = chave_limpa
        
        # Cria/atualiza o arquivo .env no servidor para o script de auditoria não reclamar!
        with open(".env", "w", encoding="utf-8") as f_env:
            f_env.write(f"GEMINI_API_KEY={chave_limpa}\n")
            f_env.write(f"GOOGLE_API_KEY={chave_limpa}\n")
            
        st.success("✅ Chave do Gemini carregada!")
    else:
        st.warning("⚠️ Insira a sua chave do Gemini para habilitar a auditoria.")

    st.divider()
    if st.button("🚪 Terminar Sessão", use_container_width=True):
        st.session_state.clear()
        if os.path.exists(".env"):
            os.remove(".env")
        st.rerun()

# =====================================================================
# 4. ÁREA PRINCIPAL: UPLOAD DE DOCUMENTOS E AUDITORIA
# =====================================================================
st.title("🔒 LELD Docs Auditor")
st.success("Acesso autorizado! Pode iniciar a preparação dos documentos.")

st.subheader("📁 Gestão de Documentos para Auditoria")
st.markdown("Faça o upload dos ficheiros PDF do docente abaixo. Eles substituirão automaticamente os anteriores na pasta `Dados/`.")

col1, col2, col3 = st.columns(3)

with col1:
    pdf_lattes = st.file_uploader("Currículo Lattes (PDF)", type=["pdf"], key="up_lattes")
    if pdf_lattes:
        with open(PASTA_DADOS / "curriculo_lattes.pdf", "wb") as f:
            f.write(pdf_lattes.getbuffer())
        st.caption("✅ Currículo salvo em `Dados/`")

with col2:
    pdf_pub = st.file_uploader("Publicações (PDF)", type=["pdf"], key="up_pub")
    if pdf_pub:
        with open(PASTA_DADOS / "publicacoes.pdf", "wb") as f:
            f.write(pdf_pub.getbuffer())
        st.caption("✅ Publicações salvas em `Dados/`")

with col3:
    pdf_eventos = st.file_uploader("Eventos (PDF)", type=["pdf"], key="up_eventos")
    if pdf_eventos:
        with open(PASTA_DADOS / "eventos.pdf", "wb") as f:
            f.write(pdf_eventos.getbuffer())
        st.caption("✅ Eventos salvos em `Dados/`")

st.divider()

# Botão de Execução da Auditoria
if st.button("🚀 Executar Auditoria Completa", use_container_width=True, disabled=not api_key_input):
    if not api_key_input:
        st.error("❌ Por favor, insira a sua chave da API do Gemini na barra lateral esquerda antes de iniciar.")
    else:
        with st.spinner("⏳ Executando a auditoria dos documentos... Isso pode levar alguns instantes."):
            try:
                # Garante mais uma vez que a chave está no ambiente e no .env antes de chamar o motor
                chave_limpa = api_key_input.strip()
                os.environ["GEMINI_API_KEY"] = chave_limpa
                os.environ["GOOGLE_API_KEY"] = chave_limpa
                
                # Desativa o override do load_dotenv caso o script externo tente apagar a variável
                dotenv.load_dotenv = lambda *args, **kwargs: None

                # =================================================================
                # IMPORTAÇÃO E CHAMADA DO SEU SCRIPT DE AUDITORIA
                # (Se no seu app.py original o nome da função ou arquivo for diferente,
                # basta manter a linha de chamada que você já usava aqui dentro!)
                # =================================================================
                if os.path.exists("auditor.py"):
                    import auditor
                    importlib.reload(auditor)
                    if hasattr(auditor, "executar_auditoria"):
                        resultado = auditor.executar_auditoria()
                        if resultado:
                            st.write(resultado)
                    elif hasattr(auditor, "main"):
                        resultado = auditor.main()
                        if resultado:
                            st.write(resultado)
                elif os.path.exists("main.py"):
                    import main as script_auditoria
                    importlib.reload(script_auditoria)
                    if hasattr(script_auditoria, "main"):
                        resultado = script_auditoria.main()
                        if resultado:
                            st.write(resultado)
                else:
                    st.info("Chave configurada! Verifique o nome do script de auditoria chamado no botão.")

                st.success("✅ Auditoria concluída com sucesso!")

            except Exception as e:
                st.error(f"Erro durante a execução da auditoria: {e}")
