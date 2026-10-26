from langchain_core.messages import AIMessage, HumanMessage

from digital_wallet_rqm.infrastructure.agent.nodes.ingest import node_ingest
from digital_wallet_rqm.infrastructure.agent.state.bank_state import BankState


def test_ingest_takes_question_from_last_human_message() -> None:
    state: BankState = {
        "messages": [HumanMessage(content="hola"), AIMessage(content="eco"), HumanMessage(content="mi saldo")],
        "question": "",
    }

    assert node_ingest(state) == {"question": "mi saldo"}


def test_ingest_skips_trailing_ai_messages() -> None:
    state: BankState = {"messages": [HumanMessage(content="hola"), AIMessage(content="eco")], "question": ""}

    assert node_ingest(state) == {"question": "hola"}


def test_ingest_without_human_message_returns_empty_question() -> None:
    state: BankState = {"messages": [AIMessage(content="eco")], "question": ""}

    assert node_ingest(state) == {"question": ""}
