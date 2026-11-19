from digital_wallet_rqm.infrastructure.outbound.agent.prompts.analizer_prompt import ANALIZER_PROMPT
from digital_wallet_rqm.infrastructure.outbound.agent.prompts.interpreter_prompt import INTERPRETER_PROMPT
from digital_wallet_rqm.infrastructure.outbound.agent.prompts.retrieve_prompt import RETRIEVE_QUERY_PROMPT


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


def test_analyzer_offers_interface_route_for_theme_background_and_font() -> None:
    system, _ = ANALIZER_PROMPT.format_messages(context="", question="")

    assert "interface = acciones en la app" in system.content
    assert "cambiar cómo se ve" in system.content
    assert "fondo de color puro o degradado" in system.content
    assert "tamaño de letra" in system.content
    assert '"ponme el modo oscuro" → interface' in system.content
    assert '"pon el fondo azul" → interface' in system.content
    assert '"quiero un fondo degradado de morado a rosado" → interface' in system.content
    assert '"cambia la fuente" → interface' in system.content
    assert '"agranda la letra" → interface' in system.content


def test_interpreter_does_not_repeat_what_a_card_already_shows() -> None:
    system, _ = INTERPRETER_PROMPT.format_messages(history="", information="", question="")

    assert "tarjeta" in system.content
    assert "no repitas montos ni números de cuenta" in system.content


def test_interpreter_cites_sources_only_for_documents() -> None:
    # Los datos de la cuenta (tools) no tienen archivo ni página: no se citan
    system, _ = INTERPRETER_PROMPT.format_messages(history="", information="", question="")

    assert "Cita las fuentes al final solo si la información viene de documentos" in system.content
    assert "Los datos de la cuenta (saldo, tarjetas) no llevan cita" in system.content


def test_analyzer_sends_qr_payments_to_interface() -> None:
    # Pagar con QR abre el escáner de la app (tool del cliente scan_qr)
    system, _ = ANALIZER_PROMPT.format_messages(context="", question="")

    assert "escanear un QR para pagar" in system.content
    assert "Pide pagar con QR o escanear un QR → interface" in system.content
    assert '"quiero pagar con QR" → interface' in system.content
    assert '"escanea este QR" → interface' in system.content
    # Las demás acciones que no ejecutamos siguen yendo a retrieve
    assert "(transferir, bloquear) → retrieve" in system.content
