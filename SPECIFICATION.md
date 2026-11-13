# 🏗️ Especificação Técnica e Blueprint de Reconstrução: LELD Docs (Versão Modular)

Este documento contém a especificação técnica completa obtida por engenharia reversa do projeto **LELD Docs (Versão Modular)**. Ele serve como um **blueprint executável** para permitir a recriação integral e idêntica do código-fonte, arquitetura, contratos de dados e salvaguardas por um agente de IA ou desenvolvedor.

---

## 1. Visão Geral e Objetivo do Sistema

* **Finalidade**: Automatizar a triagem, classificação temporal, auditabilidade página a página e sumarização quantitativa de documentos acadêmicos (Currículo Lattes, Comprovantes de Publicações e Comprovantes de Eventos) para concursos de Livre-Docência.
* **Arquitetura de Processamento**: Processamento em duas fases:
  1. **Fase 1 (Varredura Analítica & Extração JSON)**: Fatiamento de documentos extensos por blocos de páginas físicas reais (padrão de 25 páginas por lote) e extração estruturada via modelo de linguagem (LLM Google Gemini) em formato JSON estrito.
  2. **Fase 2 (Consolidação & Renderização HTML)**: Consolidação programática em Python dos arrays JSON acumulados e geração dos relatórios finais estáticos em HTML (Tabela 1 - Registros com indicação de página físico; Tabela 2 - Sumarização Quantitativa Anterior/Posterior).
* **Entradas Locais**: Arquivos PDF posicionados no diretório `Dados/` (`Lattes.pdf`, `Publicacoes.pdf`, `Eventos.pdf`).
* **Saídas Geradas**: Arquivos HTML gravados no diretório `Resultados/` (`Relatorio_Publicacoes.html`, `Relatorio_Eventos.html`).

---

## 2. Árvore de Arquivos e Responsabilidade dos Módulos

```text
projeto_livre_docencia_modular/
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
├── README.md
├── SPECIFICATION.md
├── Dados/
│   ├── Lattes.pdf
│   ├── Publicacoes.pdf
│   └── Eventos.pdf
├── Resultados/
│   ├── Relatorio_Publicacoes.html
│   └── Relatorio_Eventos.html
└── src/
    ├── __init__.py
    ├── config.py
    ├── main.py
    ├── extractors/
    │   ├── __init__.py
    │   └── pdf_extractor.py
    ├── security/
    │   ├── __init__.py
    │   └── sanitizers.py
    ├── services/
    │   ├── __init__.py
    │   └── ai_service.py
    ├── templates/
    │   ├── __init__.py
    │   └── prompts.py
    └── utils/
        ├── __init__.py
        └── file_utils.py
```

---

## 3. Especificações Técnicas Módulo a Módulo

### 3.1 `src/config.py` — Central de Configurações e Caminhos
* **Dependências**: `os`, `dotenv.load_dotenv`
* **Comportamento**:
  1. Carrega o arquivo `.env` localizado na raiz do projeto via `load_dotenv()`.
  2. Obtém a variável `GEMINI_API_KEY`. Se ausente, lança `ValueError("❌ A variável GEMINI_API_KEY não foi configurada no arquivo .env")`.
  3. Define `MODELOS_DISPONIVEIS = ["gemini-3.8-flash"]`.
  4. Ancoragem dinâmica dos caminhos:
     * `DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))`
     * `DIR_DADOS = os.path.abspath(os.path.join(DIRETORIO_BASE, "..", "Dados"))`
     * `DIR_RESULTADOS = os.path.abspath(os.path.join(DIRETORIO_BASE, "..", "Resultados"))`
     * `CAMINHO_LATTES_PDF = os.path.join(DIR_DADOS, "Lattes.pdf")`
     * `CAMINHO_PUBLICACOES_PDF = os.path.join(DIR_DADOS, "Publicacoes.pdf")`
     * `CAMINHO_EVENTOS_PDF = os.path.join(DIR_DADOS, "Eventos.pdf")`
     * `ARQUIVO_SAIDA_PUBS_HTML = os.path.join(DIR_RESULTADOS, "Relatorio_Publicacoes.html")`
     * `ARQUIVO_SAIDA_EVENTOS_HTML = os.path.join(DIR_RESULTADOS, "Relatorio_Eventos.html")`

