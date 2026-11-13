import streamlit as st
import json
import requests
import urllib.parse
import os

# Configuração da página - DEVE SER SEMPRE O PRIMEIRO COMANDO
st.set_page_config(page_title="LELD Docs Auditor", page_icon="🔒", layout="wide")

# --- INÍCIO DA CONFIGURAÇÃO DE SEGURANÇA (COFRE) ---
# Cria o arquivo de credenciais a partir do cofre (Secrets) ANTES de o ler
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
        # Converte as chaves em lista antes de aceder ao índice [0]
        client_type = list(creds_data.keys())[0] 
        CLIENT_ID = creds_data[client_type]['client_id']
        CLIENT_SECRET = creds_data[client_type]['client_secret']
        TOKEN_URI = creds_data[client_type].get('token_uri', 'https://oauth2.googleapis.com/token')
        AUTH_URI = creds_data[client_type].get('auth_uri', 'https://accounts.google.com/o/oauth2/auth')
except Exception as e:
    st.error(f"Erro ao carregar o ficheiro 'google_credentials.json': {e}")
    st.stop()

# ATUALIZADO: Usar a URL oficial do Streamlit em vez do localhost!
REDIRECT_URI = 'https://leld-docs.streamlit.app'

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
            f'<a href="{auth_url}" target="_self">'
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

                    # Validação automática para domínios da UNESP e o seu e-mail pessoal
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
            
            # Campo para o utilizador inserir a sua própria Chave da API do Google Gemini
            st.subheader("🔑 Configuração da API")
            user_api_key = st.text_input(
                "Insira a sua Google API Key", 
                type="password",
                help="Obtenha gratuitamente em aistudio.google.com"
            )
            
            if user_api_key:
                # Injeta a chave dinamicamente no ambiente para o main.py usar
                os.environ["GOOGLE_API_KEY"] = user_api_key
                st.success("Chave configurada com sucesso!")
            else:
                st.warning("⚠️ Insira a sua chave do Gemini para habilitar a auditoria.")

            st.divider()
            if st.button("🚪 Terminar Sessão", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                # Limpa a chave de API da memória ao sair
                if "GOOGLE_API_KEY" in os.environ:
                    del os.environ["GOOGLE_API_KEY"]
                st.query_params.clear()
                st.rerun()

        st.success("Acesso autorizado! Pode iniciar a preparação dos documentos.")
        st.subheader("📁 Gestão de Documentos para Auditoria")
        st.write("Faça o upload dos ficheiros PDF do docente abaixo. Eles substituirão automaticamente os anteriores na pasta `Dados/`.")

        # Garantir que a pasta Dados existe
        os.makedirs("Dados", exist_ok=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            lattes_file = st.file_uploader("Currículo Lattes (PDF)", type=["pdf"], key="lattes")
            if lattes_file:
                with open(os.path.join("Dados", "Lattes.pdf"), "wb") as f:
                    f.write(lattes_file.getbuffer())
                st.success("Lattes.pdf atualizado!")

        with col2:
            pubs_file = st.file_uploader("Publicações (PDF)", type=["pdf"], key="pubs")
            if pubs_file:
                with open(os.path.join("Dados", "Publicacoes.pdf"), "wb") as f:
                    f.write(pubs_file.getbuffer())
                st.success("Publicacoes.pdf atualizado!")

        with col3:
            eventos_file = st.file_uploader("Eventos (PDF)", type=["pdf"], key="eventos")
            if eventos_file:
                with open(os.path.join("Dados", "Eventos.pdf"), "wb") as f:
                    f.write(eventos_file.getbuffer())
                st.success("Eventos.pdf atualizado!")

        st.divider()

        # Validação cruzada: botão só executa se a chave existir no ambiente
        if st.button("🚀 Executar Auditoria Completa", use_container_width=True):
            if not os.environ.get("GOOGLE_API_KEY"):
                st.error("❌ Por favor, insira a sua Google API Key na barra lateral antes de executar a auditoria.")
            else:
                st.info("A executar o pipeline de auditoria... Acompanhe o progresso no terminal.")
                try:
                    with open("src/main.py", encoding="utf-8") as f:
                        code = f.read()
                    exec(code, {"__name__": "__main__", "__file__": "src/main.py"})
                    st.success("✨ Processamento de auditoria finalizado! Verifique a pasta Resultados.")
                except Exception as e:
                    st.error(f"Erro durante a execução da auditoria: {e}")

if __name__ == "__main__":
    main()