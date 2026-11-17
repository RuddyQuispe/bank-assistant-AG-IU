from datetime import date

from pydantic import BaseModel, Field

from digital_wallet_rqm.domain.models import DailyUsage, UsageReport


class DailyUsageResponse(BaseModel):
    day: date = Field(examples=["2026-11-16"])
    input_tokens: int = Field(description="Tokens de entrada de los LLM de chat", examples=[812])
    output_tokens: int = Field(description="Tokens de salida de los LLM de chat", examples=[95])
    runs: int = Field(description="Runs (preguntas y confirmaciones) que terminaron bien", examples=[1])

    @classmethod
    def from_domain(cls, usage: DailyUsage) -> "DailyUsageResponse":
        return cls(day=usage.day, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, runs=usage.runs)


class UsageReportResponse(BaseModel):
    today: date = Field(description="Fecha de hoy en Bolivia: el consumo del día empieza a las 00:00 locales")
    days: list[DailyUsageResponse] = Field(description="Un elemento por día con consumo, el más reciente primero")

    @classmethod
    def from_domain(cls, report: UsageReport) -> "UsageReportResponse":
        return cls(today=report.today, days=[DailyUsageResponse.from_domain(day) for day in report.days])
