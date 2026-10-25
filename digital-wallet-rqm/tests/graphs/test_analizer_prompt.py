from digital_wallet_rqm.graphs.prompts.analizer_prompt import ANALIZER_PROMPT


def test_prompt_splits_rules_and_user_input():
    system, human = ANALIZER_PROMPT.format_messages(
        context="Sin contexto previo", question="cuánto tengo"
    )

    assert system.type == "system"
    assert "Reglas:" in system.content
    assert not system.content.startswith(" ")
    assert human.type == "human"
    assert human.content == "Contexto previo: Sin contexto previo\nMensaje: cuánto tengo"
