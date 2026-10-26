from digital_wallet_rqm.domain.models.chat_session import build_title


def test_short_question_is_the_title() -> None:
    assert build_title("¿Cuánto cuesta un SPEI?") == "¿Cuánto cuesta un SPEI?"


def test_line_breaks_and_extra_spaces_are_collapsed() -> None:
    assert build_title("  hola\n\nmundo   banco ") == "hola mundo banco"


def test_long_question_is_cut_at_the_last_full_word_within_150_chars() -> None:
    question = "palabra " * 30  # 240 caracteres

    title = build_title(question)

    assert len(title) <= 150
    assert title.endswith("palabra")
    assert title == " ".join(["palabra"] * 18)


def test_exactly_150_chars_is_kept() -> None:
    question = "a" * 150

    assert build_title(question) == question


def test_single_long_word_is_cut_at_the_limit() -> None:
    assert build_title("x" * 200) == "x" * 150
