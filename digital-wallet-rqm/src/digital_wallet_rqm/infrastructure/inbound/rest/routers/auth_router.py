from fastapi import APIRouter, Depends

from digital_wallet_rqm.application.ports.inbound.auth_service import AuthService
from digital_wallet_rqm.infrastructure.inbound.dependencies import get_auth_service
from digital_wallet_rqm.infrastructure.inbound.error_schema import UNAUTHORIZED_RESPONSE
from digital_wallet_rqm.infrastructure.inbound.rest.schemas.auth_schema import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", summary="Obtener un token", responses=UNAUTHORIZED_RESPONSE)
def create_token(body: TokenRequest, auth_service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    """Login de demo: entrega un JWT al usuario de demo. No pide contraseña.

    Enviar el token en el resto de los endpoints con el header `Authorization: Bearer <token>`.
    """
    # Un usuario inexistente lanza InvalidCredentialsError: el handler global responde 401
    return TokenResponse(access_token=auth_service.login(body.nickname))
