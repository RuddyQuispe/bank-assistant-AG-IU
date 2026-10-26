from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.infrastructure.agent.messages import format_recent_context
from digital_wallet_rqm.infrastructure.agent.prompts.analizer_prompt import ANALIZER_PROMPT
from digital_wallet_rqm.infrastructure.agent.route_decision import RouteDecision
from digital_wallet_rqm.infrastructure.agent.state.bank_state import AnalyzerUpdate, BankState
from digital_wallet_rqm.infrastructure.llm.llm_model import get_llm


def node_analyzer(state: BankState) -> AnalyzerUpdate:
    """Decide si la pregunta necesita buscar en documentos o ejecutar comandos"""
    chain = ANALIZER_PROMPT | get_llm(temperature=settings.LOW_TOMPERATURE, response_format=RouteDecision)
    recent_context = format_recent_context(state["messages"])

    decision = chain.invoke({
        "context": recent_context or "Sin contexto previo",
        "question": state["question"],
    })
    if decision is None:
        # Structured output can come back empty; retrieve is the safe default route
        print("route=retrieve : (fallback, empty model output)")
        return {"route": "retrieve"}
    print(f"route={decision.route} : ({decision.reason})")
    return {"route": decision.route}
