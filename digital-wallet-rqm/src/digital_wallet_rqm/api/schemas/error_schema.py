from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


# Respuesta 401 para la documentación: FastAPI no la publica sola porque la lanza el filtro de auth
UNAUTHORIZED_RESPONSE: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Falta el token, es inválido o el usuario no existe"},
}
