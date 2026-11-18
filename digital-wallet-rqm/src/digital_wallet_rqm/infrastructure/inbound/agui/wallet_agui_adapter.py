from collections.abc import AsyncIterator

from ag_ui.core import BaseEvent, EventType, RunAgentInput
from ag_ui_langgraph import LangGraphAgent  # type: ignore[import-untyped]  # la librería no publica tipos
from langchain_core.runnables import RunnableConfig

from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.rag_agent import RagAgent

AGENT_NAME = "wallet"

_TOOL_CALL_EVENTS = {EventType.TOOL_CALL_START, EventType.TOOL_CALL_ARGS, EventType.TOOL_CALL_END}


class WalletAGUIAdapter(LangGraphAgent):  # type: ignore[misc]
    """Traductor AG-UI: corre el grafo RAG y convierte lo que pasa adentro en eventos AG-UI.

    No es otro agente: recibe el mismo grafo de build_rag_agent. Se crea uno por request porque
    lleva al usuario del token.
    """

    def __init__(self, graph: RagAgent, context: GraphContext) -> None:
        super().__init__(name=AGENT_NAME, graph=graph)
        self._graph_context = context
        # Tool calls ocultas en este run: su TOOL_CALL_RESULT tampoco se manda
        self._hidden_tool_call_ids: set[str] = set()

    async def run(self, input: RunAgentInput) -> AsyncIterator[BaseEvent]:
        async for event in super().run(input):
            # None: evento descartado por _dispatch_event
            if event is not None:
                yield event

    def _dispatch_event(self, event: BaseEvent) -> BaseEvent | None:
        # La base respeta "emit-tool-calls" al leer el LLM, pero al terminar cada tool vuelve a emitir
        # las llamadas que no registró (y su resultado) y ahí no mira la metadata: se filtran aquí
        if event.type in _TOOL_CALL_EVENTS and _is_hidden_tool_call(event):
            self._hidden_tool_call_ids.add(getattr(event, "tool_call_id", ""))
            return None
        # El resultado llega sin raw_event (no hay metadata que mirar): se oculta por el id de su llamada.
        # Si llegara, el navegador lo guardaría como resultado de una tool que nunca vio
        tool_call_id = getattr(event, "tool_call_id", None)
        if event.type == EventType.TOOL_CALL_RESULT and tool_call_id in self._hidden_tool_call_ids:
            return None
        dispatched: BaseEvent | None = super()._dispatch_event(event)
        return dispatched

    def get_schema_keys(self, config: RunnableConfig) -> dict[str, list[str]]:
        # La base genera el JSON Schema del config, que incluye GraphContext; su VectorStore no tiene
        # JSON Schema y Pydantic lanza un error que la base no atrapa. Solo hacen falta las claves
        # de entrada/salida: la entrada (MessagesState) limita qué estado puede mandar el cliente.
        input_keys = list(self.graph.get_input_jsonschema(config).get("properties", {}))
        output_keys = list(self.graph.get_output_jsonschema(config).get("properties", {}))
        return {
            "input": [*input_keys, *self.constant_schema_keys],
            "output": [*output_keys, *self.constant_schema_keys],
            "config": [],
            "context": [],
        }

    def get_stream_kwargs(
        self,
        input: object,
        subgraphs: bool = False,
        version: str = "v2",
        config: RunnableConfig | dict[str, object] | None = None,
        context: dict[str, object] | None = None,
        fork: object | None = None,
    ) -> dict[str, object]:
        stream_kwargs: dict[str, object] = super().get_stream_kwargs(
            input=input, subgraphs=subgraphs, version=version, config=config, context=context, fork=fork
        )
        # La base arma "context" como dict con todo config["configurable"] (incluye thread_id) y
        # GraphContext es un dataclass: LangGraph falla al construirlo. Se pasa el objeto tipado.
        stream_kwargs["context"] = self._graph_context
        return stream_kwargs


def _is_hidden_tool_call(event: BaseEvent) -> bool:
    raw_event = event.raw_event
    if not isinstance(raw_event, dict):
        return False
    # Emitida a mano por el nodo (manually_emit_tool_call): es explícita, nunca se oculta
    if raw_event.get("event") == "on_custom_event":
        return False
    metadata = raw_event.get("metadata")
    return isinstance(metadata, dict) and metadata.get("emit-tool-calls") is False
