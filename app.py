import streamlit as st
import json
import requests
import urllib.parse
import os
import sys

# Configuração da página - DEVE SER SEMPRE O PRIMEIRO COMANDO
st.set_page_config(page_title="LELD Docs Auditor", page_icon="🔒", layout="wide")

# Importa os caminhos oficiais e o módulo principal do src/
if os.path.abspath("src") not in sys.path:
    sys.path.insert(0, os.path.abspath("src"))

from src.config import (
    CAMINHO_LATTES_PDF,
    CAMINHO_PUBLICACOES_PDF,
    CAMINHO_EVENTOS_PDF,
    ARQUIVO_SAIDA_PUBS_HTML,
    ARQUIVO_SAIDA_EVENTOS_HTML
)

# Tenta importar a função main do main.py para execução direta
try:
    import main as auditor_main
except ImportError:
    auditor_main = None

# --- INÍCIO DA CONFIGURAÇÃO DE SEGURANÇA (COFRE) ---
if not os.path.exists("google_credentials.json"):
    try:
        with open("google_credentials.json", "w") as f:
            f.write(st.secrets["google_credentials_json"])
    except Exception as e:
        st.error("Erro: O segredo 'google_credentials_json' não foi encontrado no painel do Streamlit.")
        st.stop()
# --- FIM DA CONFIGURAÇÃO DE SEGURANÇA ---

# Ler as credenciais diretamente do ficheiro google_credentials.json
try:
    with open('google_credentials.json', 'r') as f:
        creds_data = json.load(f)
        client_type = list(creds_data.keys())[0] 
        CLIENT_ID = creds_data[client_type]['client_id']
        CLIENT_SECRET = creds_data[client_type]['client_secret']
        TOKEN_URI = creds_data[client_type].get('token_uri', 'https://oauth2.googleapis.com/token')
        AUTH_URI = creds_data[client_type].get('auth_uri', 'https://accounts.google.com/o/oauth2/auth')
except Exception as e:
    st.error(f"Erro ao carregar o ficheiro 'google_credentials.json': {e}")
    st.stop()

REDIRECT_URI = 'https://leld-docs.streamlit.app'

def salvar_pdf_upload(uploaded_file, caminho_destino):
    """Garante que a pasta existe e salva o PDF exatamente onde o config.py espera."""
    pasta = os.path.dirname(caminho_destino)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(caminho_destino, "wb") as f:
        f.write(uploaded_file.getbuffer())

