import gc
import pypdf
import pytesseract
from pdf2image import convert_from_path


def extrair_texto_pagina_com_ocr(
    caminho_pdf: str,
    indice_pagina: int,
    reader: pypdf.PdfReader = None,
) -> str:
    """
    Extrai o texto de uma página específica do PDF (índice 0-based).
    Reutiliza o 'reader' já aberto para não duplicar o PDF na memória RAM.
    """
    num_pagina_exibicao = indice_pagina + 1
    texto_pypdf = ""

    try:
        leitor = reader if reader is not None else pypdf.PdfReader(caminho_pdf)
        if indice_pagina < len(leitor.pages):
            texto_pypdf = (leitor.pages[indice_pagina].extract_text() or "").strip()
            if len(texto_pypdf) >= 10:
                return texto_pypdf
    except Exception as e:
        print(f"⚠️ Erro ao extrair texto digital da pág {num_pagina_exibicao}: {e}")
        texto_pypdf = ""

    # Fallback para OCR (em escala de cinza e 150 DPI para economizar RAM)
    texto_ocr = ""
    imagens = None
    try:
        imagens = convert_from_path(
            caminho_pdf,
            first_page=num_pagina_exibicao,
            last_page=num_pagina_exibicao,
            dpi=150,
            grayscale=True,
        )
        if imagens:
            texto_ocr = pytesseract.image_to_string(
                imagens[0],
                lang="por+eng",
            ).strip()
    except Exception as e:
        print(f"⚠️ Erro ao executar OCR na pág {num_pagina_exibicao}: {e}")
    finally:
        if imagens:
            for img in imagens:
                img.close()
            del imagens
        gc.collect()

    return texto_ocr if texto_ocr else texto_pypdf


def extrair_texto_por_paginas(caminho_pdf: str, paginas_por_lote: int = 25):
    """
    Extrai o texto do PDF agrupando por blocos de páginas físicas reais.
    Abre o arquivo uma única vez e libera a memória ao final.
    """
    reader = pypdf.PdfReader(caminho_pdf)
    total_paginas = len(reader.pages)
    lotes_paginas = []

    try:
        for i in range(0, total_paginas, paginas_por_lote):
            fim = min(i + paginas_por_lote, total_paginas)
            texto_lote = ""

            for num_pag in range(i, fim):
                try:
                    texto_pag = extrair_texto_pagina_com_ocr(
                        caminho_pdf, num_pag, reader=reader
                    )
                    if texto_pag and texto_pag.strip():
                        texto_lote += f"\n--- PÁGINA {num_pag + 1} ---\n" + texto_pag
                except Exception as err:
                    print(
                        f"⚠️ [Pág {num_pag + 1}] Erro isolado na extração/OCR da página: {err}. Continuando lote..."
                    )

            lotes_paginas.append(
                {
                    "pagina_inicio": i + 1,
                    "pagina_fim": fim,
                    "texto": texto_lote,
                }
            )
    finally:
        del reader
        gc.collect()

    return total_paginas, lotes_paginas
