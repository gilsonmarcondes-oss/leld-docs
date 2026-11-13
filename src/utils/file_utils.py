import os
import re

def salvar_arquivo_html(texto_resposta: str, caminho_destino: str):
    """Extrai o código HTML da resposta e salva no disco."""
    pasta_destino = os.path.dirname(caminho_destino)
    if pasta_destino and not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino, exist_ok=True)

    padrao_html = re.search(r"```html\s*(.*?)\s*```", texto_resposta, re.DOTALL)
    conteudo_html = padrao_html.group(1) if padrao_html else texto_resposta

    with open(caminho_destino, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo_html)

    print(f"\n🌐 Arquivo HTML gerado com sucesso em:\n   {os.path.abspath(caminho_destino)}")
