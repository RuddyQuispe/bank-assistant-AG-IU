from digital_wallet_rqm.domain.models import TokenUsage


def test_usages_add_up_field_by_field() -> None:
    assert TokenUsage(800, 90) + TokenUsage(12, 5) == TokenUsage(812, 95)


def test_empty_usage_is_zero() -> None:
    assert TokenUsage() == TokenUsage(input_tokens=0, output_tokens=0)
