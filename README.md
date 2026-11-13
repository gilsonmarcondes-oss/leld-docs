# 🎓 LELD Docs (Versão Modular) - Auditoria Automatizada de Documentos Acadêmicos para Livre-Docência

O **LELD Docs Modular** é uma solução em Python refatorada para automatizar a triagem, classificação temporal, auditabilidade e sumarização quantitativa de documentos acadêmicos (Currículo Lattes, Publicações e Comprovantes de Eventos) para avaliação de inscrições em concursos de Livre-Docência.

A aplicação adota uma **arquitetura em duas fases**: varredura analítica fatiada em lotes por páginas reais com extração de dados estruturados em **JSON** (com suporte a checkpoints e recuperação de dados intermediários), seguida da consolidação e renderização programática dos relatórios finais em **HTML**.

---

## 🚀 Funcionalidades Principais

* **Arquitetura Modularizada**: Separação clara de responsabilidades em subpacotes (`extractors`, `security`, `services`, `templates`, `utils`) devidamente inicializados com `__init__.py`.
* **Varredura Analítica e Processamento em Lotes por Páginas Reais**: O script de auditoria fatia documentos PDF longos (Publicações e Eventos) em blocos configuráveis de páginas físicas (padrão: 25 páginas por lote via `paginas_por_lote`). Isso previne estouro da janela de contexto da LLM, reduz erros de extração e preserva o número da página física original (`pagina_pdf`) para auditoria.
* **Extração Estruturada em JSON (Fase 1)**: Uso de `system_instruction` rígida na API Gemini para forçar o retorno estrito de arrays JSON estruturados com chaves padronizadas (`docente`, `tipo_publicacao`/`tipo_evento`, `titulo`/`nome_evento`, `ano`, `condicao`/`papel`, `relacao_graduacao`, `pagina_pdf`).
* **Checkpoints e Recuperação de Dados Intermediários**: Salvamento automático de lotes de texto, cache de OCR e checkpoints JSON (`Dados/intermediarios/`) para garantir resiliência e evitar reprocessamentos em caso de interrupção.
* **Categorização Rígida de Eventos**: Classificação padronizada do Tipo de Participação em Eventos nas categorias: `Com Apresentação de Trabalho`, `Sem Apresentação / Ouvinte` e `Organizador / Comitê`.
* **Consolidação Programática em HTML (Fase 2)**: Os relatórios consolidados em HTML (Tabela 1 - Registros e Tabela 2 - Sumarização Quantitativa) são montados programaticamente pelo Python a partir dos dados em JSON, garantindo 100% de precisão nos totais e eliminação de alucinações.
* **Seleção Inteligente de Graduação**: Análise automática do Currículo Lattes para identificar a área do Doutorado e selecionar a Graduação com maior afinidade temática para ancorar o marco temporal de avaliação.
* **Processamento Híbrido e OCR Local**: Leitura direta do texto digital via `pypdf`. Em páginas escaneadas ou sem camada de texto legível (menos de 10 caracteres), dispara OCR local via `pdf2image` e `pytesseract` (Tesseract OCR), com cache em `Dados/intermediarios/ocr_cache/`.
* **Sanitização de Texto e Proteção Anti-Injection**: Higienização via expressão regular e normalização Unicode (NFKC) em `sanitizers.py`, neutralizando tentativas de Prompt Injection embutidas nos documentos PDF.
* **Resiliência e Backoff Exponencial (`AIService`)**: Tratamento robusto de limites de requisição e erros de cota HTTP com retentativas e tempo de espera progressivo.

---

## 📁 Estrutura do Projeto

