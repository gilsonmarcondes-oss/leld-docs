import pytest
from src.templates.prompts import get_prompt_publicacoes

def test_construcao_prompt_publicacoes_sintetico():
    texto_sanitizado = "Artigo Publicado em 2022 por Silva, J."
    prompt_resultado = get_prompt_publicacoes(
        texto_sanitizado=texto_sanitizado,
        total_paginas=5,
        graduacao_selecionada="Engenharia de Software",
        ano_graduacao="2018",
        tema_doutorado="Inteligência Computacional",
        nome_arquivo="Publicacoes.pdf"
    )
    
    # Verifica a presença das âncoras de contexto no prompt gerado
    assert "Engenharia de Software" in prompt_resultado
    assert "2018" in prompt_resultado
    assert "Inteligência Computacional" in prompt_resultado
    assert "<document_data>" in prompt_resultado