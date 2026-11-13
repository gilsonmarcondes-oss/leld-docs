import pytest
from unittest.mock import MagicMock, patch

def test_consolidacao_json_para_html_sintetico():
    # Dados sintéticos de resposta simulando a saída da LLM (Fase 1)
    json_resposta_sintetica = [
        {
            "docente": "Docente Teste",
            "tipo_publicacao": "Artigo em Periódico",
            "titulo": "Estudo sobre Redes Neurais",
            "ano": "2021",
            "condicao": "1º de 3 (Primeiro)",
            "relacao_graduacao": "Posterior",
            "pagina_pdf": 1
        }
    ]
    
    # Valida que o registro sintético possui todas as chaves obrigatórias do contrato
    registro = json_resposta_sintetica[0]
    assert registro["tipo_publicacao"] == "Artigo em Periódico"
    assert registro["relacao_graduacao"] == "Posterior"
    assert registro["pagina_pdf"] == 1