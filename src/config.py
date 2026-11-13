import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ A variável GEMINI_API_KEY não foi configurada no arquivo .env")

MODELOS_DISPONIVEIS = ["gemini-3.5-flash-lite", "gemini-3.5-turbo", "gemini-3.5-turbo-16k", "gemini-3.5-turbo-32k"]

# Configurações de Lote e Execução
PAGINAS_POR_LOTE = 25
TEMPO_ESPERA_ENTRE_LOTES = 10


# Direcionamento de Caminhos
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))

DIR_DADOS = os.path.abspath(os.path.join(DIRETORIO_BASE, "..", "Dados"))
DIR_RESULTADOS = os.path.abspath(os.path.join(DIRETORIO_BASE, "..", "Resultados"))

CAMINHO_LATTES_PDF = os.path.join(DIR_DADOS, "Lattes.pdf")
CAMINHO_PUBLICACOES_PDF = os.path.join(DIR_DADOS, "Publicacoes.pdf")
CAMINHO_EVENTOS_PDF = os.path.join(DIR_DADOS, "Eventos.pdf")

ARQUIVO_SAIDA_PUBS_HTML = os.path.join(DIR_RESULTADOS, "Relatorio_Publicacoes.html")
ARQUIVO_SAIDA_EVENTOS_HTML = os.path.join(DIR_RESULTADOS, "Relatorio_Eventos.html")