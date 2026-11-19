from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.messages import is_client_tool_result, scanned_qr
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.analyzer import node_analyzer
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.ingest import node_ingest
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interface import node_interface
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interpreter import node_interpreter
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.qr_confirm import node_qr_confirm
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.qr_payment import node_qr_payment
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.retrieve import node_retrieve
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.tools import node_tools
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import AgentInput, BankState

# Entrada: "messages" y las tools del cliente (el nodo ingest deriva "question"); salida: el estado completo
RagAgent = CompiledStateGraph[BankState, GraphContext, AgentInput, BankState]

# Metadata de nodos internos: AG-UI no emite el texto ni las tool calls de sus LLM (ruteo, consulta, tools)
HIDDEN_FROM_CHAT = {"emit-messages": False, "emit-tool-calls": False}
# El nodo interface emite sus tool calls a mano (completas); su texto sí llega al chat
TOOL_CALLS_EMITTED_BY_NODE = {"emit-tool-calls": False}


def decide_route_node_path(state: BankState) -> Literal["retrieve", "bank_tools", "interface", "interpreter"]:
    """Router de la arista condicional (no es un nodo: no modifica el estado)."""
    # match exhaustivo: si se agrega una ruta nueva a Route, mypy avisa que falta manejarla
    match state["route"]:
        case "retrieve" | "bank_tools" | "interface" as route:
            return route
        case "analyst":
            return "interpreter"


def decide_after_ingest(state: BankState) -> Literal["analyzer", "qr_payment", "interpreter"]:
    """Con el resultado de una tool del navegador no se vuelve a clasificar"""
    # Sin esto, "question" sigue siendo el pedido original y el analyzer volvería a interface (loop)
    # 1. El escáner devolvió un QR: el backend busca el cobro antes de responder
    if scanned_qr(state["messages"]) is not None:
        return "qr_payment"
    # 2. Una acción ya aplicada en la app (tema, fuente...): se confirma directo
    return "interpreter" if is_client_tool_result(state["messages"]) else "analyzer"


def decide_after_interpreter(state: BankState) -> Literal["qr_confirm", "__end__"]:
    """Con un pago QR pendiente, después de responder el grafo espera la confirmación del cliente"""
    return "qr_confirm" if state.get("awaiting_payment") else "__end__"


def build_rag_agent(checkpointer: BaseCheckpointSaver[str] | None = None) -> RagAgent:
    """Compila el grafo; el vector store llega por context=GraphContext(...) en cada invoke."""
    builder = StateGraph(BankState, context_schema=GraphContext, input_schema=AgentInput)
    builder.add_node("ingest", node_ingest)
    builder.add_node("analyzer", node_analyzer, metadata=HIDDEN_FROM_CHAT)
    builder.add_node("retrieve", node_retrieve, metadata=HIDDEN_FROM_CHAT)
    builder.add_node("bank_tools", node_tools, metadata=HIDDEN_FROM_CHAT)
    builder.add_node("interface", node_interface, metadata=TOOL_CALLS_EMITTED_BY_NODE)
    builder.add_node("qr_payment", node_qr_payment, metadata=HIDDEN_FROM_CHAT)
    builder.add_node("qr_confirm", node_qr_confirm, metadata=HIDDEN_FROM_CHAT)
    builder.add_node("interpreter", node_interpreter)

    builder.add_edge(START, "ingest")
    builder.add_conditional_edges(
        source="ingest",
        path=decide_after_ingest,
        path_map={"analyzer": "analyzer", "qr_payment": "qr_payment", "interpreter": "interpreter"},
    )
    builder.add_conditional_edges(
        source="analyzer",
        path=decide_route_node_path,
        path_map={
            "retrieve": "retrieve",
            "bank_tools": "bank_tools",
            "interface": "interface",
            "interpreter": "interpreter"
        }
    )

    builder.add_edge("retrieve", "interpreter")
    builder.add_edge("bank_tools", "interpreter")
    builder.add_edge("qr_payment", "interpreter")
    builder.add_edge("qr_confirm", "interpreter")
    builder.add_edge("interface", END)
    builder.add_conditional_edges(
        source="interpreter",
        path=decide_after_interpreter,
        path_map={"qr_confirm": "qr_confirm", "__end__": END},
    )
    return builder.compile(checkpointer=checkpointer)
