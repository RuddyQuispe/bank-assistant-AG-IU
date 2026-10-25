from langchain_core.documents import Document
from langgraph.runtime import Runtime

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.core.llm_model import get_llm
from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.prompts.retrieve_prompt import RETRIEVE_QUERY_PROMPT
from digital_wallet_rqm.graphs.state.bank_state import BankState, RetrieveUpdate
from digital_wallet_rqm.models.types import Source
from digital_wallet_rqm.utils.messages import format_recent_context


def _build_search_query(state: BankState) -> str:
    """Completa la pregunta con el historial para que la búsqueda entienda los seguimientos"""
    # El último mensaje es la pregunta actual; el historial son los anteriores
    history = format_recent_context(state["messages"][:-1])
    if not history:
        # Primera pregunta: no hay nada que completar, se evita la llamada al LLM
        return state["question"]
    chain = RETRIEVE_QUERY_PROMPT | get_llm(temperature=settings.LOW_TOMPERATURE, response_format=str)
    return chain.invoke({"history": history, "question": state["question"]})


def node_retrieve(state: BankState, runtime: Runtime[GraphContext]) -> RetrieveUpdate:
    """Busca chunks cercanos a la pregunta en el vector store"""
    query = _build_search_query(state)
    print(f"[retrieve]: buscando {query}")
    docs: list[Document] = runtime.context.vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": settings.TOP_K_RESULTS
        }
    ).invoke(query)
    retrieved_texts: list[str] = []
    sources: list[Source] = []
    for doc in docs:
        retrieved_texts.append(doc.page_content)
        page = doc.metadata.get("page", "N/A")
        if isinstance(page, int):
            # PyPDFLoader numera desde 0; al citar se muestra desde 1
            page = page + 1
        source = Source(file=doc.metadata.get("file_name", "desconocido"), page=page)
        sources.append(source)
        print(f"[retrieve]: file: {source["file"]}, (pag. {source["page"]})")
    print(f"[retrieve]: {len(docs)} chunks encontrados")
    return {
        "retrieve_docs": retrieved_texts,
        "sources": sources
    }
