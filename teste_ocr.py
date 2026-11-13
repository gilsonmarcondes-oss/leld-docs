import pypdf
import pytesseract
from pdf2image import convert_from_path
import os

CAMINHO_EVENTOS = "Dados/Eventos.pdf"  # Ajuste o caminho se necessário

if not os.path.exists(CAMINHO_EVENTOS):
    print(f"❌ Arquivo não encontrado em: {CAMINHO_EVENTOS}")
    exit()

print("🚀 TESTANDO OCR FORÇADO NO EVENTOS.PDF...")

reader = pypdf.PdfReader(CAMINHO_EVENTOS)
print(f"📄 Total de Páginas: {len(reader.pages)}")

# Testando na Página 1
print("\n--- Testando Página 1 ---")
try:
    print("1. Tentando pdf2image / Poppler...")
    imagens = convert_from_path(CAMINHO_EVENTOS, first_page=1, last_page=1, dpi=200)
    print(f"   ✅ Imagem convertida com sucesso! Qtd imagens: {len(imagens)}")
    
    print("2. Tentando Tesseract OCR...")
    texto_ocr = pytesseract.image_to_string(imagens[0], lang="por")
    print("\n--- TEXTO EXTRAÍDO PELO TESSERACT NA PÁGINA 1 ---")
    print(texto_ocr[:500])  # Mostra os primeiros 500 caracteres
    print("-------------------------------------------------")
    
except Exception as e:
    print(f"❌ ERRO GRAVE NO TESSERACT OU POPPLER: {e}")


    # ==========================================
# 1. EXTRAÇÃO DE TEXTO POR PÁGINAS REAIS
# ==========================================

def extrair_texto_por_paginas(caminho_pdf: str, paginas_por_lote: int = 25):
    """
    Extrai o texto do PDF agrupando por blocos de páginas físicas reais.
    Evita cortes arbitrários no meio de publicações ou citações.
    """
    reader = pypdf.PdfReader(caminho_pdf)
    total_paginas = len(reader.pages)
    lotes_paginas = []

    for i in range(0, total_paginas, paginas_por_lote):
        fim = min(i + paginas_por_lote, total_paginas)
        texto_lote = ""
        for num_pag in range(i, fim):
            texto_pag = reader.pages[num_pag].extract_text()
            if texto_pag:
                texto_lote += f"\n--- PÁGINA {num_pag + 1} ---\n" + texto_pag
        
        lotes_paginas.append({
            "pagina_inicio": i + 1,
            "pagina_fim": fim,
            "texto": texto_lote
        })

    return total_paginas, lotes_paginas