def main():
    st.title("🔒 LELD Docs Auditor")

    # Inicializar estados de sessão no Streamlit
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    # Se ainda não estiver autenticado, mostra o botão de login
    if not st.session_state.authenticated:
        st.info("Acesso restrito. Faça login com a sua conta institucional (@unesp.br).")

        auth_params = {
            'client_id': CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        auth_url = f"{AUTH_URI}?" + urllib.parse.urlencode(auth_params)

        st.markdown(
            f'<a href="{auth_url}" target="_blank">'
            f'<button style="background-color:#4285F4; color:white; padding:12px 24px; border:none; border-radius:6px; cursor:pointer; font-size:16px; font-weight:bold;">'
            f'🔑 Entrar com Google'
            f'</button></a>',
            unsafe_allow_html=True
        )

        query_params = st.query_params
        if 'code' in query_params:
            code = query_params['code']
            
            token_data = {
                'code': code,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI,
                'grant_type': 'authorization_code'
            }
            
            try:
                response = requests.post(TOKEN_URI, data=token_data)
                token_json = response.json()
                
                if response.status_code == 200:
                    access_token = token_json.get('access_token')
                    
                    user_response = requests.get(
                        'https://www.googleapis.com/oauth2/v2/userinfo',
                        headers={'Authorization': f'Bearer {access_token}'}
                    )
                    user_info = user_response.json()
                    email = user_info.get('email')

                    if email.endswith("@unesp.br") or email == "gilsonmarcondes@gmail.com":
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"O e-mail **{email}** não tem permissão. Apenas contas institucionais (@unesp.br) são aceites.")
                        st.query_params.clear()
                else:
                    st.error(f"Erro na autenticação com o Google: {token_json.get('error_description', token_json)}")
                    st.query_params.clear()
            except Exception as e:
                st.error(f"Erro de conexão ao validar o token: {e}")
                st.query_params.clear()

    else:
        # Área protegida: Utilizador autenticado com sucesso!
        with st.sidebar:
            st.success(f"Sessão iniciada como:\n**{st.session_state.user_email}**")
            st.divider()
            
            st.subheader("🔑 Configuração da API")
            user_api_key = st.text_input(
                "Insira a sua Google API Key", 
                type="password",
                help="Obtenha gratuitamente em aistudio.google.com"
            )
            
            if user_api_key:
                chave_limpa = user_api_key.strip()
                os.environ["GOOGLE_API_KEY"] = chave_limpa
                os.environ["GEMINI_API_KEY"] = chave_limpa
                
                with open(".env", "w", encoding="utf-8") as f_env:
                    f_env.write(f"GEMINI_API_KEY={chave_limpa}\n")
                    f_env.write(f"GOOGLE_API_KEY={chave_limpa}\n")
                    
                st.success("Chave configurada com sucesso!")
            else:
                st.warning("⚠️ Insira a sua chave do Gemini para habilitar a auditoria.")

            st.divider()
            if st.button("🚪 Terminar Sessão", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                for var in ["GOOGLE_API_KEY", "GEMINI_API_KEY"]:
                    if var in os.environ:
                        del os.environ[var]
                if os.path.exists(".env"):
                    os.remove(".env")
                st.query_params.clear()
                st.rerun()

        st.success("Acesso autorizado! Pode iniciar a preparação dos documentos.")
        st.subheader("📁 Gestão de Documentos para Auditoria")
        st.write("Faça o upload dos ficheiros PDF do docente abaixo.")

        col1, col2, col3 = st.columns(3)

        with col1:
            lattes_file = st.file_uploader("Currículo Lattes (PDF)", type=["pdf"], key="lattes")
            if lattes_file:
                salvar_pdf_upload(lattes_file, CAMINHO_LATTES_PDF)
                st.success(f"Salvo em: `{os.path.basename(CAMINHO_LATTES_PDF)}`")

        with col2:
            pubs_file = st.file_uploader("Publicações (PDF)", type=["pdf"], key="pubs")
            if pubs_file:
                salvar_pdf_upload(pubs_file, CAMINHO_PUBLICACOES_PDF)
                st.success(f"Salvo em: `{os.path.basename(CAMINHO_PUBLICACOES_PDF)}`")

        with col3:
            eventos_file = st.file_uploader("Eventos (PDF)", type=["pdf"], key="eventos")
            if eventos_file:
                salvar_pdf_upload(eventos_file, CAMINHO_EVENTOS_PDF)
                st.success(f"Salvo em: `{os.path.basename(CAMINHO_EVENTOS_PDF)}`")

        st.divider()

        # Botão de execução da auditoria
        if st.button("🚀 Executar Auditoria Completa", use_container_width=True):
            if not os.environ.get("GEMINI_API_KEY"):
                st.error("❌ Por favor, insira a sua Google API Key na barra lateral antes de executar a auditoria.")
            elif not auditor_main:
                st.error("❌ O módulo de auditoria (src/main.py) não foi localizado corretamente.")
            else:
                with st.spinner("⏳ A executar o pipeline de auditoria... Isso pode levar alguns minutos. Aguarde."):
                    try:
                        auditor_main.main()
                        st.session_state.auditoria_concluida = True
                        st.success("✨ Processamento de auditoria finalizado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro durante a execução da auditoria: {e}")

        # --- DOWNLOAD DIRETO AUTOMÁTICO DOS RELATÓRIOS OFICIAIS ---
        # Verifica se os relatórios HTML existem na raiz ou nas pastas esperadas e disponibiliza o download direto
        candidatos_relatorios = [
            ("Relatorio_Publicacoes.html", ARQUIVO_SAIDA_PUBS_HTML),
            ("Relatorio_Eventos.html", ARQUIVO_SAIDA_EVENTOS_HTML),
            ("relatorio_publicacoes.html", "relatorio_publicacoes.html"),
            ("relatorio_eventos.html", "relatorio_eventos.html")
        ]

        encontrados_para_baixar = []
        for nome_desc, caminho in candidatos_relatorios:
            if caminho and os.path.exists(caminho):
                encontrados_para_baixar.append((nome_desc, caminho))
            elif os.path.exists(nome_desc):
                encontrados_para_baixar.append((nome_desc, nome_desc))

        if encontrados_para_baixar:
            st.divider()
            st.subheader("📥 Clique abaixo para descarregar os relatórios gerados:")
            
            for idx, (nome_desc, caminho_real) in enumerate(encontrados_para_baixar):
                with open(caminho_real, "rb") as f_down:
                    dados_binarios = f_down.read()
                
                st.download_button(
                    label=f"⬇️ Descarregar {nome_desc} (Automático)",
                    data=dados_binarios,
                    file_name=nome_desc,
                    mime="text/html",
                    use_container_width=True,
                    key=f"download_direto_{idx}"
                )
    main()
