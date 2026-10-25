from digital_wallet_rqm.graphs.prompts.analizer_prompt import ANALIZER_PROMPT
from digital_wallet_rqm.graphs.prompts.interpreter_prompt import INTERPRETER_PROMPT
from digital_wallet_rqm.graphs.prompts.retrieve_prompt import RETRIEVE_QUERY_PROMPT


def test_analyzer_only_offers_tools_that_exist() -> None:
    system, _ = ANALIZER_PROMPT.format_messages(context="", question="")

    assert "Bolivia" in system.content
    assert "solo disponible: su saldo" in system.content
    assert "SPEI" not in system.content
    assert "CLABE" not in system.content


def test_retrieve_query_prompt_sends_history_and_question() -> None:
    system, human = RETRIEVE_QUERY_PROMPT.format_messages(history="Usuario: hola", question="¿y en dólares?")

    assert system.type == "system"
    assert "No respondas la pregunta" in system.content
    assert human.content == "Historial: Usuario: hola\nPregunta: ¿y en dólares?"


def test_interpreter_asks_for_currency_and_sources() -> None:
    system, _ = INTERPRETER_PROMPT.format_messages(history="", information="", question="")

    assert "Bolivia" in system.content
    assert "(Bs o USD)" in system.content
    assert "Cita las fuentes" in system.content