### 3.2 `src/security/sanitizers.py` — Sanitização e Anti-Prompt Injection
* **Dependências**: `re`, `unicodedata`
* **Função**: `sanitizar_texto_para_prompt(texto: str) -> str`
* **Comportamento**:
  1. Retorna string vazia se `texto` for nulo/vazio.
  2. Executa normalização Unicode `NFKC`: `unicodedata.normalize("NFKC", texto)`.
  3. Remove caracteres de controle não imprimíveis: `re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", texto_sanitizado)`.
  4. Neutraliza fecho/abertura de tags wrappers XML inserindo placeholders `[TAG_FECHAMENTO_IGNORADA]` e `[TAG_ABERTURA_IGNORADA]`.
  5. Substitui padrões conhecidos de Prompt Injection por `[TEXTO_SUSPEITO_REMOVIDO]` utilizando expressões regulares insensíveis a maiúsculas/minúsculas:
     * Comandos de ignorar instruções anteriores (PT e EN).
     * Identificadores de papéis (`system:`, `user:`, `assistant:`, `[INST]`, `<|im_start|>`, etc.).
     * Alterações forçadas de formato de saída ou concessão de autoria indevida.

### 3.3 `src/extractors/pdf_extractor.py` — Extração de PDF e Fallback de OCR Local
* **Dependências**: `pypdf.PdfReader`, `pytesseract`, `pdf2image.convert_from_path`
* **Função**: `extrair_texto_pdf_com_ocr(caminho_pdf: str) -> tuple[int, str]`
* **Comportamento**:
  1. Lê o PDF via `PdfReader`.
  2. Itera sobre cada página (índice base 1). Extrai texto direto via `pagina.extract_text()`.
  3. Se `len(texto_pagina.strip()) < 10`, executa fallback de OCR local chamando `convert_from_path(caminho_pdf, first_page=idx, last_page=idx)` e processa a imagem com `pytesseract.image_to_string(imagem, lang="por+eng")`.
  4. Retorna a contagem total de páginas e a string com os trechos anotados por `--- PÁGINA X ---`.

### 3.4 `src/services/ai_service.py` — Cliente SDK Gemini com Backoff Exponencial
* **Dependências**: `time`, `google.genai`, `google.genai.errors.APIError`, `google.genai.types`, `config.GEMINI_API_KEY`
* **Classe**: `AIService`
  * `__init__(self)`: Instancia `self.client = genai.Client(api_key=GEMINI_API_KEY)`.
  * `executar_requisicao_com_retry(self, modelo: str, prompt: str, instrucao_sistema: str = None, max_tentativas: int = 5)`:
    * Executa chamadas a `self.client.models.generate_content` com `config=types.GenerateContentConfig(temperature=0.0, system_instruction=...)`.
    * Em caso de `APIError` com código HTTP `429`, `500`, `502`, `503`, `504`, executa retentativa com *exponential backoff* (espera inicial de 15 segundos, multiplicando por 2 a cada tentativa).


### 3.5 `src/templates/prompts.py` — Instruções de Sistema e Prompts
* **Instruções de Sistema**:
  * `INSTRUCAO_SISTEMA_LATTES`: Define papel de auditor de Currículo Lattes para extrair `TEMA_DOUTORADO`, `GRADUACAO_SELECIONADA` e `ANO_GRADUACAO` em chave-valor.
  * `INSTRUCAO_SISTEMA_JSON_PUBS`: Força o retorno estrito de array JSON com chaves: `docente`, `tipo_publicacao` ("Artigo em Periódico" | "Capítulo de Livro"), `titulo`, `ano`, `condicao`, `relacao_graduacao` ("Anterior" | "Posterior"), `pagina_pdf`.
  * `INSTRUCAO_SISTEMA_JSON_EVENTOS`: Força o retorno estrito de array JSON com chaves: `docente`, `tipo_evento`, `nome_evento`, `papel` ("Com Apresentação de Trabalho" | "Sem Apresentação / Ouvinte" | "Organizador / Comitê"), `ano`, `relacao_graduacao` ("Anterior" | "Posterior"), `pagina_pdf`.
* **Construtores de Prompts**:
  * `get_prompt_lattes(texto_sanitizado)`
  * `get_prompt_publicacoes(...)`
  * `get_prompt_eventos(...)`

### 3.6 `src/utils/file_utils.py` — Manipulação de Arquivos e HTML
* **Função**: `salvar_arquivo_html(texto_resposta: str, caminho_destino: str)`
* **Comportamento**:
  1. Cria o diretório pai caso não exista (`os.makedirs(pasta, exist_ok=True)`).
  2. Extrai o conteúdo HTML de blocos Markdown (```html ... ```) via expressão regular `re.search(r"```html\s*(.*?)\s*```", texto_resposta, re.DOTALL)`.
  3. Grava o arquivo com encoding `utf-8`.

