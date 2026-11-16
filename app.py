import streamlit as st
import os
import json
import importlib
import urllib.parse
import requests
from pathlib import Path

# Configuração da página
st.set_page_config(page_title="LELD Docs Auditor", page_icon="🔒", layout="wide")

# =====================================================================
# 1. CONFIGURAÇÃO DE DIRETÓRIOS
# =====================================================================
PASTA_DADOS = Path("Dados")
PASTA_DADOS.mkdir(exist_ok=True)

# =====================================================================
# 2. CONFIGURAÇÃO DO LOGIN GOOGLE (SEM BIBLIOTECAS EXTRAS)
# =====================================================================
REDIRECT_URI = "https://leld-docs.streamlit.app/"

def obter_config_google():
    """Lê as credenciais do Streamlit Secrets ou do arquivo local."""
    if "google_credentials_json" in st.secrets:
        dados = json.loads(st.secrets["google_credentials_json"])
        return dados.get("web", dados)
    elif os.path.exists("client_secret.json"):
        with open("client_secret.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados.get("web", dados)
    else:
        st.error("❌ Credenciais OAuth do Google não encontradas nos Secrets.")
        st.stop()

def autenticar_usuario():
    """Gerencia o fluxo de login com @unesp.br usando apenas requests."""
    if "usuario_email" in st.session_state and st.session_state["usuario_email"]:
        return st.session_state["usuario_email"]

    client_config = obter_config_google()
    client_id = client_config["client_id"]
    client_secret = client_config["client_secret"]

    # Verifica se o Google acabou de redirecionar de volta com o código ("code")
    query_params = st.query_params
    if "code" in query_params:
        codigo = query_params["code"]
        try:
            # Troca o código pelo token de acesso
            token_url = "https://oauth2.googleapis.com/token"
            dados_token = {
                "code": codigo,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            }
            res_token = requests.post(token_url, data=dados_token)
            token_json = res_token.json()

            if "access_token" not in token_json:
                st.query_params.clear()
                st.error(f"Erro ao obter token: {token_json}")
                st.stop()

            # Busca o e-mail do usuário autenticado
            user_info_ res = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_json['access_token']}"}
            )
            user_info = user_info_res.json()
            email = user_info.get("email", "")

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

    # Monta a URL de login do Google
    params_auth = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params_auth)}"

    st.title("🔒 LELD Docs Auditor")
    st.info("Faça login com a sua conta institucional da **UNESP** (`@unesp.br`) para acessar o sistema.")
    
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

    if api_key_input:
        chave_limpa = api_key_input.strip()
        os.environ["GEMINI_API_KEY"] = chave_limpa
        os.environ["GOOGLE_API_KEY"] = chave_limpa
        st.session_state["GEMINI_API_KEY"] = chave_limpa
        
        # Cria/atualiza o arquivo .env temporário para o motor de auditoria ler sem erro
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
                chave_limpa = api_key_input.strip()
                os.environ["GEMINI_API_KEY"] = chave_limpa
                os.environ["GOOGLE_API_KEY"] = chave_limpa

                # Desativa sobrescrita vazia do python-dotenv, se estiver instalado
                try:
                    import dotenv
                    dotenv.load_dotenv = lambda *args, **kwargs: None
                except ImportError:
                    pass

                # Chama o script de auditoria do projeto
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
                    st.warning("Arquivo de auditoria principal não localizado automaticamente. Verifique o nome do script chamado.")

                st.success("✅ Auditoria concluída com sucesso!")

            except Exception as e:
                st.error(f"Erro durante a execução da auditoria: {e}")
