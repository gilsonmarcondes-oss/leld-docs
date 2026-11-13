# 🏗️ Especificação Técnica e Blueprint de Reconstrução: LELD Docs (Versão Modular)

Este documento contém a especificação técnica completa obtida por engenharia reversa do projeto **LELD Docs (Versão Modular)**. Ele serve como um **blueprint executável** para permitir a recriação integral e idêntica do código-fonte, arquitetura, contratos de dados e salvaguardas por um agente de IA ou desenvolvedor.

---

## 1. Visão Geral e Objetivo do Sistema

* **Finalidade**: Automatizar a triagem, classificação temporal, auditabilidade página a página e sumarização quantitativa de documentos acadêmicos (Currículo Lattes, Comprovantes de Publicações e Comprovantes de Eventos) para concursos de Livre-Docência.
* **Arquitetura de Processamento**: Processamento em duas fases:
  1. **Fase 1 (Varredura Analítica & Extração JSON)**: Fatiamento de documentos extensos por blocos de páginas físicas reais (padrão de 25 páginas por lote) e extração estruturada via modelo de linguagem (LLM Google Gemini) em formato JSON estrito, com salvamento de checkpoints intermediários.
  2. **Fase 2 (Consolidação & Renderização HTML)**: Consolidação programática em Python dos arrays JSON acumulados e geração dos relatórios finais estáticos em HTML (Tabela 1 - Registros com indicação de página físico; Tabela 2 - Sumarização Quantitativa Anterior/Posterior).
* **Entradas Locais**: Arquivos PDF posicionados no diretório `Dados/brutos/` (`Lattes.pdf`, `Publicacoes.pdf`, `Eventos.pdf`) com suporte a fallback na raiz de `Dados/` e modo simulado (`Dados/ficticios/`).
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
│   ├── brutos/
│   │   ├── Lattes.pdf
│   │   ├── Publicacoes.pdf
│   │   └── Eventos.pdf
│   ├── intermediarios/
│   │   ├── ocr_cache/
│   │   ├── lotes_texto/
│   │   └── json_checkpoints/
│   └── ficticios/
│       ├── json_mock/
│       └── pdfs_mock/
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

### 3.1 `src/config.py` — Central de Configurações, Caminhos e Checkpoints
* **Dependências**: `os`, `dotenv.load_dotenv`
* **Comportamento**:
  1. Carrega o arquivo `.env` localizado na raiz do projeto via `load_dotenv()`.
  2. Obtém a variável `GEMINI_API_KEY`. Se ausente, lança `ValueError("❌ A variável GEMINI_API_KEY não foi configurada no arquivo .env")`.
  3. Define `MODELOS_DISPONIVEIS = ["gemini-3.5-flash-lite"]`.
  4. Configura `DATA_MODE` (`brutos` ou `ficticios`) e diretórios de dados intermediários (`ocr_cache`, `lotes_texto`, `json_checkpoints`).
  5. Ancoragem dinâmica dos caminhos e fallback inteligente para arquivos PDF.

### 3.2 `src/security/sanitizers.py` — Sanitização e Anti-Prompt Injection
* **Função Principal**: `sanitizar_texto(texto: str) -> str`
* **Comportamento**: Normalização Unicode (NFKC), remoção de caracteres de controle e neutralização de padrões suspeitos de instrução (Prompt Injection) embutidos em PDFs.

### 3.3 `src/extractors/pdf_extractor.py` — Extração Híbrida e Cache OCR
* **Funções**:
  * Leitura direta via `pypdf`.
  * Detecção de páginas escaneadas (< 10 caracteres) e disparo de OCR local via `pdf2image` e `pytesseract`.
  * Armazenamento em cache (`ocr_cache/`) para reuso.
  * Divisão e marcação de páginas delimitadas por `--- PÁGINA X ---`.

### 3.4 `src/services/ai_service.py` — Cliente SDK Gemini com Backoff Exponencial
* **Dependências**: `time`, `google.genai`, `google.genai.errors.APIError`, `google.genai.types`, `config.GEMINI_API_KEY`
* **Classe**: `AIService`
  * `__init__(self)`: Instancia `self.client = genai.Client(api_key=GEMINI_API_KEY)`.
  * `executar_requisicao_com_retry(...)`: Executa chamadas com `temperature=0.0`, system instruction e backoff exponencial em erros HTTP de cota/limite.

### 3.5 `src/templates/prompts.py` — Instruções de Sistema e Prompts
* **Instruções de Sistema**:
  * `INSTRUCAO_SISTEMA_LATTES`: Extração de `TEMA_DOUTORADO`, `GRADUACAO_SELECIONADA` e `ANO_GRADUACAO`.
  * `INSTRUCAO_SISTEMA_JSON_PUBS` e `INSTRUCAO_SISTEMA_JSON_EVENTOS`: Formato estrito JSON com indicação de página física.

### 3.6 `src/utils/file_utils.py` — Manipulação de Arquivos e HTML
* **Função**: `salvar_arquivo_html(texto_resposta: str, caminho_destino: str)`
* **Comportamento**: Extração de blocos ````html ... ```` e salvamento codificado em `utf-8`.

### 3.7 `src/main.py` — Orquestrador do Pipeline em Duas Fases com Checkpoints
* **Funções-Chave**:
  1. `extrair_texto_por_paginas(...)`
  2. `processar_lattes(...)`
  3. `processar_lotes_json(...)`: Itera em lotes de 25 páginas, validando checkpoints em `json_checkpoints/`.
  4. Geração programática dos relatórios em `Resultados/` (`Relatorio_Publicacoes.html`, `Relatorio_Eventos.html`).
  5. Resumo e contagem estatística precisa.

---

## 4. Arquivos de Suporte e Ambiente

### 4.1 `requirements.txt`
* Contém todas as dependências fixadas (`google-genai==2.29.0`, `pypdf==6.20.0`, `pytesseract==0.3.13`, `pdf2image==1.17.0`, etc.).