### 3.7 `src/main.py` — Orquestrador do Pipeline em Duas Fases
* **Funções-Chave**:
  1. `extrair_texto_por_paginas(caminho_pdf, paginas_por_lote=25)`: Divide o documento PDF em blocos de páginas físicas mantendo os delimitadores `--- PÁGINA X ---`.
  2. `processar_lattes(ai_service, caminho_lattes)`: Analisa as primeiras 10 páginas de `Lattes.pdf` e extrai 4 tuplas (`nome_docente`, `ano_grad`, `grad_selecionada`, `tema_doutorado`) via regex flexível.
  3. `processar_lotes_json(...)`: Itera sobre cada lote de 25 páginas com extração segura via regex `\[.*\]`, faz parseamento com `json.loads` e acumula os registros no array Python global.
  4. `gerar_html_publicacoes(...)` / `gerar_html_eventos(...)`: Renderiza programaticamente as tabelas HTML:
     - **Eventos**: Tabela 1 traz a coluna *Tipo de Participação*; Tabela 2 exibe a sumarização cruzada quantitativa entre Tipo de Participação (`Com Apresentação de Trabalho`, `Sem Apresentação / Ouvinte`, `Organizador / Comitê`) e temporalidade (`Anterior à Graduação` / `Posterior`).
  5. `main()`: Orquestra a execução sequencial com resiliência a arquivos ausentes e resumo estruturado final.

---

## 4. Arquivos de Suporte e Ambiente

### 4.1 `requirements.txt`
```text
annotated-types==0.8.0
anyio==4.15.1
beautifulsoup4==4.15.0
certifi==2026.7.22
cffi==2.1.1
charset-normalizer==3.5.2
cryptography==50.0.2
distro==1.9.0
fonttools
google==3.0.0
google-auth==2.61.0
google-genai==2.29.0
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.20
load-dotenv==0.1.0
packaging==26.3
pdf2image==1.17.0
pillow
pyasn1==0.6.4
pyasn1_modules==0.4.2
pycparser==3.11
pydantic==2.14.0
pydantic_core==2.50.0
pypdf==6.20.0
pytesseract==0.3.13
python-dotenv==1.2.4
requests==2.34.2
sniffio==1.3.1
soupsieve==2.10
tenacity==9.1.4
typing-inspection==0.4.4
typing_extensions==4.16.0
urllib3==2.8.0
websockets==16.1.1
```

### 4.2 `.env.example`
```env
GEMINI_API_KEY=sua_chave_api_aqui
```

### 4.3 `.gitignore`
```gitignore
# Credenciais e Variáveis de Ambiente
.env
*.env

# Ambientes Virtuais
.venv/
env/
venv/

# Arquivos de dados de entrada e resultados (PDFs e HTMLs gerados)
Dados/
Resultados/

# Cache e arquivos temporários do Python
__pycache__/
*.pyc
*.pyo
*.pyd

# Configurações de IDEs e Editores
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Logs
*.log
```

---

## 5. Diretrizes para Reconstrução Automatizada por IA

1. **Ordem de Geração**:
   - Passo 1: `.env.example`, `.gitignore`, `requirements.txt` e `README.md`.
   - Passo 2: `src/config.py` (garantindo resolução dinâmica de caminhos).
   - Passo 3: `src/security/sanitizers.py` (aplicando NFKC e regex anti-injection).
   - Passo 4: `src/extractors/pdf_extractor.py` (com fallback para Tesseract OCR).
   - Passo 5: `src/services/ai_service.py` (usando `google-genai` e backoff exponencial).
   - Passo 6: `src/templates/prompts.py` (com contratos de saída JSON estritos).
   - Passo 7: `src/utils/file_utils.py` (escrita de HTML).
   - Passo 8: `src/main.py` (unificando a varredura em lotes de 25 páginas e renderização programática).
2. **Garantia de Qualidade**:
   - Todo o parseamento de JSON deve ser defensivo (`try / except json.JSONDecodeError` com remoção de marcações markdown ````json`).
   - A montagem das tabelas HTML (Tabela 1 e Tabela 2) deve ocorrer exclusivamente no Python a partir dos dados do JSON acumulado, nunca solicitando a renderização final diretamente à LLM.

