from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.nodes.analyzer import node_analyzer
from digital_wallet_rqm.graphs.nodes.interpreter import node_interpreter
from digital_wallet_rqm.graphs.nodes.retrieve import node_retrieve
from digital_wallet_rqm.graphs.nodes.tools import node_tools
from digital_wallet_rqm.graphs.state.bank_state import BankState

RagAgent = CompiledStateGraph[BankState, GraphContext, BankState, BankState]


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
    builder = StateGraph(BankState, context_schema=GraphContext)
    builder.add_node("analyzer", node_analyzer)
    builder.add_node("retrieve", node_retrieve)
    builder.add_node("tools", node_tools)
    builder.add_node("interpreter", node_interpreter)

    builder.add_edge(START, "analyzer")
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
