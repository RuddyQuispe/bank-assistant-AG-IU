from dataclasses import dataclass

from langchain_core.vectorstores import VectorStore

from digital_wallet_rqm.domain.models.current_user import CurrentUser


@dataclass(frozen=True)
class GraphContext:
    """Dependencies injected into the nodes through LangGraph's Runtime"""

    vector_store: VectorStore
    # Usuario del token; las tools lo usan para saber de quién son los datos
    user: CurrentUser | None = None
