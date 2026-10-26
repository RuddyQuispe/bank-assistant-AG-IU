from digital_wallet_rqm.infrastructure.agent.state.bank_state import BankState, IngestUpdate


def node_ingest(state: BankState) -> IngestUpdate:
    """Copia el último mensaje del usuario a "question", que es lo que leen los demás nodos"""
    # Los clientes (REST y AG-UI) solo envían "messages"; este nodo no usa LLM
    for message in reversed(state["messages"]):
        if message.type == "human":
            return {"question": message.text}
    return {"question": ""}
