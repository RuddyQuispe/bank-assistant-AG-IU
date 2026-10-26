from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.nodes.analyzer import node_analyzer
from digital_wallet_rqm.graphs.nodes.ingest import node_ingest
from digital_wallet_rqm.graphs.nodes.interpreter import node_interpreter
from digital_wallet_rqm.graphs.nodes.retrieve import node_retrieve
from digital_wallet_rqm.graphs.nodes.tools import node_tools
from digital_wallet_rqm.graphs.state.bank_state import BankState

# Entrada: solo "messages" (el nodo ingest deriva "question"); salida: el estado completo
RagAgent = CompiledStateGraph[BankState, GraphContext, MessagesState, BankState]

# Metadata de nodos internos: CopilotKit no envía al chat lo que generan sus LLM (ruteo, consulta, tools)
HIDDEN_FROM_CHAT = {"copilotkit:emit-messages": False, "copilotkit:emit-tool-calls": False}


def decide_route_node_path(state: BankState) -> Literal["retrieve", "tools", "interpreter"]:
    """Router de la arista condicional (no es un nodo: no modifica el estado)."""
    # match exhaustivo: si se agrega una ruta nueva a Route, mypy avisa que falta manejarla
    match state["route"]:
        case "retrieve" | "tools" as route:
            return route
        case "analyst":
            return "interpreter"


def build_rag_agent(checkpointer: BaseCheckpointSaver[str] | None = None) -> RagAgent:
    """Compila el grafo; el vector store llega por context=GraphContext(...) en cada invoke."""
    builder = StateGraph(BankState, context_schema=GraphContext, input_schema=MessagesState)
    builder.add_node("ingest", node_ingest)
    builder.add_node("analyzer", node_analyzer, metadata=HIDDEN_FROM_CHAT)
    builder.add_node("retrieve", node_retrieve, metadata=HIDDEN_FROM_CHAT)
    builder.add_node("tools", node_tools, metadata=HIDDEN_FROM_CHAT)
    builder.add_node("interpreter", node_interpreter)

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "analyzer")
    builder.add_conditional_edges(
        source="analyzer",
        path=decide_route_node_path,
        path_map={
            "retrieve": "retrieve",
            "tools": "tools",
            "interpreter": "interpreter"
        }
    )

    builder.add_edge("retrieve", "interpreter")
    builder.add_edge("tools", "interpreter")
    builder.add_edge("interpreter", END)
    return builder.compile(checkpointer=checkpointer)
