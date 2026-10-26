from collections.abc import AsyncIterator
from typing import Any, cast

from ag_ui.core import BaseEvent, RunAgentInput
from copilotkit import LangGraphAGUIAgent
from langchain_core.runnables import RunnableConfig

from digital_wallet_rqm.infrastructure.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.agent.rag_agent import RagAgent

AGENT_NAME = "wallet"


class WalletAGUIAdapter(LangGraphAGUIAgent):
    """Traductor AG-UI: corre el grafo RAG y convierte lo que pasa adentro en eventos AG-UI.

    No es otro agente: recibe el mismo grafo de build_rag_agent. Se crea uno por request porque
    lleva al usuario del token.
    """

    def __init__(self, graph: RagAgent, context: GraphContext) -> None:
        super().__init__(
            name=AGENT_NAME,
            # La anotación de la librería asume grafos sin context_schema; el contexto se pasa abajo
            graph=cast(Any, graph),
        )
        self._graph_context = context

    async def events(self, input_data: RunAgentInput) -> AsyncIterator[BaseEvent]:
        """Versión tipada de run(): la clase de copilotkit no tiene anotaciones"""
        async for event in self.run(input_data):  # type: ignore[no-untyped-call]
            yield event

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
        # Se descarta el payload "copilotkit" que agrega la base: el grafo todavía no lo usa.
        stream_kwargs["context"] = self._graph_context
        return stream_kwargs
