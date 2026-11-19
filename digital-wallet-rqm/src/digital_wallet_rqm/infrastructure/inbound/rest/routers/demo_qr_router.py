from typing import Annotated

from fastapi import APIRouter, Depends

from digital_wallet_rqm.infrastructure.inbound.dependencies import get_current_user, get_demo_qr_repository
from digital_wallet_rqm.infrastructure.inbound.error_schema import UNAUTHORIZED_RESPONSE
from digital_wallet_rqm.infrastructure.inbound.rest.schemas.demo_qr_schema import DemoQrsResponse
from digital_wallet_rqm.infrastructure.outbound.persistence.repositories import DemoQrRepository

router = APIRouter(
    prefix="/qr",
    tags=["qr"],
    dependencies=[Depends(get_current_user)],
    responses=UNAUTHORIZED_RESPONSE,
)


@router.get("/demo", summary="QR de prueba para el escáner simulado")
async def demo_qrs(qrs: Annotated[DemoQrRepository, Depends(get_demo_qr_repository)]) -> DemoQrsResponse:
    """Tokens de los QR de prueba. El QR no lleva datos del cobro: el agente los busca al escanearlo."""
    return DemoQrsResponse(codes=qrs.codes())
