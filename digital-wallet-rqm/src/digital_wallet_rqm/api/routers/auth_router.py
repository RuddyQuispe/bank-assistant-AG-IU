from fastapi import APIRouter, Depends, HTTPException, status

from digital_wallet_rqm.api.dependencies import get_auth_service
from digital_wallet_rqm.api.schemas.auth_schema import TokenRequest, TokenResponse
from digital_wallet_rqm.api.schemas.error_schema import UNAUTHORIZED_RESPONSE
from digital_wallet_rqm.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", summary="Obtener un token", responses=UNAUTHORIZED_RESPONSE)
def create_token(body: TokenRequest, auth_service: AuthService = Depends(get_auth_service)) -> TokenResponse:
    """Login de demo: entrega un JWT al usuario de demo. No pide contraseña.

    Enviar el token en el resto de los endpoints con el header `Authorization: Bearer <token>`.
    """
    user = auth_service.authenticate(body.nickname)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario desconocido")
    return TokenResponse(access_token=auth_service.create_token(user))
