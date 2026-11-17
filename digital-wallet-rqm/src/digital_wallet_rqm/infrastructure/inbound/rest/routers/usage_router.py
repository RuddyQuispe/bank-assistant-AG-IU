from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from digital_wallet_rqm.application.usage_use_cases import UsageUseCases
from digital_wallet_rqm.infrastructure.inbound.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_usage_use_cases,
)
from digital_wallet_rqm.infrastructure.inbound.error_schema import BAD_REQUEST_RESPONSE, UNAUTHORIZED_RESPONSE
from digital_wallet_rqm.infrastructure.inbound.rest.schemas.usage_schema import UsageReportResponse

router = APIRouter(
    prefix="/usage",
    tags=["usage"],
    dependencies=[Depends(get_current_user)],
    responses=UNAUTHORIZED_RESPONSE,
)


@router.get("/daily", summary="Consumo de tokens por día", responses=BAD_REQUEST_RESPONSE)
async def daily_usage(
    user: AuthenticatedUser,
    usage: Annotated[UsageUseCases, Depends(get_usage_use_cases)],
    # "from" es palabra reservada en Python: el parámetro se llama start y se publica como "from"
    start: Annotated[date | None, Query(alias="from", description="Primer día (inclusive)")] = None,
    end: Annotated[date | None, Query(alias="to", description="Último día (inclusive); por defecto hoy")] = None,
) -> UsageReportResponse:
    """Tokens de entrada y salida de los LLM de chat del usuario del token, por día (hora de Bolivia).

    Sin rango devuelve los últimos 7 días. Los días sin consumo no aparecen.
    """
    return UsageReportResponse.from_domain(await usage.daily(user, start, end))
