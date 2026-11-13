import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ A variável GEMINI_API_KEY não foi configurada no arquivo .env")

MODELOS_DISPONIVEIS = ["gemini-3.5-flash-lite"]

# Configurações de Lote e Execução
PAGINAS_POR_LOTE = 25
TEMPO_ESPERA_ENTRE_LOTES = 10

# Modo de Dados ('brutos' ou 'ficticios')
DATA_MODE = os.getenv("DATA_MODE", "brutos")

# Direcionamento de Caminhos
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))

DIR_DADOS = os.path.abspath(os.path.join(DIRETORIO_BASE, "..", "Dados"))
DIR_DADOS_BRUTOS = os.path.join(DIR_DADOS, "brutos")
DIR_DADOS_INTERMEDIARIOS = os.path.join(DIR_DADOS, "intermediarios")
DIR_DADOS_FICTICIOS = os.path.join(DIR_DADOS, "ficticios")

DIR_OCR_CACHE = os.path.join(DIR_DADOS_INTERMEDIARIOS, "ocr_cache")
DIR_LOTES_TEXTO = os.path.join(DIR_DADOS_INTERMEDIARIOS, "lotes_texto")
DIR_JSON_CHECKPOINTS = os.path.join(DIR_DADOS_INTERMEDIARIOS, "json_checkpoints")

os.makedirs(DIR_OCR_CACHE, exist_ok=True)
os.makedirs(DIR_LOTES_TEXTO, exist_ok=True)
os.makedirs(DIR_JSON_CHECKPOINTS, exist_ok=True)

# Definição dos caminhos de entrada com suporte a modo fictício e fallback
if DATA_MODE == "ficticios":
    CAMINHO_LATTES_PDF = os.path.join(DIR_DADOS_FICTICIOS, "pdfs_mock", "Lattes_mock.pdf")
    CAMINHO_PUBLICACOES_PDF = os.path.join(DIR_DADOS_FICTICIOS, "pdfs_mock", "Publicacoes_mock.pdf")
    CAMINHO_EVENTOS_PDF = os.path.join(DIR_DADOS_FICTICIOS, "pdfs_mock", "Eventos_mock.pdf")
else:
    CAMINHO_LATTES_PDF = os.path.join(DIR_DADOS_BRUTOS, "Lattes.pdf")
    CAMINHO_PUBLICACOES_PDF = os.path.join(DIR_DADOS_BRUTOS, "Publicacoes.pdf")
    CAMINHO_EVENTOS_PDF = os.path.join(DIR_DADOS_BRUTOS, "Eventos.pdf")
    
    # Fallback para raiz de Dados caso não estejam em brutos
    if not os.path.exists(CAMINHO_LATTES_PDF) and os.path.exists(os.path.join(DIR_DADOS, "Lattes.pdf")):
        CAMINHO_LATTES_PDF = os.path.join(DIR_DADOS, "Lattes.pdf")
    if not os.path.exists(CAMINHO_PUBLICACOES_PDF) and os.path.exists(os.path.join(DIR_DADOS, "Publicacoes.pdf")):
        CAMINHO_PUBLICACOES_PDF = os.path.join(DIR_DADOS, "Publicacoes.pdf")
    if not os.path.exists(CAMINHO_EVENTOS_PDF) and os.path.exists(os.path.join(DIR_DADOS, "Eventos.pdf")):
        CAMINHO_EVENTOS_PDF = os.path.join(DIR_DADOS, "Eventos.pdf")

DIR_RESULTADOS = os.path.abspath(os.path.join(DIRETORIO_BASE, "..", "Resultados"))
os.makedirs(DIR_RESULTADOS, exist_ok=True)

ARQUIVO_SAIDA_PUBS_HTML = os.path.join(DIR_RESULTADOS, "Relatorio_Publicacoes.html")
ARQUIVO_SAIDA_EVENTOS_HTML = os.path.join(DIR_RESULTADOS, "Relatorio_Eventos.html")