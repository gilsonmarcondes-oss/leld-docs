import pypdf
import pytesseract
from pdf2image import convert_from_path


def extrair_texto_pagina_com_ocr(caminho_pdf: str, indice_pagina: int) -> str:
    """
    Extrai o texto de uma página específica do PDF (índice 0-based).
    Tenta primeiro a leitura digital via pypdf. Se houver menos de 10 caracteres,
    dispara o Tesseract OCR como fallback.
    """
    num_pagina_exibicao = indice_pagina + 1

    try:
        reader = pypdf.PdfReader(caminho_pdf)
        if indice_pagina < len(reader.pages):
            texto_pypdf = (reader.pages[indice_pagina].extract_text() or "").strip()
            # Se a extração digital nativa capturou conteúdo suficiente, utiliza diretamente
            if len(texto_pypdf) >= 10:
                return texto_pypdf
    except Exception as e:
        print(f"⚠️ Erro ao extrair texto digital da pág {num_pagina_exibicao}: {e}")
        texto_pypdf = ""

    # Fallback para OCR se a página for escaneada ou tiver pouco texto pesquisável
    texto_ocr = ""
    try:
        imagens = convert_from_path(
            caminho_pdf,
            first_page=num_pagina_exibicao,
            last_page=num_pagina_exibicao,
            dpi=200
        )
        if imagens:
            texto_ocr = pytesseract.image_to_string(
                imagens[0],
                lang="por+eng"
            ).strip()
    except Exception as e:
        print(f"⚠️ Erro ao executar OCR na pág {num_pagina_exibicao}: {e}")

    # Retorna o texto do OCR se disponível, caso contrário o texto do pypdf
    return texto_ocr if texto_ocr else texto_pypdf


def extrair_texto_por_paginas(caminho_pdf: str, paginas_por_lote: int = 25):
    """
    Extrai o texto do PDF agrupando por blocos de páginas físicas reais (padrão de 25 por lote).
    Processa cada página exatamente uma vez com tratamento isolado de exceções.
    """
    reader = pypdf.PdfReader(caminho_pdf)
    total_paginas = len(reader.pages)
    lotes_paginas = []

    for i in range(0, total_paginas, paginas_por_lote):
        fim = min(i + paginas_por_lote, total_paginas)
        texto_lote = ""

        for num_pag in range(i, fim):
            try:
                texto_pag = extrair_texto_pagina_com_ocr(caminho_pdf, num_pag)
                if texto_pag and texto_pag.strip():
                    texto_lote += f"\n--- PÁGINA {num_pag + 1} ---\n" + texto_pag
            except Exception as err:
                print(f"⚠️ [Pág {num_pag + 1}] Erro isolado na extração/OCR da página: {err}. Continuando lote...")

        lotes_paginas.append({
            "pagina_inicio": i + 1,
            "pagina_fim": fim,
            "texto": texto_lote
        })

    return total_paginas, lotes_paginas
