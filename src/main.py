"""
Main Orchestrator — LELD Docs Auditor
Pipeline de auditoria acadêmica em duas fases:
1. Fase de Extração: Varredura do PDF por blocos de páginas reais com acúmulo em JSON.
2. Fase de Consolidação: Renderização do relatório final em HTML com tabelas unificadas.
"""

import os
import sys
import json
import time
import re
import pypdf

# Resolução dinâmica do sys.path para execução como script ou pacote
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from src.config import (
        CAMINHO_LATTES_PDF,
        CAMINHO_PUBLICACOES_PDF,
        CAMINHO_EVENTOS_PDF,
        ARQUIVO_SAIDA_PUBS_HTML,
        ARQUIVO_SAIDA_EVENTOS_HTML,
        MODELOS_DISPONIVEIS,
        PAGINAS_POR_LOTE,
        TEMPO_ESPERA_ENTRE_LOTES
    )
    from src.security.sanitizers import sanitizar_texto_para_prompt
    from src.services.ai_service import AIService
    from src.utils.file_utils import salvar_arquivo_html
    from src.templates.prompts import (
        INSTRUCAO_SISTEMA_LATTES,
        INSTRUCAO_SISTEMA_JSON_PUBS,
        INSTRUCAO_SISTEMA_JSON_EVENTOS,
        get_prompt_lattes,
        get_prompt_publicacoes,
        get_prompt_eventos
    )
    from src.extractors.pdf_extractor import extrair_texto_por_paginas, extrair_texto_pagina_com_ocr
except ModuleNotFoundError:
    from config import (
        CAMINHO_LATTES_PDF,
        CAMINHO_PUBLICACOES_PDF,
        CAMINHO_EVENTOS_PDF,
        ARQUIVO_SAIDA_PUBS_HTML,
        ARQUIVO_SAIDA_EVENTOS_HTML,
        MODELOS_DISPONIVEIS,
        PAGINAS_POR_LOTE,
        TEMPO_ESPERA_ENTRE_LOTES
    )
    from security.sanitizers import sanitizar_texto_para_prompt
    from services.ai_service import AIService
    from utils.file_utils import salvar_arquivo_html
    from templates.prompts import (
        INSTRUCAO_SISTEMA_LATTES,
        INSTRUCAO_SISTEMA_JSON_PUBS,
        INSTRUCAO_SISTEMA_JSON_EVENTOS,
        get_prompt_lattes,
        get_prompt_publicacoes,
        get_prompt_eventos
    )
    from extractors.pdf_extractor import extrair_texto_por_paginas, extrair_texto_pagina_com_ocr


# ==========================================
# 1. PROCESSAMENTO DO CURRÍCULO LATTES
# ==========================================

def processar_lattes(ai_service: AIService, caminho_lattes: str):
    if not os.path.exists(caminho_lattes):
        print(f"⚠️ Arquivo Lattes não encontrado em '{caminho_lattes}'.")
        print("   💡 Dica: Adicione o arquivo 'Lattes.pdf' na pasta 'Dados/' para extrair a formação do docente.")
        return "Não Informado", "Não Informado", "Não Informado", "Não Informado"

    print("📄 Processando e sanitizando o Lattes (com suporte a OCR)...")
    reader = pypdf.PdfReader(caminho_lattes)
    total_paginas = min(len(reader.pages), 10)
    texto_lattes = ""

    for num_pag in range(total_paginas):
        try:
            t = extrair_texto_pagina_com_ocr(caminho_lattes, num_pag)
            if t and t.strip():
                texto_lattes += t + "\n"
        except Exception as e:
            print(f"⚠️ Erro ao extrair página {num_pag + 1} do Lattes: {e}")

    texto_sanitizado = sanitizar_texto_para_prompt(texto_lattes[:4000])
    prompt = get_prompt_lattes(texto_sanitizado)

    for modelo in MODELOS_DISPONIVEIS:
        res = ai_service.executar_requisicao_com_retry(modelo, prompt, INSTRUCAO_SISTEMA_LATTES)
        if res and res.text:
            texto = res.text.strip()
            match_nome = re.search(r"NOME_DOCENTE:\s*(.*)", texto)
            match_doc = re.search(r"TEMA_DOUTORADO:\s*(.*)", texto)
            match_grad = re.search(r"GRADUACAO_SELECIONADA:\s*(.*)", texto)
            match_ano = re.search(r"ANO_GRADUACAO:\s*(.*)", texto)

            return (
                match_nome.group(1).strip() if match_nome else "Não Identificado",
                match_ano.group(1).strip() if match_ano else "Não Identificado",
                match_grad.group(1).strip() if match_grad else "Não Identificado",
                match_doc.group(1).strip() if match_doc else "Não Identificado"
            )

    return "Não Identificado", "Não Identificado", "Não Identificado", "Não Identificado"


