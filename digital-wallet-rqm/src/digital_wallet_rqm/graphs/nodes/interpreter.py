from langchain_core.messages import AIMessage

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.core.llm_model import get_llm
from digital_wallet_rqm.graphs.prompts.interpreter_prompt import INTERPRETER_PROMPT
from digital_wallet_rqm.graphs.state.bank_state import BankState, InterpreterUpdate
from digital_wallet_rqm.utils.messages import format_recent_context

_NO_INFORMATION = "Sin información disponible"


def _format_information(state: BankState) -> str:
    """Arma la información que juntó el nodo anterior según la ruta"""
    route = state.get("route")
    if route == "retrieve":
        docs = state.get("retrieve_docs", [])
        sources = state.get("sources", [])
        lines = [
            f"[{source["file"]}, pág. {source["page"]}] {doc}"
            for doc, source in zip(docs, sources, strict=False)
        ]
        return "\n".join(lines) or _NO_INFORMATION
    if route == "tools":
        results = state.get("tool_results", [])
        return "\n".join(f"{result["tool"]}: {result["content"]}" for result in results) or _NO_INFORMATION
    return "Ninguna (saludo o aclaración)"


def node_interpreter(state: BankState) -> InterpreterUpdate:
    """Redacta la respuesta final del agente con la información de la ruta"""
    chain = INTERPRETER_PROMPT | get_llm(temperature=settings.DEFAULT_TEMPERATURE, response_format=str)
    response = chain.invoke({
        "history": format_recent_context(state["messages"]) or "Sin contexto previo",
        "information": _format_information(state),
        "question": state["question"],
    })
    print(f"[interpreter]: route={state.get("route")} -> {len(response)} chars")
    return {"response": response, "messages": [AIMessage(content=response)]}
