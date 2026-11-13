import time
from google import genai
from google.genai.errors import APIError
from google.genai import types

try:
    from src.config import GEMINI_API_KEY, MODELOS_DISPONIVEIS
except ModuleNotFoundError:
    from config import GEMINI_API_KEY, MODELOS_DISPONIVEIS

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def executar_requisicao_com_retry(self, modelo: str, prompt: str, instrucao_sistema: str = None, max_tentativas: int = 5):
        tempo_espera = 15

        for tentativa in range(1, max_tentativas + 1):
            try:
                config_args = {"temperature": 0.0}
                if instrucao_sistema:
                    config_args["system_instruction"] = instrucao_sistema

                resposta = self.client.models.generate_content(
                    model=modelo,
                    contents=[prompt],
                    config=types.GenerateContentConfig(**config_args)
                )
                return resposta

            except APIError as erro:
                if erro.code in [429, 500, 502, 503, 504]:
                    print(f"⚠️ [{modelo}] Cota excedida (Erro {erro.code}) na tentativa {tentativa}/{max_tentativas}.")
                    print(f"   Aguardando {tempo_espera}s para liberação da cota no Google AI Studio...")
                    time.sleep(tempo_espera)
                    tempo_espera *= 2
                else:
                    print(f"❌ [{modelo}] Erro não recuperável ({erro.code}): {erro.message}")
                    break
            except Exception as erro:
                print(f"❌ [{modelo}] Erro inesperado: {erro}")
                break

        return None