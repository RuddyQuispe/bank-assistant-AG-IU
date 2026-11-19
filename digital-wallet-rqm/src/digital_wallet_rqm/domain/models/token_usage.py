from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TokenUsage:
    """Tokens que consumieron los LLM de chat en un run (o en varios, sumados)"""

    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens)


@dataclass(frozen=True)
class DailyUsage:
    """Consumo acumulado de un usuario en un día; cada día empieza desde cero"""

    day: date
    input_tokens: int
    output_tokens: int
    runs: int


@dataclass(frozen=True)
class UsageReport:
    """Consumo diario de un usuario y la fecha de hoy del negocio (para no depender del reloj del cliente)"""

    today: date
    days: list[DailyUsage]
