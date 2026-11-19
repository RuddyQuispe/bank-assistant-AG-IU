from typing import Any, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState

from digital_wallet_rqm.infrastructure.outbound.agent.types import Route, Source


class ToolResult(TypedDict):
    tool: str
    content: str


# Descripción de una tool del cliente (name, description, parameters); su código vive en el navegador
ClientTool = dict[str, Any]


class AgentInput(MessagesState):
    """Lo que acepta el grafo al entrar: LangGraph descarta cualquier clave que no esté aquí"""

    # AG-UI escribe las tools del cliente en "tools" (nombre fijo del adapter); otros clientes no las mandan
    tools: NotRequired[list[ClientTool]]


class BankState(MessagesState):
    # "messages" viene de MessagesState y se acumula con add_messages
    # "question" la llena el nodo ingest desde el último mensaje del usuario
    question: str
    # Tools que ofrece el cliente (AG-UI las une con las del checkpoint); las ejecuta el navegador, no el backend
    tools: NotRequired[list[ClientTool]]
    # Campos que los nodos llenan durante la ejecución
    route: NotRequired[Route]
    retrieve_docs: NotRequired[list[str]]
    sources: NotRequired[list[Source]]
    tool_results: NotRequired[list[ToolResult]]
    response: NotRequired[str]
    # Token del QR que espera la confirmación del cliente (qr_confirm pausa el grafo); None si no hay pago pendiente
    awaiting_payment: NotRequired[str | None]
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
    # Tarjetas que se mostraron en el chat (tool call + resultado): así quedan en el historial
    messages: NotRequired[list[AnyMessage]]


class QrPaymentUpdate(TypedDict):
    tool_results: list[ToolResult]
    # bank_tools: el interpreter lee tool_results, como con los datos de la cuenta
    route: Route
    # La tarjeta del cobro (tool call + resultado) queda en el historial
    messages: NotRequired[list[AnyMessage]]
    awaiting_payment: str | None


class QrConfirmUpdate(TypedDict):
    tool_results: list[ToolResult]
    route: Route
    # El comprobante (tool call + resultado) queda en el historial
    messages: NotRequired[list[AnyMessage]]
    awaiting_payment: None


class InterfaceUpdate(TypedDict):
    response: str
    messages: list[AnyMessage]


class InterpreterUpdate(TypedDict):
    response: str
    messages: list[AnyMessage]