```text
projeto_livre_docencia_modular/
│
├── Dados/                          # Arquivos de entrada e processamento
│   ├── brutos/                     # PDFs oficiais de entrada
│   │   ├── Lattes.pdf              # Currículo Lattes do docente
│   │   ├── Publicacoes.pdf         # Comprovantes / lista de publicações
│   │   └── Eventos.pdf             # Comprovantes / lista de eventos
│   ├── intermediarios/             # Dados intermediários, cache e checkpoints
│   │   ├── ocr_cache/              # Cache de OCR por página
│   │   ├── lotes_texto/            # Lotes de texto extraídos
│   │   └── json_checkpoints/       # Checkpoints JSON por lote de extração
│   └── ficticios/                  # Dados de simulação e mocks
│       ├── json_mock/
│       └── pdfs_mock/
│
├── Resultados/                     # Relatórios estáticos gerados em HTML
│   ├── Relatorio_Publicacoes.html  # Relatório consolidado de artigos e capítulos
│   └── Relatorio_Eventos.html      # Relatório consolidado de participações em eventos
│
├── src/                            # Código-fonte modularizado
│   ├── __init__.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   └── pdf_extractor.py        # Extração de PDF e OCR local (Tesseract)
│   ├── security/
│   │   ├── __init__.py
│   │   └── sanitizers.py           # Sanitização regex, NFKC e remoção de injetores
│   ├── services/
│   │   ├── __init__.py
│   │   └── ai_service.py           # Cliente SDK google-genai com retentativas/backoff
│   ├── templates/
│   │   ├── __init__.py
│   │   └── prompts.py              # System instructions e construtores de prompts
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py           # Leitura/escrita e salvamento dos relatórios HTML
│   ├── config.py                   # Central de caminhos, ambiente e modelo Gemini
│   └── main.py                     # Orquestrador principal do pipeline
│
├── .env                            # Variáveis de ambiente (Chave GEMINI_API_KEY e DATA_MODE)
├── .gitignore                      # Proteção de credenciais e PDFs locais
├── pytest.ini                      # Configuração de suítes de testes automatizados
├── requirements.txt                # Dependências do projeto
└── README.md                       # Documentação do projeto
```
---

## 🛠️ Tecnologias Utilizadas

* **Linguagem**: Python 3.10+
* **IA / LLM**: SDK Oficial Google GenAI (`google-genai==2.29.0`), utilizando por padrão o modelo `gemini-3.5-flash-lite`
* **Processamento de PDF**: `pypdf==6.20.0`
* **OCR Local**: `pytesseract==0.3.13` e `pdf2image==1.17.0` (Tesseract OCR)
* **Gerenciamento de Ambiente**: `python-dotenv==1.2.4`
* **Modelagem e Validação**: `pydantic==2.14.0` e `tenacity==9.1.4`

---

## 📋 Pré-requisitos

1. Python 3.10 ou superior instalado.
2. **Tesseract OCR** e **Poppler** instalados no sistema operacional.
3. Chave de API ativa do Google Gemini (`GEMINI_API_KEY`).
4. Arquivos PDF posicionados no diretório `Dados/brutos/` (ou fallback na raiz de `Dados/`):
   * `Lattes.pdf`
   * `Publicacoes.pdf`
   * `Eventos.pdf`

---

## ⚙️ Instalação e Configuração

1. **Clonar o repositório e acessar a pasta**:
   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd projeto_livre_docencia_modular
   ```

2. **Criar e ativar o ambiente virtual**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # No Linux/macOS
   # ou no Windows:
   # .venv\Scripts\activate
   ```

3. **Instalar as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar o arquivo `.env` na raiz do projeto**:
   ```env
   GEMINI_API_KEY=sua_chave_aqui
   DATA_MODE=brutos  # ou 'ficticios' para modo mock
   ```

---

## 🏃 Execução

Para iniciar o pipeline completo de auditoria acadêmica em lote:

```bash
python src/main.py
```

O fluxo executará sequencialmente:
1. Leitura das primeiras páginas de `Lattes.pdf` para definir o marco temporal da graduação.
2. Varredura analítica de `Publicacoes.pdf` em lotes de 25 páginas reais com geração de array JSON acumulado e salvamento de checkpoints.
3. Renderização e gravação de `Resultados/Relatorio_Publicacoes.html`.
4. Varredura analítica de `Eventos.pdf` em lotes de 25 páginas reais com geração de array JSON acumulado e salvamento de checkpoints.
5. Renderização e gravação de `Resultados/Relatorio_Eventos.html`.

---

## 🌐 Visualização dos Resultados

Os relatórios gerados estarão disponíveis na pasta `Resultados/`:
* `Relatorio_Publicacoes.html`: Tabela detalhada de publicações (com indicação da página física do PDF, tipo, autoria e temporalidade) e Tabela 2 de sumarização quantitativa.
* `Relatorio_Eventos.html`: Tabela detalhada de eventos e Tabela 2 de sumarização quantitativa.

Basta abri-los em qualquer navegador web.
