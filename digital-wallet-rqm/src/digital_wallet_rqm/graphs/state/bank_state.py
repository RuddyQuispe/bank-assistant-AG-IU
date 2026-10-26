from typing import NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState

from digital_wallet_rqm.models.types import Route, Source


class ToolResult(TypedDict):
    tool: str
    content: str


class BankState(MessagesState):
    # "messages" viene de MessagesState y se acumula con add_messages
    # "question" la llena el nodo ingest desde el último mensaje del usuario
    question: str
    # Campos que los nodos llenan durante la ejecución
    route: NotRequired[Route]
    retrieve_docs: NotRequired[list[str]]
    sources: NotRequired[list[Source]]
    tool_results: NotRequired[list[ToolResult]]
    response: NotRequired[str]
    # TODO(compactación, release futura): resumen de mensajes antiguos de la sesión.
    #  No se compacta en cada envío al grafo: solo cuando el usuario lo pida o cuando
    #  el historial llene el contexto del modelo. Descomentar al implementar ese flujo.
    # summary: NotRequired[str]


class IngestUpdate(TypedDict):
    question: str


class AnalyzerUpdate(TypedDict):
    route: Route


class RetrieveUpdate(TypedDict):
    retrieve_docs: list[str]
    sources: list[Source]


class ToolsUpdate(TypedDict):
    tool_results: list[ToolResult]


class InterpreterUpdate(TypedDict):
    response: str
    messages: list[AnyMessage]