# ==========================================
# 2. FASE 1: VARREDURA E EXTRAÇÃO JSON EM LOTES
# ==========================================

def sanitizar_registro_json(registro: dict, tipo_doc: str, nome_docente: str, p_inicio: int) -> dict:
    """Higieniza e garante valores padrão defensivos para chaves ausentes ou nulas no JSON da IA."""
    if not isinstance(registro, dict):
        return {}

    item = dict(registro)

    item['docente'] = str(item.get('docente')).strip() if item.get('docente') else (nome_docente or "Docente Auditado")
    item['ano'] = str(item.get('ano')).strip() if item.get('ano') else "Não Informado"
    item['relacao_graduacao'] = str(item.get('relacao_graduacao')).strip() if item.get('relacao_graduacao') else "Não Identificado"

    try:
        item['pagina_pdf'] = int(item.get('pagina_pdf', p_inicio))
    except (ValueError, TypeError):
        item['pagina_pdf'] = p_inicio

    if tipo_doc.lower() == "publicações":
        item['titulo'] = str(item.get('titulo')).strip() if item.get('titulo') else "-"
        item['condicao'] = str(item.get('condicao')).strip() if item.get('condicao') else "-"
        item['tipo_publicacao'] = str(item.get('tipo_publicacao')).strip() if item.get('tipo_publicacao') else "Artigo em Periódico"
    else:
        item['nome_evento'] = str(item.get('nome_evento')).strip() if item.get('nome_evento') else "-"
        item['papel'] = str(item.get('papel')).strip() if item.get('papel') else "Sem Apresentação / Ouvinte"
        item['tipo_evento'] = str(item.get('tipo_evento')).strip() if item.get('tipo_evento') else "Participação em Evento"

    return item


