import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableLambda
from langchain_core.vectorstores import InMemoryVectorStore
from langgraph.graph import END, START, StateGraph

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.nodes import retrieve
from digital_wallet_rqm.graphs.nodes.retrieve import node_retrieve
from digital_wallet_rqm.graphs.state.bank_state import BankState


def _store(total: int) -> InMemoryVectorStore:
    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    store.add_documents([
        Document(page_content=f"chunk {i}", metadata={"file_name": "faq.pdf", "page": i})
        for i in range(total)
    ])
    return store


def _run_retrieve(
    store: InMemoryVectorStore, question: str = "comisiones", messages: list[BaseMessage] | None = None
) -> dict[str, object]:
    builder = StateGraph(BankState, context_schema=GraphContext)
    builder.add_node("retrieve", node_retrieve)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", END)
    graph = builder.compile()
    return graph.invoke({"messages": messages or [], "question": question}, context=GraphContext(vector_store=store))


def test_vector_store_is_injected_from_graph_context_and_limits_top_k(capsys: pytest.CaptureFixture[str]) -> None:
    result = _run_retrieve(_store(settings.TOP_K_RESULTS + 3))

    assert all(doc.startswith("chunk ") for doc in result["retrieve_docs"])
    assert len(result["retrieve_docs"]) == settings.TOP_K_RESULTS
    assert len(result["sources"]) == settings.TOP_K_RESULTS
    assert all(source["file"] == "faq.pdf" and isinstance(source["page"], int) for source in result["sources"])
    output = capsys.readouterr().out
    assert "generator object" not in output
    assert output.count("[retrieve]: file: faq.pdf") == settings.TOP_K_RESULTS


def test_missing_metadata_falls_back_to_defaults() -> None:
    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    store.add_documents([Document(page_content="sin metadata")])

    result = _run_retrieve(store)

    assert result["sources"] == [{"file": "desconocido", "page": "N/A"}]


def test_source_page_is_shown_starting_at_one() -> None:
    # PyPDFLoader numera las páginas desde 0; al citar se muestra desde 1
    store = InMemoryVectorStore(DeterministicFakeEmbedding(size=8))
    store.add_documents([Document(page_content="primera página", metadata={"file_name": "faq.pdf", "page": 0})])

    result = _run_retrieve(store)

    assert result["sources"] == [{"file": "faq.pdf", "page": 1}]


def test_first_question_searches_without_calling_the_llm(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_get_llm(temperature: float, response_format: type[str]) -> None:
        raise AssertionError("no debe llamar al LLM sin historial")

    monkeypatch.setattr(retrieve, "get_llm", fail_get_llm)

    _run_retrieve(_store(1))

    assert "[retrieve]: buscando comisiones" in capsys.readouterr().out


def test_follow_up_question_is_rewritten_with_history(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    received: list[str] = []

    def rewrite(prompt: PromptValue) -> str:
        received.append(prompt.to_messages()[-1].text)
        return "comisión de mantenimiento tarjeta de crédito Platinum"

    monkeypatch.setattr(retrieve, "get_llm", lambda temperature, response_format: RunnableLambda(rewrite))
    messages = [
        HumanMessage(content="cuánto cuesta el mantenimiento de la tarjeta de crédito"),
        AIMessage(content="Depende del tipo de tarjeta."),
        HumanMessage(content="¿y para la Platinum?"),
    ]

    _run_retrieve(_store(1), question="¿y para la Platinum?", messages=messages)

    # El historial no incluye la pregunta actual: va aparte
    assert received == [
        "Historial: Usuario: cuánto cuesta el mantenimiento de la tarjeta de crédito\n"
        "IA: Depende del tipo de tarjeta.\n"
        "Pregunta: ¿y para la Platinum?"
    ]
    assert "[retrieve]: buscando comisión de mantenimiento tarjeta de crédito Platinum" in capsys.readouterr().out
