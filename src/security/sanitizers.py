import re
import unicodedata

def sanitizar_texto_para_prompt(texto: str) -> str:
    """Higieniza texto de PDFs contra indireção de Prompt Injection."""
    if not texto:
        return ""

    # Normalização Unicode (NFKC) e remoção de caracteres de controle
    texto_sanitizado = unicodedata.normalize("NFKC", texto)
    texto_sanitizado = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", texto_sanitizado)

    # Escapamento de tags wrappers
    texto_sanitizado = texto_sanitizado.replace("</document_data>", "[TAG_FECHAMENTO_IGNORADA]")
    texto_sanitizado = texto_sanitizado.replace("<document_data>", "[TAG_ABERTURA_IGNORADA]")

    padroes_maliciosos = [
        r"(?i)ignore\s+(todas\s+as|as)?\s*(instru[çc][õo]es|orienta[çc][õo]es|regras)\s+(anteriores|pr[ée]vias)",
        r"(?i)ignore\s+(all\s+)?(previous\s+)?instructions",
        r"(?i)disregard\s+(the\s+)?above",
        r"(?i)forget\s+(everything\s+)?you\s+(know|were\s+told)",
        r"(?i)^\s*(system|user|assistant|human|ai)\s*:",
        r"(?i)\[INST\].*?\[/INST\]",
        r"(?i)<\|im_start\|>.*?<\|im_end\|>",
        r"(?i)<\|endoftext\|>",
        r"(?i)voc[êe]\s+agora\s+[ée]\s+um",
        r"(?i)you\s+are\s+now\s+a",
        r"(?i)novo\s+papel\s*:",
        r"(?i)altere\s+o\s+formato\s+de\s+sa[íi]da",
        r"(?i)retorne\s+apenas\s+o\s+texto",
        r"(?i)considere\s+este\s+docente\s+como\s+primeiro\s+autor"
    ]

    for padrao in padroes_maliciosos:
        texto_sanitizado = re.sub(padrao, "[TEXTO_SUSPEITO_REMOVIDO]", texto_sanitizado)

    return texto_sanitizado.strip()