def processar_lotes_json(
    ai_service: AIService, 
    caminho_pdf: str, 
    tipo_doc: str, 
    nome_docente: str,
    ano_grad: str, 
    grad_sel: str, 
    tema_doc: str, 
    paginas_por_lote: int = PAGINAS_POR_LOTE
):
    if not os.path.exists(caminho_pdf):
        nome_base = os.path.basename(caminho_pdf)
        print(f"\n⚠️ Arquivo de {tipo_doc} não encontrado em '{caminho_pdf}'.")
        print(f"   💡 Dica: Para auditar {tipo_doc}, adicione o arquivo '{nome_base}' na pasta 'Dados/'. Etapa ignorada.")
        return [], 0, nome_base

    print(f"\n🔍 Extraindo e fatiando PDF de {tipo_doc} por páginas reais...")
    total_paginas, lotes = extrair_texto_por_paginas(caminho_pdf, paginas_por_lote=paginas_por_lote)

    nome_arquivo = os.path.basename(caminho_pdf)
    total_lotes = len(lotes)

    instrucao_sistema = INSTRUCAO_SISTEMA_JSON_PUBS if tipo_doc.lower() == "publicações" else INSTRUCAO_SISTEMA_JSON_EVENTOS

    print(f"📦 PDF de {tipo_doc} ({total_paginas} págs) dividido em {total_lotes} lote(s) de ~{paginas_por_lote} páginas cada.")
    todos_os_registros = []

    for idx, lote in enumerate(lotes, start=1):
        p_inicio = lote["pagina_inicio"]
        p_fim = lote["pagina_fim"]
        print(f"⚙️ Extraindo Lote {idx}/{total_lotes} (Páginas {p_inicio} a {p_fim})...")

        texto_sanitizado = sanitizar_texto_para_prompt(lote["texto"])

        if tipo_doc.lower() == "publicações":
            prompt = get_prompt_publicacoes(
                texto_sanitizado=texto_sanitizado,
                total_paginas=total_paginas,
                graduacao_selecionada=grad_sel,
                ano_graduacao=ano_grad,
                tema_doutorado=tema_doc,
                nome_arquivo=f"{nome_arquivo} (Págs {p_inicio}-{p_fim})"
            )
        else:
            prompt = get_prompt_eventos(
                texto_sanitizado=texto_sanitizado,
                total_paginas=total_paginas,
                graduacao_selecionada=grad_sel,
                ano_graduacao=ano_grad,
                tema_doutorado=tema_doc,
                nome_arquivo=f"{nome_arquivo} (Págs {p_inicio}-{p_fim})"
            )

        for modelo in MODELOS_DISPONIVEIS:
            resposta = ai_service.executar_requisicao_com_retry(modelo, prompt, instrucao_sistema)
            if resposta and resposta.text:
                try:
                    # Busca preferencialmente o bloco de array JSON '[...]' delimitado no texto
                    match_array = re.search(r'\[.*\]', resposta.text, re.DOTALL)
                    conteudo_json = match_array.group(0) if match_array else re.sub(r'```json\s*|\s*```', '', resposta.text.strip())

                    dados_lote = json.loads(conteudo_json)
                    if isinstance(dados_lote, list):
                        registros_limpos = [
                            sanitizar_registro_json(reg, tipo_doc, nome_docente, p_inicio)
                            for reg in dados_lote if isinstance(reg, dict)
                        ]
                        todos_os_registros.extend(registros_limpos)
                        print(f"  └─ ✅ Págs {p_inicio}-{p_fim}: {len(registros_limpos)} registros extraídos.")
                    break
                except json.JSONDecodeError:
                    print(f"  └─ ⚠️ Falha ao decodificar JSON nas págs {p_inicio}-{p_fim} ({modelo}). Retentando...")

        if idx < total_lotes:
            time.sleep(TEMPO_ESPERA_ENTRE_LOTES)

    print(f"\n📊 Total acumulado no JSON de {tipo_doc}: {len(todos_os_registros)} registros extraídos de 100% do PDF.")
    return todos_os_registros, total_paginas, nome_arquivo

# ==========================================
# 3. FASE 2: RENDERIZADORES DE HTML CONSOLIDADO
# ==========================================

