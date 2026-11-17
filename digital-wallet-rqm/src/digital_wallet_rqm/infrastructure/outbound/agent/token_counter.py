from threading import Lock

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from digital_wallet_rqm.domain.models import TokenUsage


class TokenCounter(BaseCallbackHandler):
    """Callback de un run: suma los tokens de cada llamada a un LLM de chat, en cualquier nodo.

    Los callbacks del config llegan a todos los nodos del grafo, así que no hay que tocar ninguno.
    No usa UsageMetadataCallbackHandler de LangChain: ese ignora las respuestas sin model_name.
    """

    def __init__(self) -> None:
        self.usage = TokenUsage()
        # Los nodos síncronos corren en hilos: dos respuestas no deben pisarse la suma
        self._lock = Lock()

    def on_llm_end(self, response: LLMResult, **kwargs: object) -> None:
        for generations in response.generations:
            for generation in generations:
                if not isinstance(generation, ChatGeneration) or not isinstance(generation.message, AIMessage):
                    continue
                metadata = generation.message.usage_metadata
                if metadata:
                    with self._lock:
                        self.usage += TokenUsage(metadata["input_tokens"], metadata["output_tokens"])