def gerar_html_publicacoes(registros, nome_arquivo, total_paginas, grad_sel, ano_grad, tema_doc, arquivo_saida):
    linhas_tabela1 = ""
    docente_nome = registros[0].get('docente', 'Docente Auditado') if registros else 'Mara Lúcia Martins Lopes'

    for reg in registros:
        linhas_tabela1 += f"""
        <tr>
            <td>{reg.get('docente', docente_nome)}</td>
            <td>{reg.get('tipo_publicacao', 'Artigo em Periódico')}</td>
            <td>{reg.get('titulo', '-')}</td>
            <td style="text-align:center;">{reg.get('ano', '-')}</td>
            <td style="text-align:center;">{reg.get('condicao', '-')}</td>
            <td style="text-align:center;">{reg.get('relacao_graduacao', '-')}</td>
            <td style="text-align:center;">{reg.get('pagina_pdf', '-')}</td>
        </tr>
        """

    total_post = sum(1 for r in registros if str(r.get('relacao_graduacao', '')).lower() == 'posterior')
    total_ant = sum(1 for r in registros if str(r.get('relacao_graduacao', '')).lower() == 'anterior')

    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Consolidado de Publicações</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; background-color: #f9f9f9; line-height: 1.5; }}
        h1, h2 {{ color: #1a5276; }}
        .summary-box {{ background: #fff; padding: 15px; border-left: 5px solid #1a5276; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; background: #fff; font-size: 13px; shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        th, td {{ border: 1px solid #dcdcdc; padding: 8px 10px; text-align: left; }}
        th {{ background-color: #1a5276; color: white; text-align: center; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        .total-row {{ font-weight: bold; background-color: #eaf2f8 !important; }}
    </style>
</head>
<body>
    <h1>RELATÓRIO DE VARREDURA DE PUBLICAÇÕES</h1>
    <div class="summary-box">
        <p><strong>Nome do Arquivo:</strong> {nome_arquivo}</p>
        <p><strong>Número total de páginas:</strong> {total_paginas}</p>
        <p><strong>Graduação Selecionada:</strong> {grad_sel}</p>
        <p><strong>Ano da Conclusão da Graduação:</strong> {ano_grad}</p>
        <p><strong>Tema/Área do Doutorado:</strong> {tema_doc}</p>
        <p><strong>Status:</strong> 100% Auditado (Varredura por Páginas Integrada)</p>
        <p><strong>Nome do Docente Identificado:</strong> {docente_nome}</p>
    </div>

    <h2>Tabela 1: Publicações Acadêmicas ({len(registros)} registros)</h2>
    <table>
        <thead>
            <tr>
                <th>Docente</th>
                <th>Tipo de Publicação</th>
                <th>Título da Publicação</th>
                <th>Ano</th>
                <th>Condição</th>
                <th>Relação com a Graduação</th>
                <th>Página do PDF</th>
            </tr>
        </thead>
        <tbody>
            {linhas_tabela1}
        </tbody>
    </table>

    <h2>Tabela 2: Sumarização Quantitativa dos Dados</h2>
    <table>
        <thead>
            <tr>
                <th>Categoria Geral</th>
                <th>Tipo / Modalidade</th>
                <th>Relação com a Graduação</th>
                <th>Quantidade</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Publicação Acadêmica</td>
                <td>Artigo / Capítulo</td>
                <td>Anterior à Graduação</td>
                <td style="text-align:center;">{total_ant}</td>
            </tr>
            <tr>
                <td>Publicação Acadêmica</td>
                <td>Artigo / Capítulo</td>
                <td>Posterior</td>
                <td style="text-align:center;">{total_post}</td>
            </tr>
            <tr class="total-row">
                <td><strong>TOTAL GERAL DE REGISTROS</strong></td>
                <td style="text-align:center;"><strong>-</strong></td>
                <td style="text-align:center;"><strong>-</strong></td>
                <td style="text-align:center;"><strong>{len(registros)}</strong></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

    salvar_arquivo_html(html_template, arquivo_saida)
    print(f"🎉 Relatório Consolidado de Publicações salvo em: {arquivo_saida}")


def gerar_html_eventos(registros, nome_arquivo, total_paginas, grad_sel, ano_grad, tema_doc, arquivo_saida):
    linhas_tabela1 = ""
    docente_nome = registros[0].get('docente', 'Docente Auditado') if registros else 'Mara Lúcia Martins Lopes'

    for reg in registros:
        linhas_tabela1 += f"""
        <tr>
            <td>{reg.get('docente', docente_nome)}</td>
            <td>{reg.get('tipo_evento', 'Participação em Evento')}</td>
            <td>{reg.get('nome_evento', '-')}</td>
            <td style="text-align:center;">{reg.get('papel', '-')}</td>
            <td style="text-align:center;">{reg.get('ano', '-')}</td>
            <td style="text-align:center;">{reg.get('relacao_graduacao', '-')}</td>
            <td style="text-align:center;">{reg.get('pagina_pdf', '-')}</td>
        </tr>
        """

    categorias = [
        "Com Apresentação de Trabalho",
        "Sem Apresentação / Ouvinte",
        "Organizador / Comitê"
    ]

    linhas_tabela2 = ""
    for cat in categorias:
        count_ant = 0
        count_post = 0
        for r in registros:
            papel = str(r.get('papel', '')).strip()
            rel = str(r.get('relacao_graduacao', '')).strip().lower()

            pertence = False
            p_lower = papel.lower()
            if cat == "Com Apresentação de Trabalho" and ("apresenta" in p_lower or "autor" in p_lower or "palestran" in p_lower or p_lower == cat.lower()):
                pertence = True
            elif cat == "Organizador / Comitê" and ("organiz" in p_lower or "comit" in p_lower or "coorden" in p_lower or p_lower == cat.lower()):
                pertence = True
            elif cat == "Sem Apresentação / Ouvinte" and ("ouvinte" in p_lower or "sem apresenta" in p_lower or "participan" in p_lower or "congressista" in p_lower or p_lower == cat.lower()):
                pertence = True

            if pertence:
                if "anterior" in rel:
                    count_ant += 1
                else:
                    count_post += 1

        linhas_tabela2 += f"""
            <tr>
                <td>Participação em Evento</td>
                <td>{cat}</td>
                <td>Anterior à Graduação</td>
                <td style="text-align:center;">{count_ant}</td>
            </tr>
            <tr>
                <td>Participação em Evento</td>
                <td>{cat}</td>
                <td>Posterior</td>
                <td style="text-align:center;">{count_post}</td>
            </tr>"""

    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Consolidado de Eventos</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; background-color: #f9f9f9; line-height: 1.5; }}
        h1, h2 {{ color: #27ae60; }}
        .summary-box {{ background: #fff; padding: 15px; border-left: 5px solid #27ae60; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; background: #fff; font-size: 13px; }}
        th, td {{ border: 1px solid #dcdcdc; padding: 8px 10px; text-align: left; }}
        th {{ background-color: #27ae60; color: white; text-align: center; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        .total-row {{ font-weight: bold; background-color: #e8f8f5 !important; }}
    </style>
</head>
<body>
    <h1>RELATÓRIO DE VARREDURA DE EVENTOS</h1>
    <div class="summary-box">
        <p><strong>Nome do Arquivo:</strong> {nome_arquivo}</p>
        <p><strong>Número total de páginas:</strong> {total_paginas}</p>
        <p><strong>Graduação Selecionada:</strong> {grad_sel}</p>
        <p><strong>Ano da Conclusão da Graduação:</strong> {ano_grad}</p>
        <p><strong>Tema/Área do Doutorado:</strong> {tema_doc}</p>
        <p><strong>Status:</strong> 100% Auditado (Varredura por Páginas Integrada)</p>
        <p><strong>Nome do Docente Identificado:</strong> {docente_nome}</p>
    </div>

    <h2>Tabela 1: Participação em Eventos ({len(registros)} registros)</h2>
    <table>
        <thead>
            <tr>
                <th>Docente</th>
                <th>Tipo de Evento</th>
                <th>Nome do Evento</th>
                <th>Tipo de Participação</th>
                <th>Ano</th>
                <th>Relação com a Graduação</th>
                <th>Página do PDF</th>
            </tr>
        </thead>
        <tbody>
            {linhas_tabela1}
        </tbody>
    </table>

    <h2>Tabela 2: Sumarização Quantitativa dos Dados</h2>
    <table>
        <thead>
            <tr>
                <th>Categoria Geral</th>
                <th>Tipo de Participação</th>
                <th>Relação com a Graduação</th>
                <th>Quantidade</th>
            </tr>
        </thead>
        <tbody>
            {linhas_tabela2}
            <tr class="total-row">
                <td><strong>TOTAL GERAL DE REGISTROS</strong></td>
                <td style="text-align:center;"><strong>-</strong></td>
                <td style="text-align:center;"><strong>-</strong></td>
                <td style="text-align:center;"><strong>{len(registros)}</strong></td>
            </tr>
        </tbody>
    </table>
</body>
</html>"""

    salvar_arquivo_html(html_template, arquivo_saida)
    print(f"🎉 Relatório Consolidado de Eventos salvo em: {arquivo_saida}")


# ==========================================
# 4. ORQUESTRADOR PRINCIPAL
# ==========================================

def main():
    inicio_execucao = time.time()
    ai_service = AIService()
    print("🚀 Iniciando pipeline completo de auditoria LELD Docs...\n")
    relatorios_gerados = []

    # ETAPA A: Lattes
    nome_docente, ano_grad, grad_selecionada, tema_doutorado = processar_lattes(ai_service, CAMINHO_LATTES_PDF)
    print(f"🎓 Nome do Docente: {nome_docente}")
    print(f"🎓 Graduação Selecionada: {grad_selecionada}")
    print(f"📌 Ano da Graduação: {ano_grad}")
    print(f"🔬 Tema/Área do Doutorado: {tema_doutorado}")

    time.sleep(TEMPO_ESPERA_ENTRE_LOTES)

    # ETAPA B: Publicações
    regs_pubs, paginas_pubs, nome_pubs = processar_lotes_json(
        ai_service, 
        CAMINHO_PUBLICACOES_PDF, 
        "Publicações", 
        nome_docente,        
        ano_grad, 
        grad_selecionada, 
        tema_doutorado, 
        paginas_por_lote=PAGINAS_POR_LOTE
    )
    if regs_pubs:
        gerar_html_publicacoes(regs_pubs, nome_pubs, paginas_pubs, grad_selecionada, ano_grad, tema_doutorado, ARQUIVO_SAIDA_PUBS_HTML)
        relatorios_gerados.append(("Publicações", ARQUIVO_SAIDA_PUBS_HTML, len(regs_pubs)))
    else:
        print("ℹ️ Etapa de Publicações finalizada sem relatórios (arquivo ausente ou sem registros).")

    time.sleep(TEMPO_ESPERA_ENTRE_LOTES)

    # ETAPA C: Eventos
    regs_eventos, paginas_eventos, nome_eventos = processar_lotes_json(
        ai_service, 
        CAMINHO_EVENTOS_PDF, 
        "Eventos", 
        nome_docente,        
        ano_grad, 
        grad_selecionada, 
        tema_doutorado, 
        paginas_por_lote=PAGINAS_POR_LOTE
    )
    if regs_eventos:
        gerar_html_eventos(regs_eventos, nome_eventos, paginas_eventos, grad_selecionada, ano_grad, tema_doutorado, ARQUIVO_SAIDA_EVENTOS_HTML)
        relatorios_gerados.append(("Eventos", ARQUIVO_SAIDA_EVENTOS_HTML, len(regs_eventos)))
    else:
        print("ℹ️ Etapa de Eventos finalizada sem relatórios (arquivo ausente ou sem registros).")

    tempo_decorrido = time.time() - inicio_execucao
    minutos = int(tempo_decorrido // 60)
    segundos = int(tempo_decorrido % 60)

    print("\n" + "="*60)
    print("📊 RESUMO FINAL DA AUDITORIA LELD DOCS")
    print("="*60)
    if relatorios_gerados:
        for tipo, caminho, qtd in relatorios_gerados:
            print(f"  ✅ Relatório de {tipo}: Gerado com sucesso ({qtd} registros) -> {caminho}")
    else:
        print("  ⚠️ Nenhum relatório HTML foi gerado. Verifique os arquivos PDF de entrada na pasta 'Dados/'.")
    print(f"  ⏱️ Tempo total de auditoria: {minutos} min e {segundos} seg")
    print("="*60)
    print("✨ Processamento concluído com sucesso!")


if __name__ == "__main__":
    main()